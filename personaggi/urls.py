from django.urls import path, include
# from rest_framework.authtoken.views import obtain_auth_token

from . import views, views_staff
from rest_framework import routers

from rest_framework.routers import DefaultRouter


from .views import AbilitaViewSet, ActivateUserView, ChangePasswordView, PersonaggioTransazioniListView, RegisterView, StaffMessageListView, UserViewSet
from .views_staff import QrInspectorView, ApprovaPropostaView, RifiutaPropostaView, ProposteValutazioneList, TierStaffViewSet


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
router.register(r'punteggio', PunteggioViewSet, basename='punteggio')
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

router.register(r'game', views.GameActionsViewSet, basename='game')

router.register(r'timers/active', views.ActiveTimersViewSet, basename='active-timers')

router.register(r'statistiche', views.StatisticaViewSet, basename='statistiche')
router.register(r'staff/infusioni', views_staff.InfusioneMasterViewSet, basename='master-infusioni')
router.register(r'staff/tessiture', views_staff.TessituraMasterViewSet, basename='master-tessiture')
router.register(r'staff/cerimoniali', views_staff.CerimonialeMasterViewSet, basename='master-cerimoniali')
router.register(r'staff/oggetti', views_staff.OggettoStaffViewSet, basename='staff-oggetti')
router.register(r'staff/oggetti-base', views_staff.OggettoBaseStaffViewSet, basename='staff-oggetti-base')
router.register(r'staff/classi-oggetto', views_staff.ClasseOggettoViewSet, basename='staff-classi-oggetto')
router.register(r'staff/abilita', views_staff.AbilitaStaffViewSet, basename='staff-abilita')
router.register(r'staff/tiers', TierStaffViewSet, basename='staff-tiers')

router.register(r'tipologiepersonaggio', views.TipologiaPersonaggioViewSet)
router.register(r'gestione-personaggi', views.PersonaggioManageViewSet, basename='gestione-personaggi')

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
    path('api/personaggi/<int:pk>/modificatori-dettagliati/', views.PersonaggioModificatoriDettagliatiView.as_view(), name='api_personaggio_modificatori'),

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
    
    # Endpoint per Cerimoniali
    path('api/personaggio/me/cerimoniali_acquistabili/', views.CerimonialiAcquistabiliView.as_view(), name='api_cerimoniali_acquistabili'),
    path('api/personaggio/me/acquisisci_cerimoniale/', views.AcquisisciCerimonialeView.as_view(), name='api_acquisisci_cerimoniale'),
    
    # Endpoint per Modelli Aura
    path('api/punteggio/<int:aura_id>/modelli/', views.ModelliAuraListView.as_view(), name='lista_modelli_aura'),
    path('api/personaggio/me/seleziona_modello_aura/', views.SelezionaModelloAuraView.as_view(), name='seleziona_modello_aura'),
    path('api/admin/pending_proposals_count/', views.AdminPendingProposalsView.as_view(), name='admin_pending_count'),
    
    # NUOVI URL (Lazy Loading)
    path('api/personaggio/me/logs/', views.PersonaggioLogsListView.as_view(), name='personaggio-logs'),
    path('api/personaggio/me/transazioni/', views.PersonaggioTransazioniListView.as_view(), name='personaggio-transazioni'),
    
    path('api/user/register/', RegisterView.as_view(), name='register'),
    path('api/user/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('api/staff/activate-user/<int:user_id>/', ActivateUserView.as_view(), name='activate-user'),
    
    path('api/personaggi/search/', views.PersonaggioAutocompleteView.as_view(), name='personaggio-search'),
    path('api/messaggi/send/', views.MessaggioPrivateCreateView.as_view(), name='messaggio-send'),
    
    path('api/oggetti/equipaggia/', views.equipaggia_item_view, name='api_equipaggia_item'),
    path('api/oggetti/assembla/', views.assembla_item_view, name='api_assembla_item'),
    path('api/oggetti/smonta/', views.smonta_item_view, name='smonta_item'),
    path('api/oggetti/forgia/', views.forgia_item_view, name='forgia_item'),
    # ### NUOVO: Endpoint Validazione Assemblaggio (Mancava questo!)
    path('api/assembly/validate/', views.AssemblyValidationView.as_view(), name='api_assembly_validate'),
    
    path('api/assembly/validate/', views.AssemblyValidationView.as_view(), name='api_assembly_validate'), # <-- AGGIUNTO
    path('api/assembly/artisans/', views.CapableArtisansView.as_view(), name='capable-artisans'),
    
    path('api/forging/validate/', views.ForgingValidationView.as_view(), name='validate_forging'),
    path('api/classi_oggetto/', views.ClasseOggettoListView.as_view(), name='lista_classi_oggetto'),
    
    path('api/staff/qr-inspect/<str:qr_id>/', QrInspectorView.as_view(), name='staff-qr-inspect'),
    path('api/staff/approva-proposta/<int:proposta_id>/', ApprovaPropostaView.as_view(), name='staff-approva-proposta'),
    
    path('api/staff/proposte/valutazione/', ProposteValutazioneList.as_view(), name='staff-proposte-valutazione'),
    
    path('api/staff/proposta/<int:pk>/rifiuta/', RifiutaPropostaView.as_view(), name='staff-rifiuta-proposta'),
    path('api/staff/proposta/<int:pk>/approva/', ApprovaPropostaView.as_view(), name='staff-approva-proposta'),
    path('api/staff/messages/', StaffMessageListView.as_view(), name='staff-messages'),
    
    path('api/user/me/', views.UserMeView.as_view(), name='user_me_api'),
    
    path('api/', include(router.urls)),
    
]