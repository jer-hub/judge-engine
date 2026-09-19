"""Docker-based Java sandbox executor for untrusted student submissions."""
from __future__ import annotations

import logging
import os
import shutil
import socket
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import docker
from django.conf import settings

logger = logging.getLogger("judge")


@dataclass(frozen=True)
class RunResult:
    verdict: str
    stdout: str
    stderr: str
    execution_time_ms: int | None
    exit_code: int | None
    timed_out: bool = False
    oom_killed: bool = False


class JudgeExecutor:
    """Compile and run Java solutions inside ephemeral Docker containers."""

    def __init__(self) -> None:
        self.client = docker.from_env()
        self.image = settings.JUDGE_IMAGE
        self.data_dir = Path(os.environ.get("JUDGE_DATA_DIR", "/judge_data"))
        self.host_data_dir = os.environ.get(
            "JUDGE_HOST_DATA_DIR", str(self.data_dir)
        )

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
    ) -> dict:
        self.ensure_image()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        workspace = self.data_dir / job_id
        host_workspace = f"{self.host_data_dir.rstrip('/').rstrip(chr(92))}/{job_id}"
        workspace.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(workspace, 0o777)
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
                return {
                    "status": "CompileError",
                    "compile_error": "Compilation timed out.",
                    "results": [],
                }
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

            results = []
            overall = "Accepted"
            for tc in test_cases:
                wall = max(
                    (time_limit_ms / 1000.0) * settings.JUDGE_WALL_TIMEOUT_MULTIPLIER,
                    2.0,
                )
                jvm_heap = max(memory_limit_mb - 64, 32)
                # Feed stdin — never write hidden inputs into the bind-mounted workspace
                run = self._run_container(
                    host_workspace=host_workspace,
                    command=["java", f"-Xmx{jvm_heap}m", "Solution"],
                    time_limit_s=wall,
                    memory_limit_mb=memory_limit_mb,
                    stdin_data=tc["input_data"],
                    work_writable=False,
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
            os.chmod(workspace, 0o777)
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
                return {
                    "status": "CompileError",
                    "compile_error": "Compilation timed out.",
                    "stdout": "",
                    "stderr": "",
                    "execution_time_ms": None,
                }
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
            jvm_heap = max(memory_limit_mb - 64, 32)
            # No shell: argv + stdin socket (same path as official judging).
            run = self._run_container(
                host_workspace=host_workspace,
                command=["java", f"-Xmx{jvm_heap}m", "Solution"],
                time_limit_s=wall,
                memory_limit_mb=memory_limit_mb,
                stdin_data=stdin if stdin is not None else "",
                work_writable=False,
            )

            if run.timed_out:
                status = "TimeLimitExceeded"
            elif run.oom_killed:
                status = "MemoryLimitExceeded"
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
    ) -> RunResult:
        container = None
        start = time.monotonic()
        try:
            container = self.client.containers.create(
                image=self.image,
                command=command,
                working_dir="/work",
                volumes={
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
                user="1000:1000",
                stdin_open=stdin_data is not None,
                tty=False,
                detach=True,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
            )
            container.start()

            if stdin_data is not None:
                # Brief delay so the JVM process is ready to accept stdin.
                time.sleep(0.15)
                self._feed_stdin(container, stdin_data)

            deadline = start + time_limit_s
            exit_code = None
            while time.monotonic() < deadline:
                container.reload()
                if container.status not in ("created", "running"):
                    exit_code = container.attrs["State"].get("ExitCode", -1)
                    break
                time.sleep(0.05)
            else:
                try:
                    container.kill()
                except Exception:
                    pass
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logs = self._safe_logs(container)
                logger.info(
                    "Container timed out cmd=%s elapsed_ms=%s", command, elapsed_ms
                )
                return RunResult(
                    verdict="TimeLimitExceeded",
                    stdout=logs["stdout"],
                    stderr=logs["stderr"],
                    execution_time_ms=elapsed_ms,
                    exit_code=None,
                    timed_out=True,
                )

            elapsed_ms = int((time.monotonic() - start) * 1000)
            state = container.attrs.get("State", {})
            oom = bool(state.get("OOMKilled"))
            logs = self._safe_logs(container)

            return RunResult(
                verdict="OK",
                stdout=logs["stdout"],
                stderr=logs["stderr"],
                execution_time_ms=elapsed_ms,
                exit_code=exit_code if exit_code is not None else -1,
                oom_killed=oom,
            )
        except docker.errors.APIError as exc:
            logger.exception("Docker API error: %s", exc)
            return RunResult(
                verdict="RuntimeError",
                stdout="",
                stderr="Internal sandbox error",
                execution_time_ms=None,
                exit_code=None,
            )
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    logger.warning("Failed to remove container", exc_info=True)

    def _feed_stdin(self, container, stdin_data: str) -> None:
        """Push stdin then half-close so Java sees EOF. Input never hits the workspace FS."""
        sock = container.attach_socket(
            params={"stdin": 1, "stream": 1, "stdout": 0, "stderr": 0}
        )
        try:
            raw = sock._sock if hasattr(sock, "_sock") else sock
            payload = stdin_data.encode("utf-8")
            raw.sendall(payload)
            try:
                raw.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def _safe_logs(self, container) -> dict[str, str]:
        try:
            out = container.logs(stdout=True, stderr=False)
            err = container.logs(stdout=False, stderr=True)
            return {"stdout": _decode(out), "stderr": _decode(err)}
        except Exception:
            return {"stdout": "", "stderr": ""}

    def _classify_run(self, run: RunResult, expected_output: str) -> str:
        if run.timed_out:
            return "TimeLimitExceeded"
        if run.oom_killed:
            return "MemoryLimitExceeded"
        if run.verdict == "RuntimeError":
            return "RuntimeError"
        if run.exit_code not in (0,):
            return "RuntimeError"
        if normalize_output(run.stdout) == normalize_output(expected_output):
            return "Accepted"
        return "WrongAnswer"


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
