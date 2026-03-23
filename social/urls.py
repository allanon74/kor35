from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SocialPostViewSet, SocialProfileMeView

app_name = "social"

router = DefaultRouter()
router.register(r"posts", SocialPostViewSet, basename="social-posts")

urlpatterns = [
    path("profile/me/", SocialProfileMeView.as_view(), name="social-profile-me"),
    path("", include(router.urls)),
]
