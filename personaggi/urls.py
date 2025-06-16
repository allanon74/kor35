from django.urls import path, include
# from rest_framework.authtoken.views import obtain_auth_token

from . import views
from rest_framework import routers

from rest_framework.routers import DefaultRouter


from .views import AbilitaViewSet, UserViewSet


from .views import (AbilViewSet,
    AbilitaViewSet, TierViewSet, SpellViewSet, MattoneViewSet, PunteggioViewSet, TabellaViewSet,
    AbilitaTierViewSet, AbilitaRequisitoViewSet, AbilitaSbloccataViewSet,
    AbilitaPunteggioViewSet, AbilitaPrerequisitoViewSet,
    SpellMattoneViewSet, SpellElementoViewSet, MyAuthToken, get_csrf_token	
)

router = DefaultRouter()
router.register(r'abilita', AbilitaViewSet)
router.register(r'abil', AbilViewSet, basename='abil')
router.register(r'tier', TierViewSet)
router.register(r'spell', SpellViewSet)
router.register(r'mattone', MattoneViewSet)
router.register(r'punteggio', PunteggioViewSet)
router.register(r'tabella', TabellaViewSet)
router.register(r'abilita-tier', AbilitaTierViewSet)
router.register(r'abilita-requisito', AbilitaRequisitoViewSet)
router.register(r'abilita-sbloccata', AbilitaSbloccataViewSet)
router.register(r'abilita-punteggio', AbilitaPunteggioViewSet)
router.register(r'abilita-prerequisito', AbilitaPrerequisitoViewSet)
router.register(r'spell-mattone', SpellMattoneViewSet)
router.register(r'spell-elemento', SpellElementoViewSet)



# router.register('abil', AbilViewSet)
router.register('users', UserViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('auth/', MyAuthToken.as_view()),
    path('csrf/', get_csrf_token),

]