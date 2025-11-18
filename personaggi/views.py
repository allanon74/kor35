import string
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest

from .models import OggettoInInventario, Abilita, Tier
from .models import QrCode
from .models import Oggetto, Attivata, Manifesto, A_vista, Inventario
from .models import Personaggio, TransazioneSospesa, CreditoMovimento, PuntiCaratteristicaMovimento
from .models import Punteggio, CARATTERISTICA
import uuid # Importa uuid per il type hinting (opzionale ma pulito)

from .models import STATO_TRANSAZIONE_IN_ATTESA, STATO_TRANSAZIONE_ACCETTATA, STATO_TRANSAZIONE_RIFIUTATA, STATO_TRANSAZIONE_CHOICES

import qrcode
import io
import base64
from django.utils.html import escape

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status, permissions
from rest_framework.authtoken.admin import User
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from rest_framework import generics
from django.db import transaction
from .serializers import AbilitaMasterListSerializer


from .serializers import (
    OggettoSerializer, AttivataSerializer, 
    ManifestoSerializer, A_vistaSerializer, 
    InventarioSerializer,
    PersonaggioDetailSerializer, # <-- Nuovo
    CreditoMovimentoCreateSerializer, PersonaggioListSerializer, # <-- Nuovo
    PuntiCaratteristicaMovimentoCreateSerializer, # <-- Nuovo
    TransazioneCreateSerializer, # <-- Nuovo
    TransazioneSospesaSerializer, # <-- Nuovo
    TransazioneConfermaSerializer, #
    RubaSerializer, 
    AcquisisciSerializer,
    PunteggioDetailSerializer,
)

from personaggi.serializers import PersonaggioPublicSerializer




from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.http import JsonResponse
import requests
import os
from django.conf import settings

PARAMETRO_SCONTO_ABILITA = 'rid_cos_ab'


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


# --- MODIFICA 1: Login che restituisce info utente ---
class MyAuthToken(ObtainAuthToken):
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'is_staff': user.is_staff or user.is_superuser # Fondamentale per il frontend
        })
# ----------------------------------------------------

from .models import (
    Abilita, Tier, Punteggio, Tabella,
    abilita_tier, abilita_requisito, abilita_sbloccata,
    abilita_punteggio, abilita_prerequisito,
)
from .serializers import (
    AbilSerializer, AbilitaSerializer, AbilitaUpdateSerializer, TierSerializer, 
    # MattoneSerializer, 
    PunteggioSerializer, TabellaSerializer,
    AbilitaTierSerializer, AbilitaRequisitoSerializer, AbilitaSbloccataSerializer,
    AbilitaPunteggioSerializer, AbilitaPrerequisitoSerializer, UserSerializer
)

class AbilitaViewSet(viewsets.ModelViewSet):
    queryset = Abilita.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = AbilitaSerializer

class AbilViewSet(viewsets.ModelViewSet):
    queryset = Abilita.objects.all()
    authentication_classes = (TokenAuthentication,)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AbilitaUpdateSerializer
        return AbilSerializer

class TierViewSet(viewsets.ModelViewSet):
    queryset = Tier.objects.all()
    serializer_class = TierSerializer
    authentication_classes = (TokenAuthentication,)


# class MattoneViewSet(viewsets.ModelViewSet):
#     queryset = Mattone.objects.all()
#     serializer_class = MattoneSerializer
#     authentication_classes = (TokenAuthentication,)

class PunteggioViewSet(viewsets.ModelViewSet):
    queryset = Punteggio.objects.all()
    serializer_class = PunteggioSerializer
    authentication_classes = (TokenAuthentication,)

class TabellaViewSet(viewsets.ModelViewSet):
    queryset = Tabella.objects.all()
    serializer_class = TabellaSerializer
    authentication_classes = (TokenAuthentication,)

# THROUGH VIEWSETS

class AbilitaTierViewSet(viewsets.ModelViewSet):
    queryset = abilita_tier.objects.all()
    serializer_class = AbilitaTierSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaRequisitoViewSet(viewsets.ModelViewSet):
    queryset = abilita_requisito.objects.all()
    serializer_class = AbilitaRequisitoSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaSbloccataViewSet(viewsets.ModelViewSet):
    queryset = abilita_sbloccata.objects.all()
    serializer_class = AbilitaSbloccataSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaPunteggioViewSet(viewsets.ModelViewSet):
    queryset = abilita_punteggio.objects.all()
    serializer_class = AbilitaPunteggioSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaPrerequisitoViewSet(viewsets.ModelViewSet):
    queryset = abilita_prerequisito.objects.all()
    serializer_class = AbilitaPrerequisitoSerializer
    authentication_classes = (TokenAuthentication,)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, )

