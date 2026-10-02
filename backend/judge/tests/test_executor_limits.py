import os
import socket
from unittest.mock import MagicMock, patch

import docker
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from judge.executor import (
    JudgeExecutor,
    RunResult,
    SandboxError,
    _java_run_command,
    _OutputPump,
    _process_runtime_ms,
)


def _frame(stream: int, payload: bytes) -> bytes:
    return bytes([stream, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload


class _FakeSock:
    """Feeds pre-built chunks to the pump, then EOF."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def recv(self, _n):
        return self._chunks.pop(0) if self._chunks else b""


def _exited_state(started="2026-10-01T10:00:00.000000000Z",
                  finished="2026-10-01T10:00:00.250000000Z", exit_code=0):
    return {"State": {"Status": "exited", "ExitCode": exit_code,
                      "OOMKilled": False, "StartedAt": started,
                      "FinishedAt": finished}}


class ExecutorLimitsTests(SimpleTestCase):
    def _executor(self, mocked_from_env, state=None):
        client = MagicMock()
        mocked_from_env.return_value = client
        api = client.api
        api.create_container_config.return_value = {}
        api.create_container_from_config.return_value = {"Id": "abc"}
        api.inspect_container.return_value = state or _exited_state()
        return JudgeExecutor(), api

    def _run(self, executor, **overrides):
        kwargs = dict(
            host_workspace="/tmp/work",
            command=["java", "Solution"],
            time_limit_s=1,
            memory_limit_mb=256,
            stdin_data="1 2\n",
            work_writable=False,
        )
        kwargs.update(overrides)
        with patch("judge.executor._OutputPump") as pump_cls, \
                patch.object(executor, "_feed_stdin"):
            pump = pump_cls.return_value
            pump.overflowed = False
            pump.text.return_value = ("3\n", "")
            return executor._run_container(**kwargs)

    @patch("judge.executor.docker.from_env")
    def test_host_config_pins_sandbox_limits(self, mocked_from_env):
        executor, api = self._executor(mocked_from_env)
        self._run(executor)

        kwargs = api.create_host_config.call_args.kwargs
        self.assertEqual(kwargs["mem_limit"], "256m")
        # memswap_limit is total memory+swap ceiling in bytes; equal to mem_limit
        # disables swap so MemoryLimitExceeded fires deterministically.
        self.assertEqual(kwargs["memswap_limit"], 256 * 1024 * 1024)
        self.assertEqual(kwargs["network_mode"], "none")
        self.assertEqual(kwargs["pids_limit"], 64)
        self.assertEqual(kwargs["cap_drop"], ["ALL"])
        self.assertIn("no-new-privileges:true", kwargs["security_opt"])
        self.assertTrue(kwargs["read_only"])
        self.assertEqual(kwargs["log_config"]["Type"], "none")
        self.assertEqual(
            api.create_container_config.call_args.kwargs["user"], "1000:1000"
        )

    @patch("judge.executor.docker.from_env")
    def test_stdin_once_set_so_program_sees_eof(self, mocked_from_env):
        executor, api = self._executor(mocked_from_env)
        self._run(executor)
        config = api.create_container_from_config.call_args.args[0]
        self.assertTrue(config["StdinOnce"])

    @patch("judge.executor.docker.from_env")
    def test_attach_happens_before_start(self, mocked_from_env):
        executor, api = self._executor(mocked_from_env)
        self._run(executor)
        names = [c[0] for c in api.method_calls]
        self.assertLess(names.index("attach_socket"), names.index("start"))

    @patch("judge.executor.docker.from_env")
    def test_runtime_over_problem_limit_is_tle(self, mocked_from_env):
        executor, _ = self._executor(
            mocked_from_env,
            _exited_state(finished="2026-10-01T10:00:01.500000000Z"),
        )
        result = self._run(executor, time_limit_ms=1000)
        self.assertEqual(result.execution_time_ms, 1500)
        self.assertTrue(result.timed_out)
        self.assertEqual(executor._classify_run(result, "3\n"), "TimeLimitExceeded")

    @patch("judge.executor.docker.from_env")
    def test_runtime_within_limit_is_accepted(self, mocked_from_env):
        executor, _ = self._executor(mocked_from_env)
        result = self._run(executor, time_limit_ms=1000)
        self.assertEqual(result.execution_time_ms, 250)
        self.assertEqual(executor._classify_run(result, "3"), "Accepted")

    @patch("judge.executor.docker.from_env")
    def test_output_overflow_kills_container(self, mocked_from_env):
        executor, api = self._executor(mocked_from_env)
        api.inspect_container.side_effect = [
            {"State": {"Status": "running"}},
            _exited_state(exit_code=137),
        ]
        with patch("judge.executor._OutputPump") as pump_cls, \
                patch.object(executor, "_feed_stdin"):
            pump = pump_cls.return_value
            pump.overflowed = True
            pump.text.return_value = ("x" * 10, "")
            result = executor._run_container(
                host_workspace="/tmp/work", command=["java", "Solution"],
                time_limit_s=5, memory_limit_mb=256, stdin_data="",
                work_writable=False,
            )
        api.kill.assert_called_once_with("abc")
        self.assertTrue(result.output_limit_exceeded)
        self.assertEqual(executor._classify_run(result, "x"), "WrongAnswer")

    @patch("judge.executor.docker.from_env")
    def test_feed_stdin_tolerates_early_exit(self, mocked_from_env):
        executor, _ = self._executor(mocked_from_env)
        raw = MagicMock()
        raw.sendall.side_effect = BrokenPipeError()
        executor._feed_stdin(raw, "data")  # must not raise
        raw.shutdown.assert_not_called()

        raw = MagicMock()
        executor._feed_stdin(raw, "data")
        raw.shutdown.assert_called_once_with(socket.SHUT_WR)

    @patch("judge.executor.docker.from_env")
    def test_docker_error_raises_sandbox_error_not_a_verdict(self, mocked_from_env):
        executor, api = self._executor(mocked_from_env)
        api.start.side_effect = docker.errors.APIError("daemon unavailable")
        with self.assertRaises(SandboxError):
            self._run(executor)
        # The container is still cleaned up.
        api.remove_container.assert_called_once_with("abc", force=True)

    @patch("judge.executor.docker.from_env")
    def test_containers_are_labelled_for_orphan_cleanup(self, mocked_from_env):
        executor, api = self._executor(mocked_from_env)
        self._run(executor)
        labels = api.create_container_config.call_args.kwargs["labels"]
        self.assertEqual(labels, {"judge-engine": "sandbox"})

    @patch("judge.executor.docker.from_env")
    def test_java_out_of_memory_is_mle(self, mocked_from_env):
        executor, _ = self._executor(mocked_from_env)
        run = RunResult(
            verdict="OK", stdout="", execution_time_ms=300, exit_code=1,
            stderr='Exception in thread "main" java.lang.OutOfMemoryError: Java heap space',
        )
        self.assertEqual(executor._classify_run(run, "x"), "MemoryLimitExceeded")
        # GC thrashing pushed it past the time limit before the OOM: still MLE.
        slow_oom = RunResult(
            verdict="OK", stdout="", execution_time_ms=4800, exit_code=1, timed_out=True,
            stderr="java.lang.OutOfMemoryError: Java heap space",
        )
        self.assertEqual(executor._classify_run(slow_oom, "x"), "MemoryLimitExceeded")
        wall_killed = RunResult(
            verdict="TimeLimitExceeded", stdout="", stderr="", execution_time_ms=6000,
            exit_code=None, timed_out=True,
        )
        self.assertEqual(executor._classify_run(wall_killed, "x"), "TimeLimitExceeded")
        crashed = RunResult(
            verdict="OK", stdout="", execution_time_ms=300, exit_code=1,
            stderr="java.lang.NullPointerException",
        )
        self.assertEqual(executor._classify_run(crashed, "x"), "RuntimeError")

    @patch("judge.executor.docker.from_env")
    def test_host_data_dir_explicit_absolute_paths(self, mocked_from_env):
        for path in ("/srv/judge_data", "C:/judge/judge_data", "D:\\judge_data"):
            with patch.dict(os.environ, {"JUDGE_HOST_DATA_DIR": path}):
                executor, _ = self._executor(mocked_from_env)
                self.assertEqual(executor.host_data_dir, path)

    @patch("judge.executor.docker.from_env")
    def test_host_data_dir_rejects_relative_path(self, mocked_from_env):
        with patch.dict(os.environ, {"JUDGE_HOST_DATA_DIR": "./judge_data"}):
            executor, _ = self._executor(mocked_from_env)
            with self.assertRaises(ImproperlyConfigured):
                executor.host_data_dir

    @patch("judge.executor.docker.from_env")
    def test_host_data_dir_detected_from_own_mounts(self, mocked_from_env):
        with patch.dict(os.environ, {"JUDGE_HOST_DATA_DIR": "", "JUDGE_DATA_DIR": "/judge_data"}):
            executor, _ = self._executor(mocked_from_env)
            mocked_from_env.return_value.containers.get.return_value.attrs = {
                "Mounts": [
                    {"Destination": "/app", "Source": "/host/backend"},
                    {"Destination": "/judge_data", "Source": "/run/desktop/mnt/host/c/judge_data"},
                ]
            }
            self.assertEqual(executor.host_data_dir, "/run/desktop/mnt/host/c/judge_data")

    def test_run_command_sizes_stack_and_heap(self):
        cmd = _java_run_command(256)
        self.assertEqual(cmd[0], "java")
        self.assertIn("-Xmx192m", cmd)
        self.assertIn("-Xss64m", cmd)
        self.assertEqual(cmd[-1], "Solution")


class OutputPumpTests(SimpleTestCase):
    def test_demuxes_split_frames(self):
        data = _frame(1, b"hello ") + _frame(2, b"warn") + _frame(1, b"world")
        # Split mid-header and mid-payload to exercise reassembly.
        pump = _OutputPump(_FakeSock([data[:3], data[3:13], data[13:]]), 1024)
        pump.run()
        self.assertEqual(pump.text(), ("hello world", "warn"))
        self.assertFalse(pump.overflowed)

    def test_caps_combined_output(self):
        data = _frame(1, b"a" * 6) + _frame(2, b"b" * 6)
        pump = _OutputPump(_FakeSock([data]), 8)
        pump.run()
        self.assertTrue(pump.overflowed)
        self.assertEqual(pump.text(), ("aaaaaa", "bb"))


class RuntimeParseTests(SimpleTestCase):
    def test_nanosecond_timestamps(self):
        state = {"StartedAt": "2026-10-01T10:00:00.123456789Z",
                 "FinishedAt": "2026-10-01T10:00:02.623456789Z"}
        self.assertEqual(_process_runtime_ms(state), 2500)

    def test_unset_timestamps(self):
        state = {"StartedAt": "0001-01-01T00:00:00Z", "FinishedAt": "0001-01-01T00:00:00Z"}
        self.assertIsNone(_process_runtime_ms(state))
