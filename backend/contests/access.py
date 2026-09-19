"""Helpers for contest-gated access to unpublished problems."""

from django.db.models import Q
from django.utils import timezone

from contests.models import ContestParticipant, ContestProblem


def user_can_access_unpublished_problem(user, problem) -> bool:
    """True if user is registered for an active contest that includes the problem."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    now = timezone.now()
    return ContestProblem.objects.filter(
        problem=problem,
        contest__start_time__lte=now,
        contest__end_time__gte=now,
        contest__participants__user=user,
    ).exists()


def unpublished_contest_problem_q(user) -> Q:
    """Q filter: problems linked to an active contest the user registered for."""
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    now = timezone.now()
    contest_ids = ContestParticipant.objects.filter(
        user=user,
        contest__start_time__lte=now,
        contest__end_time__gte=now,
    ).values_list("contest_id", flat=True)
    problem_ids = ContestProblem.objects.filter(
        contest_id__in=contest_ids
    ).values_list("problem_id", flat=True)
    return Q(pk__in=problem_ids)