class AbilitaMasterListView(generics.ListAPIView):
    """
    GET /api/abilita/master_list/
    Restituisce l'elenco completo di tutte le abilità con i dati
    necessari per il calcolo dei requisiti e per i popup di dettaglio.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AbilitaMasterListSerializer
    
    # Ottimizziamo la query per includere tutti i dati relazionati
    queryset = Abilita.objects.select_related(
        'caratteristica'
    ).prefetch_related(
        'abilita_requisito_set__requisito', 
        'abilita_prerequisiti__prerequisito',
        'abilita_punteggio_set__punteggio',
        'abilitastatistica_set__statistica',
    ).order_by('nome')


class AcquisisciAbilitaView(APIView):
    """
    POST /api/personaggio/me/acquisisci_abilita/
    Esegue l'acquisto di un'abilità per il personaggio loggato.
    applicando gli sconti PARAMETRO_SCONTO_ABILITA SOLO ai crediti.
    Richiede: {"abilita_id": <id>}
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic # Assicura che l'intera operazione fallisca o riesca
    def post(self, request, format=None):
        try:
            personaggio = Personaggio.objects.select_related('tipologia').get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )

        abilita_id = request.data.get('abilita_id')
        if not abilita_id:
            return Response({"error": "abilita_id mancante."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            abilita = Abilita.objects.prefetch_related(
                'abilita_requisito_set__requisito', 
                'abilita_prerequisiti'
            ).get(id=abilita_id)
        except Abilita.DoesNotExist:
            return Response({"error": "Abilità non trovata."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Controllo: Già posseduta?
        if personaggio.abilita_possedute.filter(id=abilita_id).exists():
            return Response({"error": "Abilità già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Controllo: Requisiti di Punteggio
        character_scores = personaggio.caratteristiche_base
        for req in abilita.abilita_requisito_set.all():
            punteggio_nome = req.requisito.nome
            valore_richiesto = req.valore
            punteggio_pg = character_scores.get(punteggio_nome, 0)
            
            if punteggio_pg < valore_richiesto:
                return Response(
                    {"error": f"Requisito non soddisfatto: {punteggio_nome} {valore_richiesto} (possiedi {punteggio_pg})"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 3. Controllo: Prerequisiti di Abilità
        required_prereqs = [p.prerequisito for p in abilita.abilita_prerequisiti.all()]
        if required_prereqs:
            possessed_skill_ids = set(personaggio.abilita_possedute.values_list('id', flat=True))
            for prereq in required_prereqs:
                if prereq.id not in possessed_skill_ids:
                    return Response(
                        {"error": f"Prerequisito non soddisfatto: {prereq.nome}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 4. Controllo: Costi
# 4a. Calcola il valore dello sconto
        mods = personaggio.modificatori_calcolati
        # Usa la nuova costante 'rid_cos_ab'
        sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {'add': 0, 'mol': 1.0}) 
        
        sconto_valore = max(0, sconto_stat.get('add', 0)) 
        sconto_percent = Decimal(sconto_valore) / Decimal(100)
        moltiplicatore_costo = Decimal(1) - sconto_percent

        # 4b. Calcola i costi finali
        
        # --- MODIFICA CHIAVE ---
        # Il costo in PC NON è scontato
        costo_pc_finale = abilita.costo_pc 
        # --- FINE MODIFICA ---

        # Il costo in Crediti È scontato
        costo_crediti_base = Decimal(abilita.costo_crediti)
        costo_crediti_finale = (costo_crediti_base * moltiplicatore_costo).quantize(Decimal('0.01')) # Arrotonda a 2 decimali

        # 4c. Controlla se il personaggio ha abbastanza fondi
        if personaggio.punti_caratteristica < costo_pc_finale:
            return Response({"error": f"Punti Caratteristica insufficenti. Richiesti: {costo_pc_finale}"}, status=status.HTTP_400_BAD_REQUEST) 
        
        if personaggio.crediti < costo_crediti_finale:
            return Response({"error": f"Crediti insufficenti. Richiesti: {costo_crediti_finale} (Costo base: {abilita.costo_crediti}, Sconto: {sconto_valore}%)"}, status=status.HTTP_400_BAD_REQUEST)

        # --- 5. Esecuzione Acquisto (BLOCCO MODIFICATO) ---
        
        # Addebita i costi finali (solo crediti scontati)
        personaggio.modifica_pc(-costo_pc_finale, f"Acquisito abilità: {abilita.nome} (Costo: {costo_pc_finale} PC)")
        personaggio.modifica_crediti(-costo_crediti_finale, f"Acquisito abilità: {abilita.nome} (Costo: {costo_crediti_finale} Crediti)")
        personaggio.abilita_possedute.add(abilita)
        
        # Restituisce i dati aggiornati del personaggio
        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcquisisciAbilitaView(APIView):
    """
    POST /api/personaggio/me/acquisisci_abilita/
    Esegue l'acquisto di un'abilità per il personaggio specificato.
    Richiede: {"abilita_id": <id>, "personaggio_id": <id_personaggio>}
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic # Assicura che l'intera operazione fallisca o riesca
    def post(self, request, format=None):
        
        # 1. Recupera ID e controlla la presenza del personaggio_id
        personaggio_id = request.data.get('personaggio_id')
        abilita_id = request.data.get('abilita_id')
        
        if not personaggio_id:
            return Response(
                {"error": "L'ID del personaggio è richiesto (personaggio_id)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not abilita_id:
            return Response({"error": "abilita_id mancante."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # FIX CHIAVE: Filtra per ID specifico e proprietario
            personaggio = Personaggio.objects.select_related('tipologia').get(
                id=personaggio_id,
                proprietario=request.user
            )
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Personaggio non trovato o non appartenente all'utente."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Personaggio.MultipleObjectsReturned:
            # Gestione di sicurezza in più, anche se impossibile con un ID univoco
            return Response(
                {"error": "Errore interno: Trovati personaggi multipli con lo stesso ID."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            abilita = Abilita.objects.prefetch_related(
                'abilita_requisito_set__requisito', 
                'abilita_prerequisiti'
            ).get(id=abilita_id)
        except Abilita.DoesNotExist:
            return Response({"error": "Abilità non trovata."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Controllo: Già posseduta?
        if personaggio.abilita_possedute.filter(id=abilita_id).exists():
            return Response({"error": "Abilità già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Controllo: Requisiti di Punteggio
        character_scores = personaggio.caratteristiche_base
        for req in abilita.abilita_requisito_set.all():
            punteggio_nome = req.requisito.nome
            valore_richiesto = req.valore
            punteggio_pg = character_scores.get(punteggio_nome, 0)
            
            if punteggio_pg < valore_richiesto:
                return Response(
                    {"error": f"Requisito non soddisfatto: {punteggio_nome} {valore_richiesto} (possiedi {punteggio_pg})"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 3. Controllo: Prerequisiti di Abilità
        required_prereqs = [p.prerequisito for p in abilita.abilita_prerequisiti.all()]
        if required_prereqs:
            possessed_skill_ids = set(personaggio.abilita_possedute.values_list('id', flat=True))
            for prereq in required_prereqs:
                if prereq.id not in possessed_skill_ids:
                    return Response(
                        {"error": f"Prerequisito non soddisfatto: {prereq.nome}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # 4. Controllo: Costi
        mods = personaggio.modificatori_calcolati
        sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {'add': 0, 'mol': 1.0}) 
        sconto_valore = max(0, sconto_stat.get('add', 0)) 
        sconto_percent = Decimal(sconto_valore) / Decimal(100)
        moltiplicatore_costo = Decimal(1) - sconto_percent

        costo_pc_finale = abilita.costo_pc 
        costo_crediti_base = Decimal(abilita.costo_crediti)
        costo_crediti_finale = (costo_crediti_base * moltiplicatore_costo).quantize(Decimal('0.01'))

        if personaggio.punti_caratteristica < costo_pc_finale:
            return Response({"error": f"Punti Caratteristica insufficenti. Richiesti: {costo_pc_finale}"}, status=status.HTTP_400_BAD_REQUEST) 
        
        if personaggio.crediti < costo_crediti_finale:
            return Response({"error": f"Crediti insufficenti. Richiesti: {costo_crediti_finale} (Costo base: {abilita.costo_crediti}, Sconto: {sconto_valore}%)"}, status=status.HTTP_400_BAD_REQUEST)

        # --- 5. Esecuzione Acquisto ---
        personaggio.modifica_pc(-costo_pc_finale, f"Acquisito abilità: {abilita.nome} (Costo: {costo_pc_finale} PC)")
        personaggio.modifica_crediti(-costo_crediti_finale, f"Acquisito abilità: {abilita.nome} (Costo: {costo_crediti_finale} Crediti)")
        personaggio.abilita_possedute.add(abilita)
        
        # Restituisce i dati aggiornati del personaggio
        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    
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
def qr_code_detail_view(request: HttpRequest, pk: string) -> HttpResponse:
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

class QrCodeDetailView(APIView):
    """
    Vista API per recuperare i dettagli di un QrCode.
    Accetta un ID QrCode e restituisce il JSON dell'oggetto
    A_vista collegato (Oggetto, Attivata, Manifesto, ecc.).
    """
    
    def get(self, request, qrcode_id, format=None):
        try:
            # 1. Trova il QrCode, ottimizzando la query per includere 'vista'
            qr_code = QrCode.objects.select_related('vista').get(id=qrcode_id)
        except QrCode.DoesNotExist:
            return Response(
                {"error": "QrCode non trovato."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        vista_obj = qr_code.vista
        
        if vista_obj is None:
            # QrCode valido ma non collegato a nulla
            return Response(
                {
                    "tipo_modello": "qrcode_scollegato",
                    "messaggio": "Questo QrCode è valido ma non è collegato a nessun oggetto.",
                    "qrcode_id": qr_code.id,
                    "testo_qrcode": qr_code.testo
                },
                status=status.HTTP_200_OK
            )
        
        data = None
        model_type = None
        
        # 2. Determina il modello figlio (Polimorfismo)
        # Controlliamo quale relazione inversa esiste sull'istanza di A_vista
        
        if hasattr(vista_obj, 'personaggio'):
            model_type = 'personaggio'
            # Usiamo il serializer pubblico!
            serializer = PersonaggioPublicSerializer(vista_obj.personaggio)
            data = serializer.data
            
        elif hasattr(vista_obj, 'inventario'):
            model_type = 'inventario'
            serializer = InventarioSerializer(vista_obj.inventario)
            data = serializer.data
        
        if hasattr(vista_obj, 'oggetto'):
            model_type = 'oggetto'
            # Usiamo vista_obj.oggetto per ottenere l'istanza "figlia"
            serializer = OggettoSerializer(vista_obj.oggetto)
            data = serializer.data
            
        elif hasattr(vista_obj, 'attivata'):
            model_type = 'attivata'
            serializer = AttivataSerializer(vista_obj.attivata)
            data = serializer.data
            
        elif hasattr(vista_obj, 'manifesto'):
            model_type = 'manifesto'
            serializer = ManifestoSerializer(vista_obj.manifesto)
            data = serializer.data
            
        else:
            # È solo un A_vista, o un tipo non ancora gestito
            model_type = 'a_vista'
            serializer = A_vistaSerializer(vista_obj)
            data = serializer.data

        # 3. Costruisci e restituisci la risposta
        response_payload = {
            "tipo_modello": model_type,
            "dati": data
        }
        
        return Response(response_payload, status=status.HTTP_200_OK) 
    
class PersonaggioMeView(APIView):
    """
    GET /api/personaggio/me/
    Restituisce i dettagli completi del personaggio
    collegato all'utente attualmente loggato.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            # --- OTTIMIZZAZIONE QUERY ---
            # Precarichiamo TUTTI i dati che il PersonaggioDetailSerializer userà.
            # Questo riduce decine di query a un numero fisso e basso.
            personaggio = Personaggio.objects.select_related(
                'tipologia',
                'inventario_ptr' # Necessario per l'ereditarietà
            ).prefetch_related(
                'log_eventi',
                'movimenti_credito',
                'movimenti_pc',
                'transazioni_in_uscita_sospese',
                'transazioni_in_entrata_sospese',
                'abilita_possedute',
                'attivate_possedute__statistiche_base__statistica',
                'attivate_possedute__elementi__elemento',
                
                # Prefetch per gli oggetti posseduti
                Prefetch(
                    'inventario_ptr__tracciamento_oggetti',
                    queryset=OggettoInInventario.objects.filter(data_fine__isnull=True).select_related(
                        'oggetto__aura',
                    ).prefetch_related(
                        'oggetto__oggettostatisticabase_set__statistica',
                        'oggetto__oggettostatistica_set__statistica',
                        'oggetto__oggettoelemento_set__elemento'
                    ),
                    to_attr='tracciamento_oggetti_correnti' # Nome cache personalizzato
                ),
                
                # Prefetch per i calcoli dei modificatori
                'abilita_possedute__statistiche__statistica',
                'abilita_possedute__punteggio_acquisito__modifica_statistiche__statistica_modificata',
                'inventario_ptr__tracciamento_oggetti__oggetto__statistiche__statistica',
                
            ).get(proprietario=request.user)
            # --------------------------
            
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PersonaggioDetailSerializer(personaggio)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CreditoMovimentoCreateView(APIView):
    """
    POST /api/personaggio/me/crediti/
    Aggiunge un movimento di crediti al personaggio dell'utente loggato.
    Richiede: {"importo": "100.00", "descrizione": "Ricompensa missione"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CreditoMovimentoCreateSerializer(
            data=request.data,
            context={'personaggio': personaggio} # Passa il personaggio al serializer
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PuntiCaratteristicaMovimentoCreateView(APIView):
    """
    POST /api/personaggio/me/pc/
    Aggiunge un movimento di Punti Caratteristica al personaggio dell'utente loggato.
    Richiede: {"importo": 5, "descrizione": "Avanzamento di livello"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PuntiCaratteristicaMovimentoCreateSerializer(
            data=request.data,
            context={'personaggio': personaggio}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransazioneSospesaListView(APIView):
    """
    GET /api/transazioni/sospese/
    Restituisce l'elenco delle transazioni in uscita
    che l'utente loggato deve confermare.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Trova le transazioni in attesa in cui il mittente
        # è l'inventario del personaggio loggato
        transazioni = TransazioneSospesa.objects.filter(
            mittente=personaggio.inventario_ptr, # Usa l'inventario_ptr
            stato=STATO_TRANSAZIONE_IN_ATTESA
        )
        
        serializer = TransazioneSospesaSerializer(transazioni, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class TransazioneRichiediView(APIView):
    """
    POST /api/transazioni/richiedi/
    Un utente loggato (richiedente) crea una richiesta di transazione.
    Richiede: {"oggetto_id": 123, "mittente_id": 456}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            personaggio_richiedente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente (richiedente)."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TransazioneCreateSerializer(
            data=request.data,
            context={'richiedente': personaggio_richiedente}
        )
        
        if serializer.is_valid():
            transazione = serializer.save()
            # Serializza la transazione creata per la risposta
            response_serializer = TransazioneSospesaSerializer(transazione)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransazioneConfermaView(APIView):
    """
    POST /api/transazioni/<int:pk>/conferma/
    Permette al mittente di accettare o rifiutare una transazione.
    Richiede: {"azione": "accetta"} o {"azione": "rifiuta"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        try:
            personaggio_mittente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            transazione = TransazioneSospesa.objects.get(
                pk=pk,
                mittente=personaggio_mittente.inventario_ptr, # Verifica che l'utente sia il mittente
                stato=STATO_TRANSAZIONE_IN_ATTESA
            )
        except TransazioneSospesa.DoesNotExist:
            return Response(
                {"error": "Transazione non trovata, già processata o non autorizzata."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TransazioneConfermaSerializer(
            data=request.data,
            context={'transazione': transazione}
        )
        
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(
                    {"success": f"Transazione {serializer.validated_data['azione']}ta."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": f"Errore durante l'azione: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
# --- MODIFICA 2: PersonaggioListView con filtro opzionale ---
class PersonaggioListView(APIView):
    """
    GET /api/personaggi/
    Query params: ?view_all=true (solo per admin)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        # Default: restituisci solo i personaggi dell'utente
        queryset = Personaggio.objects.filter(proprietario=request.user)
        
        # Se l'utente è staff/admin E richiede esplicitamente 'view_all'
        if (request.user.is_staff or request.user.is_superuser) and request.query_params.get('view_all') == 'true':
            queryset = Personaggio.objects.all()
        
        serializer = PersonaggioListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
# -----------------------------------------------------------
    
class PersonaggioDetailView(APIView):
    """
    GET /api/personaggi/<pk>/
    
    Restituisce i dettagli completi di un personaggio specifico.
    Applica la stessa logica di permessi della ListView:
    - Staff/Admin: può vedere qualsiasi personaggio.
    - Utente normale: può vedere SOLO un personaggio di sua proprietà.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        # Recupera il personaggio o restituisci 404
        personaggio = get_object_or_404(Personaggio, pk=pk)
        
        user = request.user

        # Controllo di sicurezza:
        # Se l'utente NON è staff E il personaggio NON è suo
        if not (user.is_staff or user.is_superuser) and personaggio.proprietario != user:
            return Response(
                {"error": "Non hai il permesso di visualizzare questo personaggio."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Se l'utente è staff O è il proprietario, restituisci i dati
        serializer = PersonaggioDetailSerializer(personaggio)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class RubaView(APIView):
    """
    POST /personaggi/api/transazioni/ruba/
    Richiede: {"oggetto_id": 123, "target_personaggio_id": 456}
    
    Esegue la logica di furto basata sulle caratteristiche
    del personaggio richiedente (loggato).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            personaggio_richiedente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = RubaSerializer(
            data=request.data,
            context={'richiedente': personaggio_richiedente}
        )
        
        if serializer.is_valid():
            try:
                oggetto_rubato = serializer.save()
                return Response(
                    {"success": f"Oggetto '{oggetto_rubato.nome}' rubato con successo!"}, 
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                # Gestisce errori durante il salvataggio (es. logica complessa nei modelli)
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcquisisciView(APIView):
    """
    POST /personaggi/api/transazioni/acquisisci/
    Richiede: {"qrcode_id": "uuid-del-qr"}
    
    Collega l'oggetto/attivata al personaggio loggato
    e scollega il QrCode.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            personaggio_richiedente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response(
                {"error": "Nessun personaggio trovato per questo utente."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AcquisisciSerializer(
            data=request.data,
            context={'richiedente': personaggio_richiedente}
        )
        
        if serializer.is_valid():
            item_acquisito = serializer.save()
            return Response(
                {"success": f"'{item_acquisito.nome}' acquisito con successo!"}, 
                status=status.HTTP_200_OK
            )
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
@csrf_exempt
def download_icon_patch(request):
    model = request.GET.get("model")
    
    if not (request.user.is_superuser or request.user.has_perm(f"edit_{model}")):
        return HttpResponse("Not permitted")

    svg_icon = request.GET.get("icon")
    color = request.GET.get("color") # es. '%23ff0000'
    id = request.GET.get("id")

    # Decodifica il colore (es. da '%23ff0000' a '#ff0000')
    if color and color.startswith('%23'):
        color = '#' + color[3:]
    
    svg_url = f"https://api.iconify.design/{svg_icon}.svg"
    params = {'color': color}
    
    try:
        response = requests.get(svg_url, params=params, timeout=5)
        
        if response.status_code == 200:
            # --- INIZIO CORREZIONE PERCORSO ---
            # Il percorso base (es. 'media') è già nel nome del file
            # che salviamo nel database. NON va aggiunto a MEDIA_ROOT.
            
            # Percorso relativo base (es. 'punteggio')
            save_path_relative_base = os.path.join(model) 
            
            # Percorso fisico (es. /var/www/django/media/punteggio)
            save_path_absolute = os.path.join(settings.MEDIA_ROOT, save_path_relative_base)
            
            os.makedirs(save_path_absolute, exist_ok=True)
            
            filename = f"icon-{id}.svg"
            file_path_absolute = os.path.join(save_path_absolute, filename)
            
            # Salva il file nel percorso fisico corretto
            with open(file_path_absolute, "wb") as f:
                f.write(response.content)
            
            # Ora aggiungi ICON_PICKER_PATH al percorso relativo
            # che verrà salvato nel database (es. 'media/punteggio/icon-....svg')
            save_path_base = getattr(settings, "ICON_PICKER_PATH", "") # 'media'
            file_path_relative = os.path.join(save_path_base, save_path_relative_base, filename)
            # --- FINE CORREZIONE PERCORSO ---

            return HttpResponse(file_path_relative)
        else:
            return HttpResponse(
                f"Failed to download SVG file. Status code: {response.reason}",
                status=response.status_code
            )
    except requests.RequestException as e:
        return HttpResponse(f"Failed to contact Iconify API: {e}", status=500)
    except Exception as e:
        return HttpResponse(f"Internal server error: {e}", status=500)
    
class PunteggiListView(generics.ListAPIView):
    """
    GET /api/punteggi/all/
    Restituisce l'elenco completo di tutti i Punteggi
    che sono di tipo CARATTERISTICA (CA).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PunteggioDetailSerializer
    
    # Filtra il queryset per includere solo le Caratteristiche
    queryset = Punteggio.objects.all().order_by('tipo', 'nome')