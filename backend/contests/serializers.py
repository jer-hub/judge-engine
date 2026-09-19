from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from problems.models import Problem
from problems.serializers import ProblemListSerializer

from .models import Contest, ContestParticipant, ContestProblem


class ContestProblemSerializer(serializers.ModelSerializer):
    problem = ProblemListSerializer(read_only=True)
    problem_id = serializers.PrimaryKeyRelatedField(
        queryset=Problem.objects.all(),
        source="problem",
        write_only=True,
        required=False,
    )

    class Meta:
        model = ContestProblem
        fields = (
            "id",
            "letter",
            "display_order",
            "points",
            "problem",
            "problem_id",
        )


class ContestProblemWriteSerializer(serializers.Serializer):
    problem_id = serializers.PrimaryKeyRelatedField(queryset=Problem.objects.all())
    letter = serializers.CharField(max_length=4)
    display_order = serializers.IntegerField(min_value=0, required=False, default=0)
    points = serializers.IntegerField(min_value=0, required=False, default=100)


class ContestParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = ContestParticipant
        fields = ("id", "user_id", "username", "registered_at")


class ContestListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    problem_count = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = (
            "id",
            "title",
            "start_time",
            "end_time",
            "is_public",
            "status",
            "freeze_scoreboard_minutes_before_end",
            "problem_count",
        )

    def get_problem_count(self, obj: Contest) -> int:
        return obj.contest_problems.count()


class ContestDetailSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_frozen = serializers.BooleanField(read_only=True)
    problems = ContestProblemSerializer(
        source="contest_problems", many=True, read_only=True
    )
    participants = ContestParticipantSerializer(many=True, read_only=True)
    is_registered = serializers.SerializerMethodField()
    server_time = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = (
            "id",
            "title",
            "description",
            "start_time",
            "end_time",
            "is_public",
            "status",
            "is_frozen",
            "freeze_scoreboard_minutes_before_end",
            "problems",
            "participants",
            "is_registered",
            "server_time",
        )

    def get_is_registered(self, obj: Contest) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return ContestParticipant.objects.filter(
            contest=obj, user=request.user
        ).exists()

    def get_server_time(self, obj: Contest) -> str:
        return timezone.now().isoformat()


def sync_contest_problems(contest: Contest, items: list[dict]) -> None:
    """Replace contest problem set; omit deletes letters not in payload."""
    keep_ids: list[int] = []
    for item in items:
        problem = item["problem_id"]
        letter = item["letter"].strip().upper()
        cp, _ = ContestProblem.objects.update_or_create(
            contest=contest,
            problem=problem,
            defaults={
                "letter": letter,
                "display_order": item.get("display_order", 0),
                "points": item.get("points", 100),
            },
        )
        keep_ids.append(cp.id)
    ContestProblem.objects.filter(contest=contest).exclude(id__in=keep_ids).delete()


class ContestWriteSerializer(serializers.ModelSerializer):
    problems = ContestProblemWriteSerializer(many=True, required=False)
    participant_usernames = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Contest
        fields = (
            "id",
            "title",
            "description",
            "start_time",
            "end_time",
            "is_public",
            "freeze_scoreboard_minutes_before_end",
            "problems",
            "participant_usernames",
        )

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if self.instance is not None:
            start = start if start is not None else self.instance.start_time
            end = end if end is not None else self.instance.end_time
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )
        problems = attrs.get("problems")
        if problems is not None:
            letters = [p["letter"].strip().upper() for p in problems]
            if len(letters) != len(set(letters)):
                raise serializers.ValidationError(
                    {"problems": "Duplicate problem letters are not allowed."}
                )
            problem_ids = [p["problem_id"].id for p in problems]
            if len(problem_ids) != len(set(problem_ids)):
                raise serializers.ValidationError(
                    {"problems": "Duplicate problems are not allowed."}
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        problems = validated_data.pop("problems", None)
        usernames = validated_data.pop("participant_usernames", None)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        contest = Contest.objects.create(**validated_data)
        if problems is not None:
            sync_contest_problems(contest, problems)
        if usernames is not None:
            self._sync_participants(contest, usernames)
        return contest

    @transaction.atomic
    def update(self, instance, validated_data):
        problems = validated_data.pop("problems", None)
        usernames = validated_data.pop("participant_usernames", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if problems is not None:
            sync_contest_problems(instance, problems)
        if usernames is not None:
            self._sync_participants(instance, usernames)
        return instance

    def _sync_participants(self, contest: Contest, usernames: list[str]) -> None:
        from accounts.models import User

        names = [u.strip() for u in usernames if u and u.strip()]
        users = list(User.objects.filter(username__in=names))
        found = {u.username for u in users}
        missing = [n for n in names if n not in found]
        if missing:
            raise serializers.ValidationError(
                {"participant_usernames": f"Unknown users: {', '.join(missing)}"}
            )
        keep_ids = []
        for user in users:
            part, _ = ContestParticipant.objects.get_or_create(
                contest=contest, user=user
            )
            keep_ids.append(part.id)
        ContestParticipant.objects.filter(contest=contest).exclude(
            id__in=keep_ids
        ).delete()

    def to_representation(self, instance):
        return ContestDetailSerializer(instance, context=self.context).data
