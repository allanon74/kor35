from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from personaggi import views_staff
from .views import(
    EventoViewSet, QuestMostroViewSet, 
    QuestVistaViewSet, GiornoEventoViewSet, QuestViewSet, PngAssegnatoViewSet, 
    MostroTemplateViewSet, StaffOffGameViewSet,
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

router.register(r'staff/mostri-templates', MostroTemplateViewSet, basename='mostri-templates') # <--- NUOVA ROUTE
router.register(r'staff/infusioni', InfusioneMasterViewSet, basename='master-infusioni')
router.register(r'staff/tessiture',    TessituraMasterViewSet, basename='master-tessiture')
router.register(r'staff/cerimoniali', CerimonialeMasterViewSet, basename='master-cerimoniali')
router.register(r'staff-offgame', StaffOffGameViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]   