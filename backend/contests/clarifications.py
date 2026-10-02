"""Contest clarifications (student questions) and announcements."""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from .models import Clarification, Contest, ContestParticipant

MAX_TEXT = 2000
# Per student per contest: enough for real questions, not for flooding.
MAX_QUESTIONS_PER_STUDENT = 20


class ClarificationSerializer(serializers.ModelSerializer):
    problem_letter = serializers.CharField(source="problem.letter", read_only=True, default=None)
    is_announcement = serializers.BooleanField(read_only=True)
    mine = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Clarification
        fields = (
            "id",
            "problem_letter",
            "question",
            "answer",
            "is_public",
            "is_announcement",
            "mine",
            "author",
            "created_at",
            "answered_at",
        )

    def _viewer(self):
        request = self.context.get("request")
        return request.user if request else None

    def get_mine(self, obj: Clarification) -> bool:
        viewer = self._viewer()
        return bool(viewer and obj.author_id == viewer.id)

    def get_author(self, obj: Clarification) -> str | None:
        # Who asked is for admins only; classmates see just the question.
        viewer = self._viewer()
        if viewer and getattr(viewer, "is_platform_admin", False):
            return obj.author.username
        return None


def visible_clarifications(contest: Contest, user):
    qs = contest.clarifications.select_related("problem", "author")
    if getattr(user, "is_platform_admin", False):
        return qs
    # Students: published answers and announcements, plus their own questions.
    return qs.filter(Q(is_public=True, answered_at__isnull=False) | Q(author=user))


def _text(data, name: str, required: bool = True) -> str:
    value = data.get(name, "")
    if not isinstance(value, str):
        raise serializers.ValidationError({name: "Must be text."})
    value = value.strip()
    if required and not value:
        raise serializers.ValidationError({name: "Required."})
    if len(value) > MAX_TEXT:
        raise serializers.ValidationError({name: f"At most {MAX_TEXT} characters."})
    return value


def ask_question(contest: Contest, user, data) -> Clarification:
    """A registered student asks during their contest window."""
    participant = ContestParticipant.objects.filter(contest=contest, user=user).first()
    if participant is None:
        raise serializers.ValidationError({"detail": "Register for the contest to ask questions."})
    now = timezone.now()
    if now < contest.start_time or now > contest.end_time_for(user):
        raise serializers.ValidationError({"detail": "Questions are open only during the contest."})
    if contest.clarifications.filter(author=user).count() >= MAX_QUESTIONS_PER_STUDENT:
        raise serializers.ValidationError(
            {"detail": f"You can ask at most {MAX_QUESTIONS_PER_STUDENT} questions per contest."}
        )
    question = _text(data, "question")
    problem = None
    letter = data.get("problem_letter")
    if letter:
        problem = contest.contest_problems.filter(letter__iexact=str(letter).strip()).first()
        if problem is None:
            raise serializers.ValidationError({"problem_letter": "No such problem in this contest."})
    return Clarification.objects.create(
        contest=contest, author=user, problem=problem, question=question
    )


def announce(contest: Contest, admin, data) -> Clarification:
    """An admin message to every contestant."""
    text = _text(data, "answer")
    return Clarification.objects.create(
        contest=contest,
        author=admin,
        answer=text,
        is_public=True,
        answered_by=admin,
        answered_at=timezone.now(),
    )


def answer(clarification: Clarification, admin, data) -> Clarification:
    text = _text(data, "answer")
    is_public = data.get("is_public", False)
    if not isinstance(is_public, bool):
        raise serializers.ValidationError({"is_public": "Must be true or false."})
    clarification.answer = text
    clarification.is_public = is_public
    clarification.answered_by = admin
    clarification.answered_at = timezone.now()
    clarification.save(update_fields=["answer", "is_public", "answered_by", "answered_at"])
    return clarification
