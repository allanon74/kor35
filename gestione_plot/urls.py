from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventoViewSet, QuestMostroViewSet, QuestVistaViewSet, GiornoEventoViewSet, QuestViewSet, PngAssegnatoViewSet

router = DefaultRouter()
router.register(r'eventi', EventoViewSet, basename='eventi')
router.register(r'giorni', GiornoEventoViewSet, basename='giorni')
router.register(r'quests', QuestViewSet, basename='quests')
router.register(r'mostri-istanza', QuestMostroViewSet)
router.register(r'viste-setup', QuestVistaViewSet)
router.register(r'png-assegnati', PngAssegnatoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]