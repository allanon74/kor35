from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest
from .models import QrCode
import uuid # Importa uuid per il type hinting (opzionale ma pulito)

import qrcode
import io
import base64
from django.utils.html import escape


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


def generate_qr_data_uri(data_string: str) -> str:
    """
    Genera un'immagine QR code dalla stringa data
    e restituisce un Data URI (Base64) da usare in un tag <img>.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,  # Dimensione dei box
        border=4,     # Spessore del bordo
    )
    qr.add_data(data_string)
    qr.make(fit=True)

    # Crea l'immagine (usando Pillow)
    img = qr.make_image(fill_color="black", back_color="white")

    # Salva l'immagine in un buffer in memoria
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    
    # Ottieni i bytes e codificali in Base64
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    # Restituisci il Data URI completo
    return f"data:image/png;base64,{img_base64}"

# VISTA 1: Elenco di tutti i QrCode

def qr_code_list_view(request: HttpRequest) -> HttpResponse:
    """
    Restituisce un HTML con l'elenco di tutti i QR Code.
    Ogni QR code contiene l'ID e mostra il testo sotto.
    """
    
    # Recupera tutti gli oggetti
    qrcodes = QrCode.objects.all().order_by('-data_creazione')
    
    html_items = []
    
    # Stile CSS per i box
    box_style = (
        "display: inline-block; vertical-align: top; "
        "border: 1px solid #ccc; padding: 15px; margin: 10px; "
        "text-align: center; max-width: 250px; word-wrap: break-word;"
    )
    
    for qr in qrcodes:
        qr_id_str = str(qr.id)
        
        # 1. Genera il QR code che contiene l'ID
        qr_img_data_uri = generate_qr_data_uri(qr_id_str)
        
        # 2. Prepara il testo (con escape per sicurezza)
        testo = escape(qr.testo) if qr.testo else "<i>(Nessun testo)</i>"
        
        # 3. Costruisci l'HTML per questo item
        html_items.append(f"""
        <div style="{box_style}">
            <img src="{qr_img_data_uri}" alt="QR Code per {qr_id_str}" width="200" height="200">
            <p style="font-family: monospace; font-size: 12px; margin-top: 10px;">{qr_id_str}</p>
            <p>{testo}</p>
        </div>
        """)
    
    # Unisci tutti gli item
    html_body = "\n".join(html_items)
    
    # Costruisci la pagina finale
    html_response = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <title>Elenco QrCode</title>
        <style>body {{ font-family: sans-serif; padding: 1em; }}</style>
    </head>
    <body>
        <h1>Elenco QrCode</h1>
        <div>
            {html_body if html_body else "<p>Nessun QrCode trovato.</p>"}
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_response)


# VISTA 2: Dettaglio del singolo QrCode
def qr_code_detail_view(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """
    Restituisce l'HTML per un singolo QrCode, identificato dalla sua PK (UUID).
    """
    
    # Recupera il singolo oggetto o restituisce 404
    qr = get_object_or_404(QrCode, pk=pk)
    
    qr_id_str = str(qr.id)
    
    # 1. Genera il QR code
    qr_img_data_uri = generate_qr_data_uri(qr_id_str)
    
    # 2. Prepara il testo
    testo = escape(qr.testo) if qr.testo else "<i>(Nessun testo)</i>"
    
    # Stile CSS per il box
    box_style = (
        "display: inline-block; border: 1px solid #ccc; "
        "padding: 20px; text-align: center;"
    )

    # 3. Costruisci l'HTML per il singolo item
    html_item = f"""
    <div style="{box_style}">
        <img src="{qr_img_data_uri}" alt="QR Code per {qr_id_str}" width="300" height="300">
        <p style="font-family: monospace; font-size: 14px; margin-top: 15px;">{qr_id_str}</p>
        <p style="font-size: 1.2em;">{testo}</p>
    </div>
    """
    
    # Costruisci la pagina finale
    html_response = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <title>Dettaglio QrCode</title>
        <style>body {{ font-family: sans-serif; padding: 1em; }}</style>
    </head>
    <body>
        <h1>Dettaglio QrCode</h1>
        <div>
            {html_item}
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_response)