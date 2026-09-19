from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin

from .models import TestCase
from .serializers import TestCaseSerializer


class TestCaseViewSet(viewsets.ModelViewSet):
    """
    Admin-only test case CRUD.

    Includes expected_output for hidden cases — students must never read this.
    Do not copy ProblemViewSet's open-read permission pattern here.
    """

    serializer_class = TestCaseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = TestCase.objects.select_related("problem").all()

    def get_queryset(self):
        qs = super().get_queryset()
        problem_id = self.request.query_params.get("problem")
        if problem_id:
            qs = qs.filter(problem_id=problem_id)
        return qs.order_by("order", "id")

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        """
        Body: {"items": [{"id": 1, "order": 0}, ...]}
        """
        items = request.data.get("items")
        if not isinstance(items, list) or not items:
            return Response(
                {"detail": "items must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ids = [item.get("id") for item in items]
        if any(i is None for i in ids):
            return Response(
                {"detail": "Each item requires an id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            cases = {tc.id: tc for tc in TestCase.objects.filter(id__in=ids)}
            if len(cases) != len(set(ids)):
                return Response(
                    {"detail": "One or more test case ids were not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            problem_ids = {tc.problem_id for tc in cases.values()}
            if len(problem_ids) > 1:
                return Response(
                    {"detail": "All reordered test cases must belong to the same problem."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            for item in items:
                tc = cases[item["id"]]
                tc.order = int(item.get("order", tc.order))
                tc.save(update_fields=["order"])
        return Response({"updated": len(items)})
