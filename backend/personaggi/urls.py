from django.urls import path, include
# from rest_framework.authtoken.views import obtain_auth_token

from . import views, views_staff, views_scommesse, views_carte, views_carte_platform, watch_views
from rest_framework import routers

from rest_framework.routers import DefaultRouter


from .views import AbilitaViewSet, ActivateUserView, DeleteUserView, ChangePasswordView, PersonaggioTransazioniListView, RegisterView, StaffMessageListView, UserViewSet
from .views_negozio_mercante import (
    NegozioMercanteGiocatoreViewSet,
    NegozioMercanteQrListinoView,
    NegozioMercanteStaffViewSet,
    NegozioMercanteVoceStaffViewSet,
)
from .views_staff import (
    QrInspectorView, ApprovaPropostaView, RifiutaPropostaView, ProposteValutazioneList,
    TierStaffViewSet, InventarioStaffViewSet, OggettiSenzaPosizioneView,
    TipologiaEffettoViewSet, EffettoCasualeViewSet, SelezionaEffettoCasualeView,
    MattoniMagiciListView,
    DichiarazioneStaffViewSet,
    StaffQrInventoryScanView,
    StaffMinigiocoQrConfigView,
    StaffMinigiocoBibliotecaView,
    StaffMinigiocoBibliotecaAggiornaView,
    StaffMinigiocoOpenverseRegistraView,
    StaffMinigiocoOpenverseSalvaView,
    StaffMinigiocoOpenverseVerificaView,
    FormulaBuilderSchemaView, FormulaBuilderPreviewView,
    FormulaSemanticOptionsView,
)
from .views_minigioco import MinigiocoQrCompleteView, MinigiocoQrExpireView


