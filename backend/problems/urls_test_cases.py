from rest_framework.routers import DefaultRouter

from .views_test_cases import TestCaseViewSet

router = DefaultRouter()
router.register("", TestCaseViewSet, basename="testcase")

urlpatterns = router.urls
