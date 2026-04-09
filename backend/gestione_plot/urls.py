from django.urls import path, include
from rest_framework.routers import DefaultRouter

from icon_widget import views

# from personaggi import views_staff
from .views import(
    EventoViewSet, PublicAuraViewSet, PublicTabellaViewSet, PublicTierViewSet, PublicEventiViewSet, QuestMostroViewSet, 
    QuestVistaViewSet, GiornoEventoViewSet, QuestViewSet, PngAssegnatoViewSet, 
    MostroTemplateViewSet, StaffOffGameViewSet, QuestFaseViewSet, QuestTaskViewSet,
    PaginaRegolamentoSmallViewSet, PaginaRegolamentoViewSet,
    PublicPaginaRegolamentoMenu, PublicPaginaRegolamentoDetail, 
    get_wiki_menu, get_wiki_page, get_wiki_tier_display, get_wiki_mattoni_display, get_wiki_image_display, get_wiki_buttons_display, public_wiki_punteggi, serve_wiki_image, PublicWikiImmagineViewSet, StaffWikiImmagineViewSet,
    PublicWikiTierWidgetViewSet, StaffWikiTierWidgetViewSet,
    PublicWikiButtonWidgetViewSet, StaffWikiButtonWidgetViewSet,
    PublicWikiMattoniWidgetViewSet, StaffWikiMattoniWidgetViewSet,
    PublicConfigurazioneSitoViewSet, PublicLinkSocialViewSet,
                   )
from personaggi.views_staff import(
    InfusioneMasterViewSet, 
    TessituraMasterViewSet, 
    CerimonialeMasterViewSet,   
)

router = DefaultRouter()
router.register(r'eventi', EventoViewSet, basename='eventi')
router.register(r'giorni', GiornoEventoViewSet, basename='giorni')
router.register(r'quests', QuestViewSet, basename='quests')
router.register(r'mostri-istanza', QuestMostroViewSet)
router.register(r'viste-setup', QuestVistaViewSet)
router.register(r'png-assegnati', PngAssegnatoViewSet)
router.register(r'fasi', QuestFaseViewSet)
router.register(r'tasks', QuestTaskViewSet)

router.register(r'staff/mostri-templates', MostroTemplateViewSet, basename='mostri-templates') # <--- NUOVA ROUTE
router.register(r'staff/infusioni', InfusioneMasterViewSet, basename='master-infusioni')
router.register(r'staff/tessiture',    TessituraMasterViewSet, basename='master-tessiture')
router.register(r'staff/cerimoniali', CerimonialeMasterViewSet, basename='master-cerimoniali')
router.register(r'staff/staff-offgame', StaffOffGameViewSet)
router.register(r'staff/pagine-regolamento', 
                PaginaRegolamentoViewSet, 
                basename='pagine-regolamento')
router.register(r'staff/pagine-regolamento-small', 
                PaginaRegolamentoSmallViewSet, 
                basename='pagine-regolamento-small')
router.register(r'staff/wiki-immagini', 
                StaffWikiImmagineViewSet, 
                basename='staff-wiki-immagini')
router.register(r'staff/wiki-buttons', 
                StaffWikiButtonWidgetViewSet, 
                basename='staff-wiki-buttons')
router.register(r'staff/wiki-tiers', 
                StaffWikiTierWidgetViewSet, 
                basename='staff-wiki-tiers')
router.register(r'staff/wiki-mattoni',
                StaffWikiMattoniWidgetViewSet,
                basename='staff-wiki-mattoni')
router.register(r'public/wiki-menu', PublicPaginaRegolamentoMenu, basename='public-wiki-menu')
router.register(r'public/wiki-page', PublicPaginaRegolamentoDetail, basename='public-wiki-page')
router.register(r'public/wiki-tabelle', PublicTabellaViewSet, basename='public-wiki-tabelle')
router.register(r'public/wiki-aure', PublicAuraViewSet, basename='public-wiki-aure')
router.register(r'public/wiki-tiers', PublicTierViewSet, basename='public-wiki-tiers')
router.register(r'public/wiki-immagini', PublicWikiImmagineViewSet, basename='public-wiki-immagini')
router.register(r'public/wiki-buttons', PublicWikiButtonWidgetViewSet, basename='public-wiki-buttons')
router.register(r'public/wiki-tier-widgets', PublicWikiTierWidgetViewSet, basename='public-wiki-tier-widgets')
router.register(r'public/wiki-mattoni-widgets', PublicWikiMattoniWidgetViewSet, basename='public-wiki-mattoni-widgets')
router.register(r'public/eventi', PublicEventiViewSet, basename='public-eventi')
router.register(r'public/configurazione-sito', PublicConfigurazioneSitoViewSet, basename='public-configurazione-sito')
router.register(r'public/link-social', PublicLinkSocialViewSet, basename='public-link-social')

urlpatterns = [
    path('api/wiki/menu/', get_wiki_menu, name='wiki_menu'),
    path('api/wiki/pagina/<slug:slug>/', get_wiki_page, name='wiki_page'),
    path('api/wiki/image/<slug:slug>/', serve_wiki_image, name='wiki_image'),
    path('api/wiki/tier-display/<str:key>/', get_wiki_tier_display, name='wiki_tier_display'),
    path('api/wiki/mattoni-display/<str:key>/', get_wiki_mattoni_display, name='wiki_mattoni_display'),
    path('api/wiki/image-display/<str:key>/', get_wiki_image_display, name='wiki_image_display'),
    path('api/wiki/buttons-display/<str:key>/', get_wiki_buttons_display, name='wiki_buttons_display'),
    path('api/wiki/punteggi/', public_wiki_punteggi, name='wiki_punteggi'),
    path('api/', include(router.urls)),
]   