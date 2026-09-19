from rest_framework.routers import DefaultRouter

from .views import ProblemViewSet

router = DefaultRouter()
router.register("", ProblemViewSet, basename="problem")

urlpatterns = router.urls
