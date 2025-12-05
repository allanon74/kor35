from django.urls import path, include
# from rest_framework.authtoken.views import obtain_auth_token

from . import views
from rest_framework import routers

from rest_framework.routers import DefaultRouter


from .views import AbilitaViewSet, PersonaggioTransazioniListView, UserViewSet


from .views import (AbilViewSet,
    AbilitaViewSet, TierViewSet, 
    # MattoneViewSet, 
    PunteggioViewSet, TabellaViewSet,
    AbilitaTierViewSet, AbilitaRequisitoViewSet, AbilitaSbloccataViewSet,
    AbilitaPunteggioViewSet, AbilitaPrerequisitoViewSet,
    MyAuthToken, get_csrf_token, AbilitaAcquistabiliView,	
    PropostaTecnicaViewSet,
)

app_name = 'personaggi'

router = DefaultRouter()
router.register(r'abilita', AbilitaViewSet)
router.register(r'abil', AbilViewSet, basename='abil')
router.register(r'tier', TierViewSet)
# router.register(r'mattone', MattoneViewSet)
router.register(r'punteggio', PunteggioViewSet)
router.register(r'tabella', TabellaViewSet)
router.register(r'abilita-tier', AbilitaTierViewSet)
router.register(r'abilita-requisito', AbilitaRequisitoViewSet)
router.register(r'abilita-sbloccata', AbilitaSbloccataViewSet)
router.register(r'abilita-punteggio', AbilitaPunteggioViewSet)
router.register(r'abilita-prerequisito', AbilitaPrerequisitoViewSet)
router.register(r'proposte', PropostaTecnicaViewSet, basename='proposte')

# --- ROTTE AGGIUNTE PER NEGOZIO E CRAFTING ---
router.register(r'negozio', views.NegozioViewSet, basename='negozio')
router.register(r'crafting', views.CraftingViewSet, basename='crafting')
# ---------------------------------------------

# router.register('abil', AbilViewSet)
router.register('users', UserViewSet)
router.register(r'oggetti', views.OggettoViewSet, basename='oggetti') # Era fuori router, meglio dentro

router.register(r'richieste-assemblaggio', views.RichiestaAssemblaggioViewSet, basename='richieste-assemblaggio') # <-- AGGIUNTO

urlpatterns = [
    
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
    path('api/personaggi/<int:pk>/', views.PersonaggioDetailView.as_view(), name='api_personaggio_detail'),

    # --- Viste API Transazioni (Nuove) ---
    path('api/transazioni/sospese/', views.TransazioneSospesaListView.as_view(), name='api_transazioni_sospese'),
    path('api/transazioni/richiedi/', views.TransazioneRichiediView.as_view(), name='api_transazioni_richiedi'),
    path('api/transazioni/<int:pk>/conferma/', views.TransazioneConfermaView.as_view(), name='api_transazioni_conferma'),
    path('api/transazioni/ruba/', views.RubaView.as_view(), name='api_ruba'),
    path('api/transazioni/acquisisci/', views.AcquisisciView.as_view(), name='api_acquisisci'),
    path('api/abilita/master_list/', views.AbilitaMasterListView.as_view(), name='abilita_master_list'),
    path('api/personaggio/me/acquisisci_abilita/', views.AcquisisciAbilitaView.as_view(), name='acquisisci_abilita'),
    path('api/personaggio/me/abilita_acquistabili/', views.AbilitaAcquistabiliView.as_view(), name='abilita-acquistabili'),
    path('api/punteggi/all/', views.PunteggiListView.as_view(), name='api_punteggi_all'),
    
    # --- MESSAGING ENDPOINTS (Phase 1) ---
    path('api/messaggi/', views.MessaggioListView.as_view(), name='api_messaggi_list'),
    path('api/messaggi/broadcast/send/', views.MessaggioBroadcastCreateView.as_view(), name='api_messaggi_broadcast_send'),
    path('api/messaggi/admin/sent/', views.MessaggioAdminSentListView.as_view(), name='api_messaggi_admin_sent'),
    path('api/messaggi/<int:pk>/<str:action_type>/', views.MessaggioActionView.as_view(), name='messaggio-azione'),
    path('api/webpush/subscribe/', views.WebPushSubscribeView.as_view(), name='api_webpush_subscribe'),
    
    # Endpoint per Infusioni
    path('api/personaggio/me/infusioni_acquistabili/', views.InfusioniAcquistabiliView.as_view(), name='infusioni_acquistabili'),
    path('api/personaggio/me/acquisisci_infusione/', views.AcquisisciInfusioneView.as_view(), name='acquisisci_infusione'),

    # Endpoint per Tessiture
    path('api/personaggio/me/tessiture_acquistabili/', views.TessitureAcquistabiliView.as_view(), name='tessiture_acquistabili'),
    path('api/personaggio/me/acquisisci_tessitura/', views.AcquisisciTessituraView.as_view(), name='acquisisci_tessitura'),
    
    # Endpoint per Modelli Aura
    path('api/punteggio/<int:aura_id>/modelli/', views.ModelliAuraListView.as_view(), name='lista_modelli_aura'),
    path('api/personaggio/me/seleziona_modello_aura/', views.SelezionaModelloAuraView.as_view(), name='seleziona_modello_aura'),
    path('api/admin/pending_proposals_count/', views.AdminPendingProposalsView.as_view(), name='admin_pending_count'),
    
    # NUOVI URL (Lazy Loading)
    path('api/personaggio/me/logs/', views.PersonaggioLogsListView.as_view(), name='personaggio-logs'),
    path('api/personaggio/me/transazioni/', views.PersonaggioTransazioniListView.as_view(), name='personaggio-transazioni'),
    
    path('api/personaggi/search/', views.PersonaggioAutocompleteView.as_view(), name='personaggio-search'),
    path('api/messaggi/send/', views.MessaggioPrivateCreateView.as_view(), name='messaggio-send'),
    
    path('api/oggetti/equipaggia/', views.equipaggia_item_view, name='api_equipaggia_item'),
    path('api/oggetti/assembla/', views.assembla_item_view, name='api_assembla_item'),
    # ### NUOVO: Endpoint Validazione Assemblaggio (Mancava questo!)
    path('api/assembly/validate/', views.AssemblyValidationView.as_view(), name='api_assembly_validate'),
    
    path('api/assembly/validate/', views.AssemblyValidationView.as_view(), name='api_assembly_validate'), # <-- AGGIUNTO
    path('api/assembly/artisans/', views.CapableArtisansView.as_view(), name='capable-artisans'),
    
    path('api/', include(router.urls)),
    
]