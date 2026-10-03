"""Docker-based Java sandbox executor for untrusted student submissions."""
from __future__ import annotations

import logging
import os
import re
import shutil
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import docker
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from docker.types import LogConfig

logger = logging.getLogger("judge")

OUTPUT_LIMIT_MESSAGE = "Output limit exceeded."
# How long to wait, after the container exits, for its output to drain.
PUMP_DRAIN_TIMEOUT_S = 10

# Every sandbox container carries this label so the recovery sweep can find
# ones orphaned by a worker crash.
SANDBOX_LABEL = "judge-engine"
SANDBOX_LABEL_VALUE = "sandbox"


class SandboxError(Exception):
    """The sandbox itself failed (Docker error), not the student's program.

    Raised instead of returning a verdict so the task can retry and, if the
    failure persists, record SystemError rather than charging the student.
    """


class CompileTimeout(Exception):
    """javac ran past JUDGE_COMPILE_TIMEOUT_S.

    Charged to the submission as a compile error: retrying a source written
    to make javac slow would only multiply the load on the judge.
    """


# The sandbox user: "nobody", which owns nothing on a typical host. uid 1000
# is usually the host's first login user, so a container escape would land
# with that user's files (and often the docker group).
SANDBOX_UID = 65534


def _restrict_workspace(workspace: Path) -> None:
    """Give the job folder to the sandbox user alone (0700).

    Some bind mounts (Docker Desktop's Windows/macOS file sharing) ignore
    ownership; there the folder falls back to 0777, as before, or javac
    could not write its class file.
    """
    try:
        os.chown(workspace, SANDBOX_UID, SANDBOX_UID)
        os.chmod(workspace, 0o700)
        if workspace.stat().st_uid == SANDBOX_UID:
            return
    except OSError:
        pass
    logger.warning("Cannot hand %s to the sandbox user; using mode 0777", workspace)
    os.chmod(workspace, 0o777)


def _is_absolute_host_path(path: str) -> bool:
    # The daemon may run on Windows, where os.path.isabs() (Linux rules here)
    # would reject "C:/..." paths.
    return path.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", path) is not None


# Runs the program, then reports the container's CPU time on stderr. Time
# limits use CPU time: wall-clock time also counts waiting for the CPU or the
# disk, so a busy host turned correct solutions into TLE. `kill -9 -1` first
# ends anything the program left running, so the marker is always the last
# line and the program cannot forge it (we parse only a trailing marker).
CPU_MARKER = "__JUDGE_CPU_USEC="
_CPU_WRAPPER = (
    '"$@"; code=$?\n'
    "kill -9 -1 2>/dev/null\n"
    "cpu=$(sed -n 's/^usage_usec //p' /sys/fs/cgroup/cpu.stat 2>/dev/null)\n"
    f"printf '\\n{CPU_MARKER}%s\\n' \"$cpu\" >&2\n"
    "exit $code\n"
)
_CPU_MARKER_RE = re.compile(r"\n?" + re.escape(CPU_MARKER) + r"(\d*)\n?\Z")


def _with_cpu_accounting(command: list[str]) -> list[str]:
    return ["sh", "-c", _CPU_WRAPPER, "sh", *command]


