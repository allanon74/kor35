"""  
URL configuration for kor35 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.conf import settings
from django.conf.urls.static import static
from personaggi import views as personaggi_views

from django.views.decorators.csrf import csrf_exempt
from django_icon_picker import views as icon_picker_views

urlpatterns = [
    path('summernote/', include('django_summernote.urls')), # summernote 28/01/2025
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    re_path(r'^admin/', admin.site.urls),
    # path('icon_picker/', include('django_icon_picker.urls')),
    # path('icon_picker/download-svg/', csrf_exempt(icon_picker_views.download_and_save_svg), name='download_svg_patch'),
    path('icon_picker/download-svg/', personaggi_views.download_icon_patch, name='download_svg_patch'),
    path('icon-widget-api/', include('icon_widget.urls')), # <-- LA NOSTRA APP
    # --- FINE DELLA PATCH URL ---
    path('personaggi/', include('personaggi.urls')),
    path('plot/', include('gestione_plot.urls')),
    # path('oggetti/', include('oggetti.urls', namespace='oggetti')),
    # path('auth/', obtain_auth_token),
    path ('auth/', personaggi_views.MyAuthToken.as_view()),
    path('api/api-token-auth/', obtain_auth_token, name='api_token_auth'),
    
    path("icons/", include("dj_iconify.urls")),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('webpush/', include('webpush.urls')), # Endpoint per il frontend
    re_path(r'^', include('cms.urls')),

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
