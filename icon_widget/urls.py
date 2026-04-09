from django.urls import path
from . import views

app_name = 'icon_widget'
urlpatterns = [
    path('save-icon/', views.download_icon_api, name='save_icon'),
]