def _split_cpu_marker(stderr: str) -> tuple[str, int | None]:
    """Strip the wrapper's trailing CPU marker; returns (stderr, cpu_ms)."""
    match = _CPU_MARKER_RE.search(stderr)
    if match is None:
        return stderr, None
    usec = match.group(1)
    return stderr[: match.start()], (int(usec) // 1000 if usec else None)


def _java_run_command(memory_limit_mb: int) -> list[str]:
    jvm_heap = max(memory_limit_mb - 64, 32)
    # -Xss: recursive DFS on ~1e5 nodes must not overflow the default 1 MB
    # stack. Serial GC: no GC threads competing for the single CPU and pids cap.
    return _with_cpu_accounting(
        ["java", f"-Xmx{jvm_heap}m", "-Xss64m", "-XX:+UseSerialGC", "Solution"]
    )


def _is_java_oom(run: "RunResult") -> bool:
    # The heap cap (-Xmx) sits below the container limit, so the JVM usually
    # dies with its own OutOfMemoryError before Docker's OOM killer fires.
    return run.exit_code not in (0, None) and "java.lang.OutOfMemoryError" in run.stderr


@dataclass(frozen=True)
class RunResult:
    verdict: str
    stdout: str
    stderr: str
    execution_time_ms: int | None
    exit_code: int | None
    timed_out: bool = False
    oom_killed: bool = False
    output_limit_exceeded: bool = False


class JudgeExecutor:
    """Compile and run Java solutions inside ephemeral Docker containers."""

    def __init__(self) -> None:
        self.client = docker.from_env()
        self.image = settings.JUDGE_IMAGE
        self.data_dir = Path(os.environ.get("JUDGE_DATA_DIR", "/judge_data"))
        self._host_data_dir: str | None = None

    @property
    def host_data_dir(self) -> str:
        """Where ``data_dir`` lives on the Docker host: sandbox bind mounts are
        resolved by the daemon, not inside this (worker) container."""
        if self._host_data_dir is None:
            self._host_data_dir = self._resolve_host_data_dir()
        return self._host_data_dir

    def _resolve_host_data_dir(self) -> str:
        configured = os.environ.get("JUDGE_HOST_DATA_DIR", "").strip()
        if configured:
            if not _is_absolute_host_path(configured):
                raise ImproperlyConfigured(
                    f"JUDGE_HOST_DATA_DIR must be an absolute host path, got {configured!r}. "
                    "Unset it to detect the path automatically."
                )
            return configured
        # In a container: ask Docker which host folder is mounted at data_dir.
        try:
            me = self.client.containers.get(socket.gethostname())
            for mount in me.attrs.get("Mounts", []):
                if mount.get("Destination") == str(self.data_dir):
                    return mount["Source"]
        except docker.errors.DockerException:
            logger.debug("Could not inspect own container", exc_info=True)
        if not os.path.exists("/.dockerenv"):
            # Running directly on the host: both sides see the same path.
            return str(self.data_dir.resolve())
        raise ImproperlyConfigured(
            f"Cannot find the host folder mounted at {self.data_dir}; "
            "set JUDGE_HOST_DATA_DIR to its absolute host path."
        )

    def cleanup_orphans(self, older_than: datetime) -> int:
        """Remove sandbox containers and workspaces left behind by a crashed
        worker. Live runs are never older than a few wall-time limits, far
        below the stale window the sweep passes in."""
        cutoff = older_than.timestamp()
        removed = 0
        for container in self.client.api.containers(
            all=True, filters={"label": f"{SANDBOX_LABEL}={SANDBOX_LABEL_VALUE}"}
        ):
            if container.get("Created", cutoff) < cutoff:
                try:
                    self.client.api.remove_container(container["Id"], force=True)
                    removed += 1
                except docker.errors.APIError:
                    logger.warning("Could not remove orphan container %s", container["Id"])
        if self.data_dir.is_dir():
            for entry in self.data_dir.iterdir():
                if (
                    entry.is_dir()
                    and re.fullmatch(r"[0-9a-f]{32}", entry.name)
                    and entry.stat().st_mtime < cutoff
                ):
                    shutil.rmtree(entry, ignore_errors=True)
                    removed += 1
        return removed

    def ensure_image(self) -> None:
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            logger.info("Pulling judge image %s", self.image)
            self.client.images.pull(self.image)

    def judge_submission_source(
        self,
        source_code: str,
        test_cases: list[dict],
        time_limit_ms: int,
        memory_limit_mb: int,
        run_all_tests: bool = False,
        results: list | None = None,
    ) -> dict:
        """Compile and judge against every test case.

        Per-test results are appended to ``results`` (a fresh list if None) as
        they finish, so a caller interrupted by the task time limit can still
        save the tests that ran.
        """
        self.ensure_image()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        workspace = self.data_dir / job_id
        host_workspace = f"{self.host_data_dir.rstrip('/').rstrip(chr(92))}/{job_id}"
        workspace.mkdir(parents=True, exist_ok=True)
        try:
            _restrict_workspace(workspace)
            (workspace / "Solution.java").write_text(source_code, encoding="utf-8")

            compile_result = self._run_container(
                host_workspace=host_workspace,
                command=["javac", "Solution.java"],
                time_limit_s=settings.JUDGE_COMPILE_TIMEOUT_S,
                memory_limit_mb=memory_limit_mb,
                stdin_data=None,
                work_writable=True,
            )
            if compile_result.timed_out:
                raise CompileTimeout("Compilation timed out")
            if compile_result.exit_code is None:
                raise SandboxError("Compiler container exited without a status")
            if compile_result.exit_code not in (0,):
                err = (compile_result.stderr or compile_result.stdout).strip()
                return {
                    "status": "CompileError",
                    "compile_error": err or "Compilation failed.",
                    "results": [],
                }

            # Remove source after compile so students cannot exfiltrate via side channels
            try:
                (workspace / "Solution.java").unlink(missing_ok=True)
            except OSError:
                pass

            if results is None:
                results = []
            overall = "Accepted"
            for tc in test_cases:
                wall = max(
                    (time_limit_ms / 1000.0) * settings.JUDGE_WALL_TIMEOUT_MULTIPLIER,
                    2.0,
                )
                # Feed stdin — never write hidden inputs into the bind-mounted workspace
                run = self._run_container(
                    host_workspace=host_workspace,
                    command=_java_run_command(memory_limit_mb),
                    time_limit_s=wall,
                    memory_limit_mb=memory_limit_mb,
                    stdin_data=tc["input_data"],
                    work_writable=False,
                    time_limit_ms=time_limit_ms,
                )
                verdict = self._classify_run(run, tc["expected_output"])
                results.append(
                    {
                        "test_case_id": tc["id"],
                        "verdict": verdict,
                        "execution_time_ms": run.execution_time_ms,
                        "stdout_snippet": run.stdout[:2000],
                        "stderr_snippet": run.stderr[:2000],
                    }
                )
                logger.info(
                    "Test case %s verdict=%s time_ms=%s",
                    tc["id"],
                    verdict,
                    run.execution_time_ms,
                )
                if verdict != "Accepted":
                    overall = verdict
                    if not run_all_tests:
                        break

            return {
                "status": overall,
                "compile_error": "",
                "results": results,
            }
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def preview_run(
        self,
        source_code: str,
        stdin: str,
        time_limit_ms: int,
        memory_limit_mb: int,
    ) -> dict:
        """Compile and run once with custom stdin. Does not compare against expected output."""
        self.ensure_image()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        workspace = self.data_dir / job_id
        host_workspace = f"{self.host_data_dir.rstrip('/').rstrip(chr(92))}/{job_id}"
        workspace.mkdir(parents=True, exist_ok=True)
        try:
            _restrict_workspace(workspace)
            (workspace / "Solution.java").write_text(source_code, encoding="utf-8")

            compile_result = self._run_container(
                host_workspace=host_workspace,
                command=["javac", "Solution.java"],
                time_limit_s=settings.JUDGE_COMPILE_TIMEOUT_S,
                memory_limit_mb=memory_limit_mb,
                stdin_data=None,
                work_writable=True,
            )
            if compile_result.timed_out:
                # javac on a normal-sized source never takes this long; it
                # means the host is overloaded, so retry rather than blame.
                raise SandboxError("Compilation timed out")
            if compile_result.exit_code is None:
                raise SandboxError("Compiler container exited without a status")
            if compile_result.exit_code not in (0,):
                err = (compile_result.stderr or compile_result.stdout).strip()
                return {
                    "status": "CompileError",
                    "compile_error": err or "Compilation failed.",
                    "stdout": "",
                    "stderr": err,
                    "execution_time_ms": None,
                }

            try:
                (workspace / "Solution.java").unlink(missing_ok=True)
            except OSError:
                pass

            wall = max(
                (time_limit_ms / 1000.0) * settings.JUDGE_WALL_TIMEOUT_MULTIPLIER,
                2.0,
            )
            # No shell: argv + stdin socket (same path as official judging).
            run = self._run_container(
                host_workspace=host_workspace,
                command=_java_run_command(memory_limit_mb),
                time_limit_s=wall,
                memory_limit_mb=memory_limit_mb,
                stdin_data=stdin if stdin is not None else "",
                work_writable=False,
                time_limit_ms=time_limit_ms,
            )

            # Memory first: a JVM thrashing GC near its heap cap often runs
            # past the time limit before dying of OutOfMemoryError.
            if run.oom_killed or _is_java_oom(run):
                status = "MemoryLimitExceeded"
            elif run.timed_out:
                status = "TimeLimitExceeded"
            elif run.output_limit_exceeded:
                status = "OutputLimitExceeded"
            elif run.exit_code not in (0,):
                status = "RuntimeError"
            else:
                status = "OK"

            return {
                "status": status,
                "compile_error": "",
                "stdout": run.stdout[:8000],
                "stderr": run.stderr[:4000],
                "execution_time_ms": run.execution_time_ms,
            }
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _run_container(
        self,
        host_workspace: str,
        command: list[str],
        time_limit_s: float,
        memory_limit_mb: int,
        stdin_data: str | None,
        work_writable: bool,
        time_limit_ms: int | None = None,
    ) -> RunResult:
        """Run one sandboxed process.

        ``time_limit_s`` is the wall-clock hard kill. ``time_limit_ms``, when
        given, is the problem's limit, checked against the process lifetime
        Docker reports (StartedAt..FinishedAt), so container setup is excluded.
        """
        api = self.client.api
        container_id = None
        sock = None
        pump = None
        wants_stdin = stdin_data is not None
        try:
            host_config = api.create_host_config(
                binds={
                    host_workspace: {
                        "bind": "/work",
                        "mode": "rw" if work_writable else "ro",
                    },
                },
                network_mode="none",
                mem_limit=f"{memory_limit_mb}m",
                # memswap_limit is the combined memory+swap ceiling in bytes.
                # Setting it equal to mem_limit disables swap so MLE fires
                # deterministically instead of degrading into a timeout.
                memswap_limit=memory_limit_mb * 1024 * 1024,
                nano_cpus=1_000_000_000,
                pids_limit=64,
                tmpfs={"/tmp": "size=16m,mode=1777"},
                # Only /tmp (size-capped tmpfs) and, during compile, /work are
                # writable — nothing can grow the container layer on host disk.
                read_only=True,
                # Output is read from the attach stream below; Docker keeps no
                # log file, so a print loop cannot fill the host disk.
                log_config=LogConfig(type=LogConfig.types.NONE),
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                # e.g. "runsc" (gVisor): a user-space kernel between the
                # student's code and the host. Empty uses Docker's default.
                runtime=settings.JUDGE_RUNTIME or None,
            )
            config = api.create_container_config(
                image=self.image,
                command=command,
                user=f"{SANDBOX_UID}:{SANDBOX_UID}",
                working_dir="/work",
                stdin_open=wants_stdin,
                tty=False,
                detach=True,
                host_config=host_config,
                labels={SANDBOX_LABEL: SANDBOX_LABEL_VALUE},
            )
            # Without StdinOnce Docker never closes the process's stdin when we
            # half-close, so EOF-driven readers (Scanner.hasNext) hang until TLE.
            # docker-py has no kwarg for it, hence the raw config edit.
            config["StdinOnce"] = wants_stdin
            container_id = api.create_container_from_config(config)["Id"]

            # Attach before start so no output is missed and stdin is buffered
            # by the daemon — no need to sleep while the JVM boots.
            sock = api.attach_socket(
                container_id,
                params={
                    "stdin": int(wants_stdin),
                    "stdout": 1,
                    "stderr": 1,
                    "stream": 1,
                },
            )
            raw = sock._sock if hasattr(sock, "_sock") else sock
            # docker-py leaves its client timeout (60 s) on this socket. The
            # loop below enforces the wall limit, and the stream ends when the
            # container does, so a quiet program must not time the reader out.
            if hasattr(raw, "settimeout"):
                raw.settimeout(None)
            pump = _OutputPump(raw, settings.JUDGE_OUTPUT_MAX_BYTES)
            pump.start()

            start = time.monotonic()
            api.start(container_id)
            if wants_stdin:
                # On its own thread: sendall() blocks while the program is not
                # reading, and the wall-limit loop must keep running meanwhile.
                feeder = threading.Thread(
                    target=self._feed_stdin, args=(raw, stdin_data), daemon=True
                )
                feeder.start()

            deadline = start + time_limit_s
            state: dict = {}
            killed_for = None
            while True:
                state = api.inspect_container(container_id).get("State", {})
                if state.get("Status") not in ("created", "running"):
                    break
                if pump.overflowed:
                    killed_for = "output"
                elif time.monotonic() >= deadline:
                    killed_for = "wall"
                if killed_for:
                    try:
                        api.kill(container_id)
                    except docker.errors.APIError:
                        pass
                    state = api.inspect_container(container_id).get("State", {})
                    break
                time.sleep(0.05)

            wall_ms = int((time.monotonic() - start) * 1000)
            # The container has exited, so the daemon is closing the stream;
            # wait for the reader to drain it.
            pump.join(timeout=PUMP_DRAIN_TIMEOUT_S)
            if killed_for is None and (pump.is_alive() or not pump.completed):
                # Grading cut-off output would turn a correct answer into
                # WrongAnswer: retry instead.
                raise SandboxError("Output stream did not finish")
            stdout, stderr = pump.text()

            if killed_for == "wall":
                logger.info("Container timed out cmd=%s elapsed_ms=%s", command, wall_ms)
                return RunResult(
                    verdict="TimeLimitExceeded",
                    stdout=stdout,
                    stderr=stderr,
                    execution_time_ms=wall_ms,
                    exit_code=None,
                    timed_out=True,
                )

            stderr, cpu_ms = _split_cpu_marker(stderr)
            # CPU time when the wrapper reported it; otherwise (compile, or
            # output cut off before the marker) the process lifetime.
            elapsed_ms = cpu_ms if cpu_ms is not None else _process_runtime_ms(state)
            if elapsed_ms is None:
                elapsed_ms = wall_ms
            over_limit = time_limit_ms is not None and elapsed_ms > time_limit_ms

            if killed_for == "output" or pump.overflowed:
                return RunResult(
                    verdict="OutputLimitExceeded",
                    stdout=stdout,
                    stderr=(stderr + "\n" + OUTPUT_LIMIT_MESSAGE).lstrip(),
                    execution_time_ms=elapsed_ms,
                    exit_code=state.get("ExitCode"),
                    output_limit_exceeded=True,
                )

            exit_code = state.get("ExitCode")
            return RunResult(
                verdict="OK",
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=elapsed_ms,
                exit_code=exit_code if exit_code is not None else -1,
                timed_out=over_limit,
                oom_killed=bool(state.get("OOMKilled")),
            )
        except docker.errors.APIError as exc:
            logger.exception("Docker API error: %s", exc)
            raise SandboxError(str(exc)) from exc
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            if container_id is not None:
                try:
                    api.remove_container(container_id, force=True)
                except Exception:
                    logger.warning("Failed to remove container", exc_info=True)

    def _feed_stdin(self, raw_sock, stdin_data: str) -> None:
        """Push stdin then half-close so Java sees EOF. Input never hits the workspace FS.

        The socket stays open for reading; the output pump owns it from here.
        """
        try:
            raw_sock.sendall(stdin_data.encode("utf-8"))
            raw_sock.shutdown(socket.SHUT_WR)
        except OSError:
            # The process exited (or closed stdin) before reading everything —
            # legitimate for programs that ignore input. Judge on its output.
            logger.debug("stdin closed early by sandboxed process", exc_info=True)

    def _classify_run(self, run: RunResult, expected_output: str) -> str:
        # Memory first: a JVM thrashing GC near its heap cap often runs past
        # the time limit before dying of OutOfMemoryError. A run killed by the
        # wall timer has no exit code, so it stays TimeLimitExceeded.
        if run.oom_killed or _is_java_oom(run):
            return "MemoryLimitExceeded"
        if run.timed_out:
            return "TimeLimitExceeded"
        if run.output_limit_exceeded:
            # Usually a print in an endless loop; never a correct answer.
            return "OutputLimitExceeded"
        if run.exit_code not in (0,):
            return "RuntimeError"
        if normalize_output(run.stdout) == normalize_output(expected_output):
            return "Accepted"
        return "WrongAnswer"


class _OutputPump(threading.Thread):
    """Demultiplex a non-TTY Docker attach stream into capped stdout/stderr buffers.

    Frames are ``[stream(1) 0 0 0 size(4, big-endian)] payload``. Once the
    combined output passes ``max_bytes`` the pump flags ``overflowed`` and
    discards further data (the caller kills the container).
    """

    def __init__(self, sock, max_bytes: int) -> None:
        super().__init__(daemon=True)
        self._sock = sock
        self._max = max_bytes
        self._bufs = {1: bytearray(), 2: bytearray()}
        self._total = 0
        self.overflowed = False
        # True only once the stream ended normally (EOF), i.e. the output is whole.
        self.completed = False

    def run(self) -> None:
        pending = bytearray()
        try:
            while True:
                chunk = self._sock.recv(65536)
                if not chunk:
                    self.completed = True
                    break
                pending += chunk
                while len(pending) >= 8:
                    size = int.from_bytes(pending[4:8], "big")
                    if len(pending) < 8 + size:
                        break
                    self._append(pending[0], pending[8 : 8 + size])
                    del pending[: 8 + size]
        except OSError:
            pass

    def _append(self, stream: int, payload: bytes) -> None:
        if self.overflowed or stream not in self._bufs:
            return
        room = self._max - self._total
        if len(payload) > room:
            self._bufs[stream] += payload[:room]
            self._total = self._max
            self.overflowed = True
            return
        self._bufs[stream] += payload
        self._total += len(payload)

    def text(self) -> tuple[str, str]:
        return _decode(bytes(self._bufs[1])), _decode(bytes(self._bufs[2]))


def _parse_docker_time(value: str | None) -> datetime | None:
    # Docker emits RFC 3339 with nanoseconds ("...T10:00:00.123456789Z");
    # fromisoformat only takes microseconds.
    if not value or value.startswith("0001-"):
        return None
    value = value.rstrip("Z")
    if "." in value:
        head, frac = value.split(".", 1)
        value = f"{head}.{frac[:6].ljust(6, '0')}"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _process_runtime_ms(state: dict) -> int | None:
    started = _parse_docker_time(state.get("StartedAt"))
    finished = _parse_docker_time(state.get("FinishedAt"))
    if started is None or finished is None or finished < started:
        return None
    return int((finished - started).total_seconds() * 1000)


def _decode(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def normalize_output(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
