"""Keep a problem's worst-case judging time inside the judge task's budget.

A judge task is stopped after JUDGE_TASK_SOFT_LIMIT_S. Each test may run up
to its wall limit (time limit x JUDGE_WALL_TIMEOUT_MULTIPLIER, at least 2 s),
so a looping solution on a problem with many slow tests could never finish
judging. Refuse such limits when the teacher sets them, not mid-contest.
"""
from django.conf import settings

# Container create/start/remove per test, on top of the wall limit.
CONTAINER_OVERHEAD_S = 2.0
# Headroom below the task's soft limit for DB writes and a slow host.
BUDGET_FRACTION = 0.9


def _per_test_seconds(time_limit_ms: int) -> float:
    wall = max(time_limit_ms / 1000.0 * settings.JUDGE_WALL_TIMEOUT_MULTIPLIER, 2.0)
    return wall + CONTAINER_OVERHEAD_S


def max_test_cases(time_limit_ms: int) -> int:
    budget = settings.JUDGE_TASK_SOFT_LIMIT_S * BUDGET_FRACTION - settings.JUDGE_COMPILE_TIMEOUT_S
    return max(int(budget // _per_test_seconds(time_limit_ms)), 1)


def judge_budget_error(time_limit_ms: int, test_count: int) -> str | None:
    """A message for the teacher if the limits cannot be judged in time."""
    limit = max_test_cases(time_limit_ms)
    if test_count <= limit:
        return None
    return (
        f"With a {time_limit_ms} ms time limit the judge can run at most {limit} "
        f"test cases per submission ({test_count} configured). Lower the time "
        "limit or merge test cases."
    )
