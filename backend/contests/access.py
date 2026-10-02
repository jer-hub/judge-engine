"""Helpers for contest-gated access to unpublished problems."""

from datetime import timedelta

from django.db.models import DateTimeField, ExpressionWrapper, F, Q, Value
from django.utils import timezone

from contests.models import ContestParticipant, ContestProblem


def _active_participations(user):
    """The user's registrations in contests running now for them, counting
    their personal time extension past the official end."""
    now = timezone.now()
    personal_end = ExpressionWrapper(
        F("contest__end_time") + F("extra_minutes") * Value(timedelta(minutes=1)),
        output_field=DateTimeField(),
    )
    return (
        ContestParticipant.objects.filter(user=user, contest__start_time__lte=now)
        .annotate(personal_end=personal_end)
        .filter(personal_end__gte=now)
    )


def user_can_access_unpublished_problem(user, problem) -> bool:
    """True if user is registered for a contest, running for them, that includes the problem."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    contest_ids = _active_participations(user).values_list("contest_id", flat=True)
    return ContestProblem.objects.filter(problem=problem, contest_id__in=contest_ids).exists()


def unpublished_contest_problem_q(user) -> Q:
    """Q filter: problems linked to a contest running for the user."""
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    contest_ids = _active_participations(user).values_list("contest_id", flat=True)
    problem_ids = ContestProblem.objects.filter(
        contest_id__in=contest_ids
    ).values_list("problem_id", flat=True)
    return Q(pk__in=problem_ids)
