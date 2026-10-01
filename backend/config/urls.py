from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views_auth import ThrottledTokenObtainPairView
from config.health import healthz
from accounts.views_logout import LogoutView
from submissions.run_views import RunPreviewResultView, RunPreviewView

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/auth/login/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="token_logout"),
    path("api/auth/", include("accounts.urls")),
    path("api/users/", include("accounts.urls_users")),
    path("api/problems/", include("problems.urls")),
    path("api/test-cases/", include("problems.urls_test_cases")),
    path("api/contests/", include("contests.urls")),
    path("api/submissions/", include("submissions.urls")),
    path("api/runs/", RunPreviewView.as_view(), name="run-preview"),
    path("api/runs/<str:task_id>/", RunPreviewResultView.as_view(), name="run-preview-result"),
]
