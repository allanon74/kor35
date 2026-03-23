from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SocialPostViewSet, SocialProfileMeViewSet

app_name = "social"

router = DefaultRouter()
router.register(r"posts", SocialPostViewSet, basename="social-posts")
router.register(r"profile/me", SocialProfileMeViewSet, basename="social-profile-me")

urlpatterns = [
    path("", include(router.urls)),
]
