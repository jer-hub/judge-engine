from rest_framework.routers import DefaultRouter

from .views_users import UserViewSet

router = DefaultRouter()
router.register("", UserViewSet, basename="user")

urlpatterns = router.urls
