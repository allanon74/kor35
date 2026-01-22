from django.urls import path, include
from rest_framework.routers import DefaultRouter

from icon_widget import views

# from personaggi import views_staff
from .views import(
    EventoViewSet, PublicAuraViewSet, PublicTabellaViewSet, PublicTierViewSet, QuestMostroViewSet, 
    QuestVistaViewSet, GiornoEventoViewSet, QuestViewSet, PngAssegnatoViewSet, 
    MostroTemplateViewSet, StaffOffGameViewSet, QuestFaseViewSet, QuestTaskViewSet,
    PaginaRegolamentoSmallViewSet, PaginaRegolamentoViewSet,
    PublicPaginaRegolamentoMenu, PublicPaginaRegolamentoDetail, 
    get_wiki_menu, get_wiki_page, serve_wiki_image, PublicWikiImmagineViewSet, StaffWikiImmagineViewSet,
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
router.register(r'public/wiki-menu', PublicPaginaRegolamentoMenu, basename='public-wiki-menu')
router.register(r'public/wiki-page', PublicPaginaRegolamentoDetail, basename='public-wiki-page')
router.register(r'public/wiki-tabelle', PublicTabellaViewSet, basename='public-wiki-tabelle')
router.register(r'public/wiki-aure', PublicAuraViewSet, basename='public-wiki-aure')
router.register(r'public/wiki-tiers', PublicTierViewSet, basename='public-wiki-tiers')
router.register(r'public/wiki-immagini', PublicWikiImmagineViewSet, basename='public-wiki-immagini')

urlpatterns = [
    path('api/wiki/menu/', get_wiki_menu, name='wiki_menu'),
    path('api/wiki/pagina/<slug:slug>/', get_wiki_page, name='wiki_page'),
    path('api/wiki/image/<slug:slug>/', serve_wiki_image, name='wiki_image'),
    path('api/', include(router.urls)),
]   