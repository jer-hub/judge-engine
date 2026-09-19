from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from judge.executor import JudgeExecutor


class ExecutorLimitsTests(SimpleTestCase):
    @patch("judge.executor.docker.from_env")
    def test_create_kwargs_pin_sandbox_limits(self, mocked_from_env):
        client = MagicMock()
        mocked_from_env.return_value = client
        container = MagicMock()
        container.status = "exited"
        container.attrs = {"State": {"ExitCode": 0}}
        container.logs.return_value = b""
        client.containers.create.return_value = container

        executor = JudgeExecutor()
        # Force a short path through _run_container
        with patch.object(executor, "_feed_stdin"):
            executor._run_container(
                host_workspace="/tmp/work",
                command=["java", "Solution"],
                time_limit_s=0.01,
                memory_limit_mb=256,
                stdin_data=None,
                work_writable=False,
            )

        kwargs = client.containers.create.call_args.kwargs
        self.assertEqual(kwargs["mem_limit"], "256m")
        # memswap_limit is total memory+swap ceiling in bytes; equal to mem_limit
        # disables swap so MemoryLimitExceeded fires deterministically.
        self.assertEqual(kwargs["memswap_limit"], 256 * 1024 * 1024)
        self.assertEqual(kwargs["network_mode"], "none")
        self.assertEqual(kwargs["pids_limit"], 64)
        self.assertEqual(kwargs["cap_drop"], ["ALL"])
        self.assertIn("no-new-privileges:true", kwargs["security_opt"])
        self.assertEqual(kwargs["user"], "1000:1000")
