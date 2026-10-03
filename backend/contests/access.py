"""Helpers for contest-gated access to unpublished problems."""

from datetime import timedelta

from django.db.models import DateTimeField, ExpressionWrapper, F, Max, Q, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from contests.models import Contest, ContestParticipant, ContestProblem


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


def practice_problem_ids(user):
    """Problems opened for practice: in a finished contest with
    practice_after_end that the user could see (public, or registered).

    "Finished" counts every time extension, and a problem that is also in a
    contest not yet over for everyone stays closed: a practice verdict there
    would let a contestant test a solution without penalty.
    """
    if not user or not user.is_authenticated:
        return ContestProblem.objects.none().values_list("problem_id", flat=True)
    now = timezone.now()
    last_end = ExpressionWrapper(
        F("end_time")
        + Coalesce(Max("participants__extra_minutes"), 0) * Value(timedelta(minutes=1)),
        output_field=DateTimeField(),
    )
    contests = Contest.objects.annotate(last_end=last_end)
    still_running = contests.filter(last_end__gte=now).values_list("pk", flat=True)
    closed = ContestProblem.objects.filter(contest_id__in=still_running).values_list(
        "problem_id", flat=True
    )
    open_contests = (
        contests.filter(practice_after_end=True, last_end__lt=now)
        .filter(Q(is_public=True) | Q(participants__user=user))
        .values_list("pk", flat=True)
    )
    return (
        ContestProblem.objects.filter(contest_id__in=open_contests)
        .exclude(problem_id__in=closed)
        .values_list("problem_id", flat=True)
    )


def running_contest_with_problem(user, problem) -> Contest | None:
    """A contest running for the user (extension included) that includes
    this problem, or None. Outside the contest a verdict on it would be a
    penalty-free test of a contest solution."""
    contest_ids = _active_participations(user).values_list("contest_id", flat=True)
    return Contest.objects.filter(
        pk__in=contest_ids, contest_problems__problem=problem
    ).first()


def user_can_practice_problem(user, problem) -> bool:
    """True if the user may submit this unpublished problem as practice."""
    return practice_problem_ids(user).filter(problem_id=problem.pk).exists()


def user_can_access_unpublished_problem(user, problem) -> bool:
    """True if the problem is in a contest running for the user, or open for practice."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    contest_ids = _active_participations(user).values_list("contest_id", flat=True)
    if ContestProblem.objects.filter(problem=problem, contest_id__in=contest_ids).exists():
        return True
    return user_can_practice_problem(user, problem)


def unpublished_contest_problem_q(user) -> Q:
    """Q filter: problems in a contest running for the user, or open for practice."""
    if not user or not user.is_authenticated:
        return Q(pk__in=[])
    contest_ids = _active_participations(user).values_list("contest_id", flat=True)
    problem_ids = ContestProblem.objects.filter(
        contest_id__in=contest_ids
    ).values_list("problem_id", flat=True)
    return Q(pk__in=problem_ids) | Q(pk__in=practice_problem_ids(user))
