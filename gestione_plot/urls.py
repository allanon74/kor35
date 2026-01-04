from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventoViewSet, QuestMostroViewSet, QuestVistaViewSet

router = DefaultRouter()
router.register(r'eventi', EventoViewSet, basename='eventi')
router.register(r'mostri-istanza', QuestMostroViewSet)
router.register(r'viste-setup', QuestVistaViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]