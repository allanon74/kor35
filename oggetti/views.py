from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest
from .models import QrCode
import uuid # Importa uuid per il type hinting (opzionale ma pulito)

def qr_code_html_view(request: HttpRequest) -> HttpResponse:
    uuid_str = request.GET.get('id')
    if not uuid_str:
        return HttpResponse("ID non fornito.", status=400)

    try:
        # Convalida e recupera l'oggetto
        qrcode = QrCode.objects.get(id=uuid.UUID(uuid_str))
    except (QrCode.DoesNotExist, ValueError):
        return HttpResponse("QrCode non trovato o ID non valido.", status=404)

    # 2. Recupera il testo. Gestiamo il caso in cui sia None o vuoto (come da modello)
    testo_contenuto = qrcode.testo
    
    if not testo_contenuto:
        testo_html = "<i>(Nessun testo definito per questo QrCode)</i>"
    else:
        # Nota: Se il testo contiene HTML, dovresti fare l'escape
        # Ma presumendo sia testo semplice, lo inseriamo in un paragrafo.
        testo_html = f"<p>{testo_contenuto}</p>" # TODO: Considera l'escape se il testo è user-generated

    # 3. Costruisci la risposta HTML
    html_response = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dettaglio QrCode</title>
        <style>
            body {{ font-family: sans-serif; margin: 2em; }}
        </style>
    </head>
    <body>
        <h1>Contenuto del QrCode</h1>
        <div>
            {testo_html}
        </div>
    </body>
    </html>
    """
    
    # 4. Restituisci la HttpResponse
    return HttpResponse(html_response)