from .views import (AbilViewSet,
    AbilitaViewSet, TierViewSet, 
    # MattoneViewSet, 
    PunteggioViewSet, TabellaViewSet,
    AbilitaTierViewSet, AbilitaRequisitoViewSet, AbilitaSbloccataViewSet,
    AbilitaPunteggioViewSet, AbilitaPrerequisitoViewSet,
    MyAuthToken, get_csrf_token, AbilitaAcquistabiliView,	
    PropostaTecnicaViewSet,
    EraViewSet, PrefetturaViewSet, RegioneViewSet,
    KorpViewSet, CarrieraViewSet, SegnoZodiacaleViewSet,
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
router.register(r'negozi-mercante', NegozioMercanteGiocatoreViewSet, basename='negozi-mercante')
router.register(r'staff/negozi-mercante', NegozioMercanteStaffViewSet, basename='staff-negozi-mercante')
router.register(r'staff/negozi-mercante-voci', NegozioMercanteVoceStaffViewSet, basename='staff-negozi-mercante-voci')
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
router.register(r'staff/inventari', views_staff.InventarioStaffViewSet, basename='staff-inventari')
router.register(r'staff/manifesti', views_staff.ManifestoStaffViewSet, basename='staff-manifesti')
router.register(r'staff/nodi', views_staff.NodoStaffViewSet, basename='staff-nodi')
router.register(r'staff/nodi-reward-config', views_staff.NodoRewardConfigStaffViewSet, basename='staff-nodi-reward-config')
router.register(r'staff/innesco-timer', views_staff.InnescoTimerStaffViewSet, basename='staff-innesco-timer')
router.register(r'staff/tipologie-effetto', views_staff.TipologiaEffettoViewSet, basename='staff-tipologie-effetto')
router.register(r'staff/effetti-casuali', views_staff.EffettoCasualeViewSet, basename='staff-effetti-casuali')
router.register(r'staff/dichiarazioni', views_staff.DichiarazioneStaffViewSet, basename='staff-dichiarazioni')
router.register(r'staff/ere', views_staff.EraStaffViewSet, basename='staff-ere')
router.register(r'staff/regioni', views_staff.RegioneStaffViewSet, basename='staff-regioni')
router.register(r'staff/prefetture', views_staff.PrefetturaStaffViewSet, basename='staff-prefetture')
router.register(r'staff/tipi-carriera', views_staff.TipoCarrieraStaffViewSet, basename='staff-tipi-carriera')
router.register(r'staff/carriere', views_staff.CarrieraStaffViewSet, basename='staff-carriere')
router.register(r'staff/cariche', views_staff.CaricaStaffViewSet, basename='staff-cariche')
router.register(
    r'staff/personaggi-carriere-membership',
    views_staff.PersonaggioCarrieraMembershipStaffViewSet,
    basename='staff-personaggi-carriere-membership',
)
router.register(
    r'staff/personaggi',
    views_staff.PersonaggioStaffViewSet,
    basename='staff-personaggi',
)
router.register(
    r'staff/personaggi-eliminati',
    views_staff.PersonaggioEliminatiStaffViewSet,
    basename='staff-personaggi-eliminati',
)
router.register(
    r'staff/regole-transazioni',
    views_staff.RegolaTransazioneCategoriaStaffViewSet,
    basename='staff-regole-transazioni',
)

router.register(r'tipologiepersonaggio', views.TipologiaPersonaggioViewSet)
router.register(r'gestione-personaggi', views.PersonaggioManageViewSet, basename='gestione-personaggi')
router.register(r'ere', EraViewSet, basename='ere')
router.register(r'prefetture', PrefetturaViewSet, basename='prefetture')
router.register(r'regioni', RegioneViewSet, basename='regioni')
router.register(r'korp', KorpViewSet, basename='korp')
router.register(r'carriere', CarrieraViewSet, basename='carriere')
router.register(r'segni-zodiacali', SegnoZodiacaleViewSet, basename='segni-zodiacali')
router.register(r'staff/campagne', views.CampagnaAdminViewSet, basename='staff-campagne')
router.register(r'staff/campagne-utenti', views.CampagnaUtenteAdminViewSet, basename='staff-campagne-utenti')
router.register(r'staff/campagne-feature-policy', views.CampagnaFeaturePolicyAdminViewSet, basename='staff-campagne-feature-policy')
router.register(r'staff/scommesse/sport', views_scommesse.SportScommesseStaffViewSet, basename='staff-scommesse-sport')
router.register(r'staff/scommesse/squadre', views_scommesse.SquadraScommesseStaffViewSet, basename='staff-scommesse-squadre')
router.register(r'staff/scommesse/calendari', views_scommesse.CalendarioScommesseStaffViewSet, basename='staff-scommesse-calendari')
router.register(
    r'staff/scommesse/programmazioni',
    views_scommesse.ProgrammazioneTorneoScommesseStaffViewSet,
    basename='staff-scommesse-programmazioni',
)
router.register(r'staff/carte/espansioni', views_carte.EspansioneCarteStaffViewSet, basename='staff-carte-espansioni')
router.register(r'staff/carte/catalogo', views_carte.CartaCollezionabileStaffViewSet, basename='staff-carte-catalogo')
router.register(r'staff/carte/bustine', views_carte.BustinaCarteStaffViewSet, basename='staff-carte-bustine')
router.register(r'staff/carte/config', views_carte.ConfigurazioneCarteStaffViewSet, basename='staff-carte-config')
router.register(r'staff/carte/keywords', views_carte.KeywordCartaStaffViewSet, basename='staff-carte-keywords')
router.register(r'staff/carte/tags', views_carte.TagCartaStaffViewSet, basename='staff-carte-tags')
router.register(r'staff/carte/combo-reliquiario', views_carte.ComboReliquiarioStaffViewSet, basename='staff-carte-combo-reliquiario')
router.register(r'staff/carte/errata', views_carte.CartaErrataStaffViewSet, basename='staff-carte-errata')
router.register(r'staff/carte/platform/gioco', views_carte_platform.CarteGiocoDefinizioneStaffViewSet, basename='staff-carte-platform-gioco')
router.register(r'staff/carte/platform/templates', views_carte_platform.CarteStudioTemplateStaffViewSet, basename='staff-carte-platform-templates')
router.register(r'staff/carte/platform/packages', views_carte_platform.CarteMsePackageImportStaffViewSet, basename='staff-carte-platform-packages')
router.register(r'staff/carte/platform/ruleset', views_carte_platform.CarteArenaRulesetStaffViewSet, basename='staff-carte-platform-ruleset')
router.register(r'staff/carte/platform/giocatori', views_carte_platform.CartePlatformGiocatoreStaffViewSet, basename='staff-carte-platform-giocatori')
router.register(r'staff/carte/platform/jobs', views_carte_platform.CartePlatformExchangeJobStaffViewSet, basename='staff-carte-platform-jobs')

urlpatterns = [
    path('api/device/watch/pair/start/', watch_views.WatchPairStartView.as_view(), name='watch-pair-start'),
    path('api/device/watch/pair/status/', watch_views.WatchPairStatusView.as_view(), name='watch-pair-status'),
    path('api/device/watch/pair/confirm/', watch_views.WatchPairConfirmView.as_view(), name='watch-pair-confirm'),
    path('api/device/watch/disconnect/', watch_views.WatchDisconnectView.as_view(), name='watch-disconnect'),
    path('api/device/watch/status/', watch_views.WatchBindingStatusView.as_view(), name='watch-status'),
    path('api/device/watch/profile/', watch_views.WatchProfileView.as_view(), name='watch-profile'),
    path('api/device/watch/sync/', watch_views.WatchSyncView.as_view(), name='watch-sync'),
    path('api/device/watch/ota/manifest/', watch_views.WatchOtaManifestView.as_view(), name='watch-ota-manifest'),
    path('api/device/watch/wearos/manifest/', watch_views.WatchWearManifestView.as_view(), name='watch-wearos-manifest'),

    
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
    path(
        'api/minigioco/<uuid:session_id>/complete/',
        MinigiocoQrCompleteView.as_view(),
        name='api_minigioco_complete',
    ),
    path(
        'api/minigioco/<uuid:session_id>/expire/',
        MinigiocoQrExpireView.as_view(),
        name='api_minigioco_expire',
    ),
    
    # path('api/personaggi/', views.PersonaggioListView.as_view(), name='api_personaggio_list'),
    
    path('api/personaggio/me/', views.PersonaggioMeView.as_view(), name='api_personaggio_me'),
    path('api/personaggio/me/crediti/', views.CreditoMovimentoCreateView.as_view(), name='api_crediti_create'),
    path('api/personaggio/me/pc/', views.PuntiCaratteristicaMovimentoCreateView.as_view(), name='api_pc_create'),
    path('api/personaggi/', views.PersonaggioListView.as_view(), name='api_personaggio_list'),
    path('api/personaggi/<int:pk>/', views.PersonaggioDetailView.as_view(), name='api_personaggio_detail'),
    path('api/personaggi/<int:pk>/game_state/', views.PersonaggioGameStateView.as_view(), name='api_personaggio_game_state'),
    path('api/personaggi/<int:pk>/modificatori-dettagliati/', views.PersonaggioModificatoriDettagliatiView.as_view(), name='api_personaggio_modificatori'),

    # --- Viste API Transazioni (Nuove) ---
    path('api/transazioni/sospese/', views.TransazioneSospesaListView.as_view(), name='api_transazioni_sospese'),
    path('api/transazioni/richiedi/', views.TransazioneRichiediView.as_view(), name='api_transazioni_richiedi'),
    path('api/transazioni/<int:pk>/conferma/', views.TransazioneConfermaView.as_view(), name='api_transazioni_conferma'),
    path('api/transazioni/ruba/', views.RubaView.as_view(), name='api_ruba'),
    path('api/transazioni/acquisisci/', views.AcquisisciView.as_view(), name='api_acquisisci'),
    # --- Viste API Transazioni Avanzate ---
    path('api/transazioni/avanzata/', views.TransazioneAvanzataCreateView.as_view(), name='api_transazioni_avanzata_create'),
    path('api/transazioni/<int:pk>/', views.TransazioneDetailView.as_view(), name='api_transazioni_detail'),
    path('api/transazioni/<int:pk>/proposta/', views.PropostaTransazioneCreateView.as_view(), name='api_transazioni_proposta'),
    path('api/abilita/master_list/', views.AbilitaMasterListView.as_view(), name='abilita_master_list'),
    path('api/personaggio/me/acquisisci_abilita/', views.AcquisisciAbilitaView.as_view(), name='acquisisci_abilita'),
    path('api/personaggio/me/revoca_abilita/', views.RevocaAbilitaView.as_view(), name='revoca_abilita'),
    path('api/personaggio/me/abilita_acquistabili/', views.AbilitaAcquistabiliView.as_view(), name='abilita-acquistabili'),
    path('api/punteggi/all/', views.PunteggiListView.as_view(), name='api_punteggi_all'),
    path('api/statistiche/containers/', views.StatisticaContainerListView.as_view(), name='api_statistiche_containers'),
    path('api/cache-revision/', views.CacheRevisionView.as_view(), name='api_cache_revision'),
    path('api/evento-premi/applica/', views.EventoPremiApplicaView.as_view(), name='api_evento_premi_applica'),
    path('api/gioco/evento-stato/', views.EventoGiocoStatoView.as_view(), name='api_gioco_evento_stato'),
    
    # --- MESSAGING ENDPOINTS (Phase 1) ---
    path('api/messaggi/', views.MessaggioListView.as_view(), name='api_messaggi_list'),
    path('api/messaggi/unread_counts/', views.MessaggiUnreadCountsView.as_view(), name='api_messaggi_unread_counts'),
    path('api/messaggi/conversazioni/', views.ConversazioniView.as_view(), name='api_conversazioni'),
    path('api/messaggi/<int:messaggio_id>/rispondi/', views.RispondiMessaggioView.as_view(), name='api_rispondi_messaggio'),
    path('api/messaggi/broadcast/send/', views.MessaggioBroadcastCreateView.as_view(), name='api_messaggi_broadcast_send'),
    path('api/messaggi/admin/sent/', views.MessaggioAdminSentListView.as_view(), name='api_messaggi_admin_sent'),
    path('api/messaggi/<int:pk>/<str:action_type>/', views.MessaggioActionView.as_view(), name='messaggio-azione'),
    path('api/webpush/subscribe/', views.WebPushSubscribeView.as_view(), name='api_webpush_subscribe'),
    
    # Endpoint per Infusioni
    path('api/personaggio/me/infusioni_acquistabili/', views.InfusioniAcquistabiliView.as_view(), name='infusioni_acquistabili'),
    path('api/personaggio/me/acquisisci_infusione/', views.AcquisisciInfusioneView.as_view(), name='acquisisci_infusione'),
    path('api/personaggio/me/revoca_infusione/', views.RevocaInfusioneView.as_view(), name='revoca_infusione'),

    # Endpoint per Tessiture
    path('api/personaggio/me/tessiture_acquistabili/', views.TessitureAcquistabiliView.as_view(), name='tessiture_acquistabili'),
    path('api/personaggio/me/acquisisci_tessitura/', views.AcquisisciTessituraView.as_view(), name='acquisisci_tessitura'),
    path('api/personaggio/me/revoca_tessitura/', views.RevocaTessituraView.as_view(), name='revoca_tessitura'),
    path('api/personaggio/me/toggle_tessitura_favorite/', views.ToggleTessituraFavoriteView.as_view(), name='toggle_tessitura_favorite'),
    path('api/personaggio/me/consuma_consumabile/', views.ConsumaConsumabileView.as_view(), name='consuma_consumabile'),
    path('api/personaggio/me/avvia_creazione_consumabile/', views.AvviaCreazioneConsumabileView.as_view(), name='avvia_creazione_consumabile'),
    path('api/personaggio/me/completa_creazione_consumabile/', views.CompletaCreazioneConsumabileView.as_view(), name='completa_creazione_consumabile'),
    
    # Endpoint per Cerimoniali
    path('api/personaggio/me/cerimoniali_acquistabili/', views.CerimonialiAcquistabiliView.as_view(), name='api_cerimoniali_acquistabili'),
    path('api/personaggio/me/acquisisci_cerimoniale/', views.AcquisisciCerimonialeView.as_view(), name='api_acquisisci_cerimoniale'),
    path('api/personaggio/me/revoca_cerimoniale/', views.RevocaCerimonialeView.as_view(), name='revoca_cerimoniale'),
    
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
    path('api/staff/delete-user/<int:user_id>/', DeleteUserView.as_view(), name='delete-user'),
    path('api/staff/messages/<int:message_id>/leggi/', views.StaffMessageMarkReadView.as_view(), name='staff-message-read'),
    path('api/staff/messages/<int:message_id>/cancella/', views.StaffMessageDeleteView.as_view(), name='staff-message-delete'),
    
    path('api/personaggi/search/', views.PersonaggioAutocompleteView.as_view(), name='personaggio-search'),
    path('api/personaggi/preferred/', views.PreferredPersonaggioView.as_view(), name='personaggio-preferred'),
    path('api/campagne/', views.CampagnaListView.as_view(), name='campagne-list'),
    path('api/campagne/active/', views.ActiveCampagnaValidateView.as_view(), name='campagne-active-validate'),
    path('api/messaggi/send/', views.MessaggioPrivateCreateView.as_view(), name='messaggio-send'),
    
    path('api/oggetti/equipaggia/', views.equipaggia_item_view, name='api_equipaggia_item'),
    path('api/oggetti/danneggia/', views.danneggia_item_view, name='api_danneggia_item'),
    path('api/oggetti/ripara/', views.ripara_item_view, name='api_ripara_item'),
    path('api/oggetti/scarta/', views.scarta_item_view, name='api_scarta_item'),
    path('api/oggetti/assembla/', views.assembla_item_view, name='api_assembla_item'),
    path('api/oggetti/smonta/', views.smonta_item_view, name='smonta_item'),
    path('api/oggetti/forgia/', views.forgia_item_view, name='forgia_item'),
    # ### NUOVO: Endpoint Validazione Assemblaggio (Mancava questo!)
    path('api/assembly/validate/', views.AssemblyValidationView.as_view(), name='api_assembly_validate'),
    path('api/assembly/artisans/', views.CapableArtisansView.as_view(), name='capable-artisans'),
    
    path('api/forging/validate/', views.ForgingValidationView.as_view(), name='validate_forging'),
    path('api/classi_oggetto/', views.ClasseOggettoListView.as_view(), name='lista_classi_oggetto'),
    
    path('api/staff/qr-inspect/<str:qr_id>/', QrInspectorView.as_view(), name='staff-qr-inspect'),
    path(
        'api/staff/minigioco-qr/<str:qr_id>/',
        StaffMinigiocoQrConfigView.as_view(),
        name='staff-minigioco-qr-config',
    ),
    path(
        'api/staff/minigioco-biblioteca/',
        StaffMinigiocoBibliotecaView.as_view(),
        name='staff-minigioco-biblioteca',
    ),
    path(
        'api/staff/minigioco-biblioteca/aggiorna/',
        StaffMinigiocoBibliotecaAggiornaView.as_view(),
        name='staff-minigioco-biblioteca-aggiorna',
    ),
    path(
        'api/staff/minigioco-biblioteca/openverse/salva/',
        StaffMinigiocoOpenverseSalvaView.as_view(),
        name='staff-minigioco-openverse-salva',
    ),
    path(
        'api/staff/minigioco-biblioteca/openverse/registra/',
        StaffMinigiocoOpenverseRegistraView.as_view(),
        name='staff-minigioco-openverse-registra',
    ),
    path(
        'api/staff/minigioco-biblioteca/openverse/verifica/',
        StaffMinigiocoOpenverseVerificaView.as_view(),
        name='staff-minigioco-openverse-verifica',
    ),
    path('api/staff/qr-inventario-scan/', StaffQrInventoryScanView.as_view(), name='staff-qr-inventario-scan'),
    path('api/staff/approva-proposta/<int:proposta_id>/', ApprovaPropostaView.as_view(), name='staff-approva-proposta'),
    
    path('api/staff/proposte/valutazione/', ProposteValutazioneList.as_view(), name='staff-proposte-valutazione'),
    
    path('api/staff/proposta/<int:pk>/rifiuta/', RifiutaPropostaView.as_view(), name='staff-rifiuta-proposta'),
    path('api/staff/proposta/<int:pk>/approva/', ApprovaPropostaView.as_view(), name='staff-approva-proposta'),
    path('api/staff/messages/', StaffMessageListView.as_view(), name='staff-messages'),
    path('api/staff/oggetti-senza-posizione/', views_staff.OggettiSenzaPosizioneView.as_view(), name='staff-oggetti-senza-posizione'),
    path('api/staff/seleziona-effetto-casuale/', SelezionaEffettoCasualeView.as_view(), name='staff-seleziona-effetto-casuale'),
    path('api/staff/mattoni-magici/', MattoniMagiciListView.as_view(), name='staff-mattoni-magici'),
    path('api/staff/formula-builder/schema/', FormulaBuilderSchemaView.as_view(), name='staff-formula-builder-schema'),
    path('api/staff/formula-builder/preview/', FormulaBuilderPreviewView.as_view(), name='staff-formula-builder-preview'),
    path('api/staff/formula-semantic-options/', FormulaSemanticOptionsView.as_view(), name='staff-formula-semantic-options'),
    path('api/staff/risorse-pool/', views.StaffRisorsaPoolListView.as_view(), name='staff-risorse-pool-list'),
    path('api/staff/risorse-pool/incrementa/', views.StaffRisorsaIncrementView.as_view(), name='staff-risorse-pool-incrementa'),

    path('api/scommesse/calendari/', views_scommesse.ScommesseCalendariPlayerView.as_view(), name='scommesse-calendari'),
    path('api/scommesse/calendari/<uuid:calendario_id>/', views_scommesse.ScommesseCalendarioDetailPlayerView.as_view(), name='scommesse-calendario-detail'),
    path('api/scommesse/puntate/', views_scommesse.ScommessePuntataCreateView.as_view(), name='scommesse-puntate-create'),
    path('api/scommesse/mie-puntate/', views_scommesse.ScommesseMiePuntateView.as_view(), name='scommesse-mie-puntate'),
    path('api/scommesse/puntate/<uuid:puntata_id>/riscuoti/', views_scommesse.ScommesseRiscuotiVincitaView.as_view(), name='scommesse-riscuoti-vincita'),
    path('api/scommesse/puntate/<uuid:puntata_id>/ritira-riserva/', views_scommesse.ScommesseRitiraRiservaView.as_view(), name='scommesse-ritira-riserva'),
    path('api/scommesse/codici/genera/', views_scommesse.ScommesseGeneraCodiceView.as_view(), name='scommesse-codici-genera'),
    path('api/scommesse/miei-codici/', views_scommesse.ScommesseMieiCodiciView.as_view(), name='scommesse-miei-codici'),
    path('api/scommesse/config/', views_scommesse.ScommesseConfigPlayerView.as_view(), name='scommesse-config'),
    path('api/scommesse/squadre/<uuid:squadra_id>/storico/', views_scommesse.ScommesseSquadraStoricoView.as_view(), name='scommesse-squadra-storico'),
    path('api/scommesse/classifiche/', views_scommesse.ScommesseClassifichePlayerView.as_view(), name='scommesse-classifiche'),
    path('api/scommesse/sport/<uuid:sport_id>/classifica/', views_scommesse.ScommesseClassificaSportPlayerView.as_view(), name='scommesse-classifica-sport'),
    path('api/staff/scommesse/config/', views_scommesse.ScommesseConfigStaffView.as_view(), name='staff-scommesse-config'),

    path('api/carte/stato/', views_carte.CarteStatoGiocatoreView.as_view(), name='carte-stato'),
    path('api/carte/collezione/', views_carte.CarteCollezionabiliGiocatoreView.as_view(), name='carte-collezione'),
    path('api/carte/apri-bustina/', views_carte.CarteApriBustinaView.as_view(), name='carte-apri-bustina'),
    path('api/carte/reliquiario/', views_carte.CarteReliquiarioView.as_view(), name='carte-reliquiario'),
    path('api/carte/mercato/', views_carte.CarteMercatoView.as_view(), name='carte-mercato'),
    path('api/carte/mercato/accetta/', views_carte.CarteMercatoAccettaView.as_view(), name='carte-mercato-accetta'),
    path('api/carte/mercato/annulla/', views_carte.CarteMercatoAnnullaView.as_view(), name='carte-mercato-annulla'),
    path('api/carte/mazzo/', views_carte.CarteMazzoDuelloView.as_view(), name='carte-mazzo'),
    path('api/carte/duello/', views_carte.CarteDuelloListaView.as_view(), name='carte-duello-lista'),
    path('api/carte/duello/avversari/', views_carte.CarteDuelloAvversariView.as_view(), name='carte-duello-avversari'),
    path('api/carte/duello/invita/', views_carte.CarteDuelloInvitaView.as_view(), name='carte-duello-invita'),
    path('api/carte/duello/accetta/', views_carte.CarteDuelloAccettaView.as_view(), name='carte-duello-accetta-codice'),
    path('api/carte/duello/<uuid:duello_id>/', views_carte.CarteDuelloDettaglioView.as_view(), name='carte-duello-dettaglio'),
    path('api/carte/duello/<uuid:duello_id>/accetta/', views_carte.CarteDuelloAccettaView.as_view(), name='carte-duello-accetta'),
    path('api/carte/duello/<uuid:duello_id>/azione/', views_carte.CarteDuelloAzioneView.as_view(), name='carte-duello-azione'),
    path('api/carte/duello/<uuid:duello_id>/annulla/', views_carte.CarteDuelloAnnullaView.as_view(), name='carte-duello-annulla'),
    path('api/carte/scontro/apri/', views_carte.CarteScontroApriView.as_view(), name='carte-scontro-apri'),
    path('api/carte/scontro/unisciti/', views_carte.CarteScontroUniscitiView.as_view(), name='carte-scontro-unisciti'),
    path('api/carte/scontro/<uuid:duello_id>/prematch/', views_carte.CarteScontroPrematchView.as_view(), name='carte-scontro-prematch'),
    path(
        'api/staff/carte/wiki-regolamento/sync/',
        views_carte.StaffWikiCarteRegolamentoView.as_view(),
        name='staff-carte-wiki-regolamento-sync',
    ),
    path(
        'api/staff/carte/effect-schema/',
        views_carte.StaffCarteEffectSchemaView.as_view(),
        name='staff-carte-effect-schema',
    ),
    path(
        'api/staff/carte/scambi/',
        views_carte.StaffCarteScambiView.as_view(),
        name='staff-carte-scambi',
    ),
    
    path('api/user/me/', views.UserMeView.as_view(), name='user_me_api'),
    
    # Endpoint per associare QR a elementi A_vista
    path('api/a-vista/<int:a_vista_id>/associa-qr/', views.AssociaQrAVistaView.as_view(), name='associa-qr-a-vista'),
    
    path('api/', include(router.urls)),
    
]