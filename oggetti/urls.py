from django.urls import path
from . import views

# È una buona pratica definire un app_name per il namespacing
app_name = 'oggetti'

urlpatterns = [
    # Il pattern URL che hai richiesto: .../oggetti/qrcode/id=<uuid>/
    # <uuid:pk> cattura la parte UUID dell'URL e la passa alla vista
    # come argomento chiamato 'pk'.
    path('qrcode/', views.qr_code_html_view, name='qr_code_html_view'),
    
    # ... altre url della tua app
]