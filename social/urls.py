from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    SocialNotificationsView,
    SocialPostViewSet,
    SocialProfileDetailView,
    SocialProfileMeView,
    SocialPublicPostDetailView,
    SocialStaffEventReportView,
)

app_name = "social"

router = DefaultRouter()
router.register(r"posts", SocialPostViewSet, basename="social-posts")

urlpatterns = [
    path("profile/me/", SocialProfileMeView.as_view(), name="social-profile-me"),
    path("notifications/", SocialNotificationsView.as_view(), name="social-notifications"),
    path("profiles/<int:personaggio_id>/", SocialProfileDetailView.as_view(), name="social-profile-detail"),
    path("public/posts/<slug:slug>/", SocialPublicPostDetailView.as_view(), name="social-public-post-detail"),
    path("staff/event-report/", SocialStaffEventReportView.as_view(), name="social-staff-event-report"),
    path("", include(router.urls)),
]
