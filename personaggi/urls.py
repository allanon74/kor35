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

app_name = 'personaggi'

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
        path('qrcode/', views.qr_code_html_view, name='qr_code_html_view'),
    
    # NUOVA VISTA 1: Elenco dei QR (../oggetti/qr/)
    path('qr/', views.qr_code_list_view, name='qr_code_list'),
    
    # NUOVA VISTA 2: Dettaglio del singolo QR (../oggetti/qr/<uuid>/)
    path('qr/<str:pk>/', views.qr_code_detail_view, name='qr_code_detail'),
 
    # Definisci il nuovo endpoint
    # L'app React chiamerà: /oggetti/api/qrcode/IL-TUO-ID/   
    path('api/qrcode/<str:qrcode_id>/', views.QrCodeDetailView.as_view(), name='api_qrcode_detail'),
    
    # path('api/personaggi/', views.PersonaggioListView.as_view(), name='api_personaggio_list'),
    
    path('api/personaggio/me/', views.PersonaggioMeView.as_view(), name='api_personaggio_me'),
    path('api/personaggio/me/crediti/', views.CreditoMovimentoCreateView.as_view(), name='api_crediti_create'),
    path('api/personaggio/me/pc/', views.PuntiCaratteristicaMovimentoCreateView.as_view(), name='api_pc_create'),
    path('api/personaggi/', views.PersonaggioListView.as_view(), name='api_personaggio_list'),

    # --- Viste API Transazioni (Nuove) ---
    path('api/transazioni/sospese/', views.TransazioneSospesaListView.as_view(), name='api_transazioni_sospese'),
    path('api/transazioni/richiedi/', views.TransazioneRichiediView.as_view(), name='api_transazioni_richiedi'),
    path('api/transazioni/<int:pk>/conferma/', views.TransazioneConfermaView.as_view(), name='api_transazioni_conferma'),

]