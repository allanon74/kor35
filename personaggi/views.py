import string
from collections import Counter
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Count, Prefetch # Importato Count
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest
from rest_framework import serializers
from django.utils import timezone

from .models import OggettoInInventario, Abilita, Tier
from .models import QrCode
from .models import Oggetto, Attivata, Manifesto, A_vista, Inventario, Infusione, Tessitura
from .models import Personaggio, TransazioneSospesa, CreditoMovimento, PuntiCaratteristicaMovimento
from .models import Punteggio, CARATTERISTICA, PersonaggioModelloAura, ModelloAura
from .models import PropostaTecnica, PropostaTecnicaMattone, STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE

import uuid 

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
from rest_framework.decorators import action

from rest_framework import generics
from django.db import transaction
from .serializers import AbilitaMasterListSerializer


from .serializers import (
    OggettoSerializer, AttivataSerializer, InfusioneSerializer, TessituraSerializer,
    ManifestoSerializer, A_vistaSerializer, 
    InventarioSerializer,
    PersonaggioDetailSerializer, 
    CreditoMovimentoCreateSerializer, PersonaggioListSerializer, 
    PuntiCaratteristicaMovimentoCreateSerializer, 
    TransazioneCreateSerializer, 
    TransazioneSospesaSerializer, 
    TransazioneConfermaSerializer, 
    RubaSerializer, 
    AcquisisciSerializer,
    PunteggioDetailSerializer,
    ModelloAuraSerializer,
    PropostaTecnicaSerializer,
)

from personaggi.serializers import PersonaggioPublicSerializer

from .models import Gruppo, Messaggio
from .serializers import MessaggioSerializer, MessaggioBroadcastCreateSerializer
from django.db.models import Q

from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.http import JsonResponse
import requests
import os
from django.conf import settings

from webpush.models import PushInformation, SubscriptionInfo
import json

PARAMETRO_SCONTO_ABILITA = 'rid_cos_ab'

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

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
            'is_staff': user.is_staff or user.is_superuser 
        })

from .models import (
    Abilita, Tier, Punteggio, Tabella,
    abilita_tier, abilita_requisito, abilita_sbloccata,
    abilita_punteggio, abilita_prerequisito,
)
from .serializers import (
    AbilSerializer, AbilitaSerializer, AbilitaUpdateSerializer, TierSerializer, 
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
        if self.action in ['update', 'partial_update']: return AbilitaUpdateSerializer
        return AbilSerializer

class TierViewSet(viewsets.ModelViewSet):
    queryset = Tier.objects.all()
    serializer_class = TierSerializer
    authentication_classes = (TokenAuthentication,)

class PunteggioViewSet(viewsets.ModelViewSet):
    queryset = Punteggio.objects.all()
    serializer_class = PunteggioSerializer
    authentication_classes = (TokenAuthentication,)

class TabellaViewSet(viewsets.ModelViewSet):
    queryset = Tabella.objects.all()
    serializer_class = TabellaSerializer
    authentication_classes = (TokenAuthentication,)

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
    permission_classes = [IsAuthenticated]
    serializer_class = AbilitaMasterListSerializer
    queryset = Abilita.objects.select_related(
        'caratteristica'
    ).prefetch_related(
        'abilita_requisito_set__requisito', 
        'abilita_prerequisiti__prerequisito',
        'abilita_punteggio_set__punteggio',
        'abilitastatistica_set__statistica',
    ).order_by('nome')

class AcquisisciAbilitaView(APIView):
    permission_classes = [IsAuthenticated]
    @transaction.atomic 
    def post(self, request, format=None):
        personaggio_id = request.data.get('personaggio_id')
        abilita_id = request.data.get('abilita_id')
        if not personaggio_id: return Response({"error": "L'ID del personaggio è richiesto (personaggio_id)."}, status=status.HTTP_400_BAD_REQUEST)
        if not abilita_id: return Response({"error": "abilita_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            personaggio = Personaggio.objects.select_related('tipologia').get(id=personaggio_id, proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Personaggio non trovato o non appartenente all'utente."}, status=status.HTTP_404_NOT_FOUND)
        except Personaggio.MultipleObjectsReturned: return Response({"error": "Errore interno: Trovati personaggi multipli con lo stesso ID."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            abilita = Abilita.objects.prefetch_related('abilita_requisito_set__requisito', 'abilita_prerequisiti').get(id=abilita_id)
        except Abilita.DoesNotExist: return Response({"error": "Abilità non trovata."}, status=status.HTTP_404_NOT_FOUND)

        if personaggio.abilita_possedute.filter(id=abilita_id).exists(): return Response({"error": "Abilità già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        character_scores = personaggio.caratteristiche_base
        for req in abilita.abilita_requisito_set.all():
            punteggio_nome = req.requisito.nome
            valore_richiesto = req.valore
            punteggio_pg = character_scores.get(punteggio_nome, 0)
            if punteggio_pg < valore_richiesto: return Response({"error": f"Requisito non soddisfatto: {punteggio_nome} {valore_richiesto} (possiedi {punteggio_pg})"}, status=status.HTTP_400_BAD_REQUEST)

        required_prereqs = [p.prerequisito for p in abilita.abilita_prerequisiti.all()]
        if required_prereqs:
            possessed_skill_ids = set(personaggio.abilita_possedute.values_list('id', flat=True))
            for prereq in required_prereqs:
                if prereq.id not in possessed_skill_ids: return Response({"error": f"Prerequisito non soddisfatto: {prereq.nome}"}, status=status.HTTP_400_BAD_REQUEST)

        mods = personaggio.modificatori_calcolati
        sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {'add': 0, 'mol': 1.0}) 
        sconto_valore = max(0, sconto_stat.get('add', 0)) 
        sconto_percent = Decimal(sconto_valore) / Decimal(100)
        moltiplicatore_costo = Decimal(1) - sconto_percent
        costo_pc_finale = abilita.costo_pc 
        costo_crediti_base = Decimal(abilita.costo_crediti)
        costo_crediti_finale = (costo_crediti_base * moltiplicatore_costo).quantize(Decimal('0.01'))

        if personaggio.punti_caratteristica < costo_pc_finale: return Response({"error": f"Punti Caratteristica insufficenti. Richiesti: {costo_pc_finale}"}, status=status.HTTP_400_BAD_REQUEST) 
        if personaggio.crediti < costo_crediti_finale: return Response({"error": f"Crediti insufficenti. Richiesti: {costo_crediti_finale} (Costo base: {abilita.costo_crediti}, Sconto: {sconto_valore}%)"}, status=status.HTTP_400_BAD_REQUEST)

        personaggio.modifica_pc(-costo_pc_finale, f"Acquisito abilità: {abilita.nome} (Costo: {costo_pc_finale} PC)")
        personaggio.modifica_crediti(-costo_crediti_finale, f"Acquisito abilità: {abilita.nome} (Costo: {costo_crediti_finale} Crediti)")
        personaggio.abilita_possedute.add(abilita)
        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class AbilitaAcquistabiliView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AbilitaMasterListSerializer
    def get(self, request, format=None):
        character_id = request.query_params.get('char_id')
        if not character_id: return Response({"error": "L'ID del personaggio è richiesto (char_id)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            personaggio = Personaggio.objects.select_related('tipologia').get(id=character_id)
        except Personaggio.DoesNotExist: return Response({"error": "Personaggio non trovato o non appartenente all'utente."}, status=status.HTTP_404_NOT_FOUND)
        except Personaggio.MultipleObjectsReturned: return Response({"error": "Errore interno: Trovati personaggi multipli con lo stesso ID per l'utente."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if personaggio.proprietario != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Personaggio non appartenente all'utente."}, status=status.HTTP_404_NOT_FOUND)

        possessed_skill_ids = set(personaggio.abilita_possedute.values_list('id', flat=True))
        char_scores = personaggio.caratteristiche_base
        mods = personaggio.modificatori_calcolati
        sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {'add': 0, 'mol': 1.0}) 
        sconto_valore = max(0, sconto_stat.get('add', 0)) 
        sconto_percent = Decimal(sconto_valore) / Decimal(100)
        moltiplicatore_costo = Decimal(1) - sconto_percent

        master_skills_list = Abilita.objects.exclude(id__in=possessed_skill_ids).select_related('caratteristica').prefetch_related('abilita_requisito_set__requisito', 'abilita_prerequisiti__prerequisito', 'abilita_punteggio_set__punteggio', 'abilitastatistica_set__statistica').order_by('nome')

        acquirable_skills = []
        for skill in master_skills_list:
            meets_reqs = True
            for req in skill.abilita_requisito_set.all():
                if char_scores.get(req.requisito.nome, 0) < req.valore:
                    meets_reqs = False
                    break
            if not meets_reqs: continue
            meets_prereqs = True
            for pre in skill.abilita_prerequisiti.all():
                if pre.prerequisito.id not in possessed_skill_ids:
                    meets_prereqs = False
                    break
            if not meets_prereqs: continue
            acquirable_skills.append(skill)

        serializer = AbilitaMasterListSerializer(acquirable_skills, many=True, context={'request': request})
        serialized_data = serializer.data
        final_data = []
        for skill_data in serialized_data:
            costo_crediti_base = Decimal(skill_data.get('costo_crediti', 0))
            costo_pc_base = skill_data.get('costo_pc', 0)
            costo_crediti_calc = (costo_crediti_base * moltiplicatore_costo).quantize(Decimal('0.01'))
            skill_data['costo_pc_calc'] = costo_pc_base 
            skill_data['costo_crediti_calc'] = float(costo_crediti_calc)
            final_data.append(skill_data)
        return Response(final_data, status=status.HTTP_200_OK)

# --- NUOVE VISTE PER INFUSIONI E TESSITURE (CORRETTE) ---

class InfusioniAcquistabiliView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InfusioneSerializer

    def get(self, request, format=None):
        character_id = request.query_params.get('char_id')
        if not character_id: return Response({"error": "L'ID del personaggio è richiesto (char_id)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            personaggio = Personaggio.objects.select_related('tipologia').get(id=character_id)
        except Personaggio.DoesNotExist: return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        
        if personaggio.proprietario != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)

        possedute_ids = personaggio.infusioni_possedute.values_list('id', flat=True)
        
        # Calcolo livello per ordinamento
        tutte_infusioni = Infusione.objects.exclude(id__in=possedute_ids).annotate(
            livello_calc=Count('mattoni')
        ).select_related(
            'aura_richiesta', 'aura_infusione'
        ).prefetch_related(
            'infusionemattone_set__mattone',
            'infusionestatisticabase_set__statistica'
        ).order_by('livello_calc', 'nome')

        acquistabili = []
        for infusione in tutte_infusioni:
            aura_req = infusione.aura_richiesta
            if aura_req:
                if aura_req.modelli_definiti.exists():
                    has_model_selected = personaggio.modelli_aura.filter(aura=aura_req).exists()
                    if not has_model_selected:
                        continue
            is_valid, _ = personaggio.valida_acquisto_tecnica(infusione)
            if is_valid:
                acquistabili.append(infusione)

        # MODIFICA FONDAMENTALE: Passiamo 'personaggio' nel contesto
        context = {'request': request, 'personaggio': personaggio}
        
        serializer = InfusioneSerializer(acquistabili, many=True, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AcquisisciInfusioneView(APIView):
    permission_classes = [IsAuthenticated]
    @transaction.atomic 
    def post(self, request, format=None):
        personaggio_id = request.data.get('personaggio_id')
        infusione_id = request.data.get('infusione_id')
        if not personaggio_id or not infusione_id: return Response({"error": "Dati mancanti."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            personaggio = Personaggio.objects.get(id=personaggio_id, proprietario=request.user)
            infusione = Infusione.objects.prefetch_related('infusionemattone_set').get(id=infusione_id)
        except (Personaggio.DoesNotExist, Infusione.DoesNotExist): return Response({"error": "Personaggio o Infusione non trovati."}, status=status.HTTP_404_NOT_FOUND)

        is_valid, error_msg = personaggio.valida_acquisto_tecnica(infusione)
        if not is_valid: return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        if personaggio.infusioni_possedute.filter(id=infusione.id).exists(): return Response({"error": "Infusione già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        costo = infusione.costo_crediti 
        if personaggio.crediti < costo: return Response({"error": f"Crediti insufficienti. Richiesti: {costo}"}, status=status.HTTP_400_BAD_REQUEST)

        personaggio.modifica_crediti(-costo, f"Acquisito infusione: {infusione.nome}")
        personaggio.infusioni_possedute.add(infusione)
        personaggio.aggiungi_log(f"Ha appreso l'infusione '{infusione.nome}' (Liv. {infusione.livello}).")

        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TessitureAcquistabiliView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TessituraSerializer

    def get(self, request, format=None):
        character_id = request.query_params.get('char_id')
        if not character_id: return Response({"error": "L'ID del personaggio è richiesto."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            personaggio = Personaggio.objects.select_related('tipologia').get(id=character_id)
        except Personaggio.DoesNotExist: return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        
        if personaggio.proprietario != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)

        possedute_ids = personaggio.tessiture_possedute.values_list('id', flat=True)
        
        tutte_tessiture = Tessitura.objects.exclude(id__in=possedute_ids).annotate(
            livello_calc=Count('mattoni')
        ).select_related(
            'aura_richiesta', 'elemento_principale'
        ).prefetch_related(
            'tessituramattone_set__mattone',
            'tessiturastatisticabase_set__statistica'
        ).order_by('livello_calc', 'nome')

        acquistabili = []
        for tessitura in tutte_tessiture:
            aura_req = tessitura.aura_richiesta
            if aura_req:
                if aura_req.modelli_definiti.exists():
                    has_model_selected = personaggio.modelli_aura.filter(aura=aura_req).exists()
                    if not has_model_selected:
                        continue
            is_valid, _ = personaggio.valida_acquisto_tecnica(tessitura)
            if is_valid:
                acquistabili.append(tessitura)

        # MODIFICA FONDAMENTALE: Passiamo 'personaggio' nel contesto
        context = {'request': request, 'personaggio': personaggio}

        serializer = TessituraSerializer(acquistabili, many=True, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcquisisciTessituraView(APIView):
    permission_classes = [IsAuthenticated]
    @transaction.atomic 
    def post(self, request, format=None):
        personaggio_id = request.data.get('personaggio_id')
        tessitura_id = request.data.get('tessitura_id')
        if not personaggio_id or not tessitura_id: return Response({"error": "Dati mancanti."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            personaggio = Personaggio.objects.get(id=personaggio_id, proprietario=request.user)
            tessitura = Tessitura.objects.prefetch_related('tessituramattone_set').get(id=tessitura_id)
        except (Personaggio.DoesNotExist, Tessitura.DoesNotExist): return Response({"error": "Oggetto non trovato."}, status=status.HTTP_404_NOT_FOUND)

        is_valid, error_msg = personaggio.valida_acquisto_tecnica(tessitura)
        if not is_valid: return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        if personaggio.tessiture_possedute.filter(id=tessitura.id).exists(): return Response({"error": "Tessitura già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        costo = tessitura.costo_crediti
        if personaggio.crediti < costo: return Response({"error": f"Crediti insufficienti. Richiesti: {costo}"}, status=status.HTTP_400_BAD_REQUEST)

        personaggio.modifica_crediti(-costo, f"Acquisito tessitura: {tessitura.nome}")
        personaggio.tessiture_possedute.add(tessitura)
        personaggio.aggiungi_log(f"Ha appreso la tessitura '{tessitura.nome}' (Liv. {tessitura.livello}).")

        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


def qr_code_html_view(request: HttpRequest) -> HttpResponse:
    uuid_str = request.GET.get('id')
    if not uuid_str: return HttpResponse("ID non fornito.", status=400)
    try:
        qrcode = QrCode.objects.get(id=uuid.UUID(uuid_str))
    except (QrCode.DoesNotExist, ValueError): return HttpResponse("QrCode non trovato o ID non valido.", status=404)
    testo_contenuto = qrcode.testo
    if not testo_contenuto: testo_html = "<i>(Nessun testo definito per questo QrCode)</i>"
    else: testo_html = f"<p>{testo_contenuto}</p>" 
    html_response = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dettaglio QrCode</title><style>body {{ font-family: sans-serif; margin: 2em; }}</style></head><body><h1>Contenuto del QrCode</h1><div>{testo_html}</div></body></html>"""
    return HttpResponse(html_response)

def generate_qr_data_uri(data_string: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"

def qr_code_list_view(request: HttpRequest) -> HttpResponse:
    qrcodes = QrCode.objects.all().order_by('-data_creazione')
    html_items = []
    box_style = "display: inline-block; vertical-align: top; border: 1px solid #ccc; padding: 15px; margin: 10px; text-align: center; max-width: 250px; word-wrap: break-word;"
    for qr in qrcodes:
        qr_id_str = str(qr.id)
        qr_img_data_uri = generate_qr_data_uri(qr_id_str)
        testo = escape(qr.testo) if qr.testo else "<i>(Nessun testo)</i>"
        html_items.append(f"""<div style="{box_style}"><img src="{qr_img_data_uri}" alt="QR Code per {qr_id_str}" width="200" height="200"><p style="font-family: monospace; font-size: 12px; margin-top: 10px;">{qr_id_str}</p><p>{testo}</p></div>""")
    html_body = "\n".join(html_items)
    html_response = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><title>Elenco QrCode</title><style>body {{ font-family: sans-serif; padding: 1em; }}</style></head><body><h1>Elenco QrCode</h1><div>{html_body if html_body else "<p>Nessun QrCode trovato.</p>"}</div></body></html>"""
    return HttpResponse(html_response)

def qr_code_detail_view(request: HttpRequest, pk: string) -> HttpResponse:
    qr = get_object_or_404(QrCode, pk=pk)
    qr_id_str = str(qr.id)
    qr_img_data_uri = generate_qr_data_uri(qr_id_str)
    testo = escape(qr.testo) if qr.testo else "<i>(Nessun testo)</i>"
    box_style = "display: inline-block; border: 1px solid #ccc; padding: 20px; text-align: center;"
    html_item = f"""<div style="{box_style}"><img src="{qr_img_data_uri}" alt="QR Code per {qr_id_str}" width="300" height="300"><p style="font-family: monospace; font-size: 14px; margin-top: 15px;">{qr_id_str}</p><p style="font-size: 1.2em;">{testo}</p></div>"""
    html_response = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><title>Dettaglio QrCode</title><style>body {{ font-family: sans-serif; padding: 1em; }}</style></head><body><h1>Dettaglio QrCode</h1><div>{html_item}</div></body></html>"""
    return HttpResponse(html_response)

class QrCodeDetailView(APIView):
    def get(self, request, qrcode_id, format=None):
        try:
            qr_code = QrCode.objects.select_related('vista').get(id=qrcode_id)
        except QrCode.DoesNotExist: return Response({"error": "QrCode non trovato."}, status=status.HTTP_404_NOT_FOUND)
        
        vista_obj = qr_code.vista
        if vista_obj is None: return Response({"tipo_modello": "qrcode_scollegato", "messaggio": "Questo QrCode è valido ma non è collegato a nessun oggetto.", "qrcode_id": qr_code.id, "testo_qrcode": qr_code.testo}, status=status.HTTP_200_OK)
        
        data = None
        model_type = None
        
        if hasattr(vista_obj, 'personaggio'):
            model_type = 'personaggio'
            serializer = PersonaggioPublicSerializer(vista_obj.personaggio)
            data = serializer.data
        elif hasattr(vista_obj, 'inventario'):
            model_type = 'inventario'
            serializer = InventarioSerializer(vista_obj.inventario)
            data = serializer.data
        
        if hasattr(vista_obj, 'oggetto'):
            model_type = 'oggetto'
            serializer = OggettoSerializer(vista_obj.oggetto)
            data = serializer.data
        elif hasattr(vista_obj, 'attivata'): # Legacy
            model_type = 'attivata'
            serializer = AttivataSerializer(vista_obj.attivata)
            data = serializer.data
        elif hasattr(vista_obj, 'infusione'): # Nuovo
            model_type = 'infusione'
            serializer = InfusioneSerializer(vista_obj.infusione)
            data = serializer.data
        elif hasattr(vista_obj, 'tessitura'): # Nuovo
            model_type = 'tessitura'
            serializer = TessituraSerializer(vista_obj.tessitura)
            data = serializer.data
        elif hasattr(vista_obj, 'manifesto'):
            model_type = 'manifesto'
            serializer = ManifestoSerializer(vista_obj.manifesto)
            data = serializer.data
        else:
            model_type = 'a_vista'
            serializer = A_vistaSerializer(vista_obj)
            data = serializer.data

        response_payload = {"tipo_modello": model_type, "dati": data}
        return Response(response_payload, status=status.HTTP_200_OK) 
    
class PersonaggioMeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        try:
            personaggio = Personaggio.objects.select_related(
                'tipologia', 'inventario_ptr'
            ).prefetch_related(
                'log_eventi', 'movimenti_credito', 'movimenti_pc', 'transazioni_in_uscita_sospese', 'transazioni_in_entrata_sospese',
                'abilita_possedute', 'attivate_possedute__statistiche_base__statistica', 'attivate_possedute__elementi__elemento',
                'infusioni_possedute__statistiche_base__statistica', 'infusioni_possedute__mattoni__mattone',
                'tessiture_possedute__statistiche_base__statistica', 'tessiture_possedute__mattoni__mattone',
                
                Prefetch(
                    'inventario_ptr__tracciamento_oggetti',
                    queryset=OggettoInInventario.objects.filter(data_fine__isnull=True).select_related('oggetto__aura').prefetch_related('oggetto__oggettostatisticabase_set__statistica', 'oggetto__oggettostatistica_set__statistica', 'oggetto__oggettoelemento_set__elemento'),
                    to_attr='tracciamento_oggetti_correnti'
                ),
                'abilita_possedute__statistiche__statistica', 'abilita_possedute__punteggio_acquisito__modifica_statistiche__statistica_modificata', 'inventario_ptr__tracciamento_oggetti__oggetto__statistiche__statistica',
            ).get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PersonaggioDetailSerializer(personaggio)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CreditoMovimentoCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CreditoMovimentoCreateSerializer(data=request.data, context={'personaggio': personaggio})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PuntiCaratteristicaMovimentoCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PuntiCaratteristicaMovimentoCreateSerializer(data=request.data, context={'personaggio': personaggio})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransazioneSospesaListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        transazioni = TransazioneSospesa.objects.filter(mittente=personaggio.inventario_ptr, stato=STATO_TRANSAZIONE_IN_ATTESA)
        serializer = TransazioneSospesaSerializer(transazioni, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class TransazioneRichiediView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, format=None):
        try:
            personaggio_richiedente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente (richiedente)."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TransazioneCreateSerializer(data=request.data, context={'richiedente': personaggio_richiedente})
        if serializer.is_valid():
            transazione = serializer.save()
            response_serializer = TransazioneSospesaSerializer(transazione)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransazioneConfermaView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk, format=None):
        try:
            personaggio_mittente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        try:
            transazione = TransazioneSospesa.objects.get(pk=pk, mittente=personaggio_mittente.inventario_ptr, stato=STATO_TRANSAZIONE_IN_ATTESA)
        except TransazioneSospesa.DoesNotExist: return Response({"error": "Transazione non trovata, già processata o non autorizzata."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TransazioneConfermaSerializer(data=request.data, context={'transazione': transazione})
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"success": f"Transazione {serializer.validated_data['azione']}ta."}, status=status.HTTP_200_OK)
            except Exception as e: return Response({"error": f"Errore durante l'azione: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PersonaggioListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        queryset = Personaggio.objects.filter(proprietario=request.user)
        if (request.user.is_staff or request.user.is_superuser) and request.query_params.get('view_all') == 'true':
            queryset = Personaggio.objects.all()
        serializer = PersonaggioListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class PersonaggioDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk, format=None):
        personaggio = get_object_or_404(Personaggio, pk=pk)
        user = request.user
        if not (user.is_staff or user.is_superuser) and personaggio.proprietario != user:
            return Response({"error": "Non hai il permesso di visualizzare questo personaggio."}, status=status.HTTP_403_FORBIDDEN)
        serializer = PersonaggioDetailSerializer(personaggio)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class RubaView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, format=None):
        try:
            personaggio_richiedente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RubaSerializer(data=request.data, context={'richiedente': personaggio_richiedente})
        if serializer.is_valid():
            try:
                oggetto_rubato = serializer.save()
                return Response({"success": f"Oggetto '{oggetto_rubato.nome}' rubato con successo!"}, status=status.HTTP_200_OK)
            except Exception as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AcquisisciView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, format=None):
        try:
            personaggio_richiedente = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist: return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AcquisisciSerializer(data=request.data, context={'richiedente': personaggio_richiedente})
        if serializer.is_valid():
            item_acquisito = serializer.save()
            return Response({"success": f"'{item_acquisito.nome}' acquisito con successo!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@csrf_exempt
def download_icon_patch(request):
    model = request.GET.get("model")
    if not (request.user.is_superuser or request.user.has_perm(f"edit_{model}")): return HttpResponse("Not permitted")
    svg_icon = request.GET.get("icon")
    color = request.GET.get("color") 
    id = request.GET.get("id")
    if color and color.startswith('%23'): color = '#' + color[3:]
    svg_url = f"https://api.iconify.design/{svg_icon}.svg"
    params = {'color': color}
    try:
        response = requests.get(svg_url, params=params, timeout=5)
        if response.status_code == 200:
            save_path_relative_base = os.path.join(model) 
            save_path_absolute = os.path.join(settings.MEDIA_ROOT, save_path_relative_base)
            os.makedirs(save_path_absolute, exist_ok=True)
            filename = f"icon-{id}.svg"
            file_path_absolute = os.path.join(save_path_absolute, filename)
            with open(file_path_absolute, "wb") as f: f.write(response.content)
            save_path_base = getattr(settings, "ICON_PICKER_PATH", "") 
            file_path_relative = os.path.join(save_path_base, save_path_relative_base, filename)
            return HttpResponse(file_path_relative)
        else: return HttpResponse(f"Failed to download SVG file. Status code: {response.reason}", status=response.status_code)
    except requests.RequestException as e: return HttpResponse(f"Failed to contact Iconify API: {e}", status=500)
    except Exception as e: return HttpResponse(f"Internal server error: {e}", status=500)
    
class PunteggiListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PunteggioDetailSerializer
    queryset = Punteggio.objects.all().order_by('tipo','ordine', 'nome')
    
class MessaggioListView(generics.ListAPIView):
    serializer_class = MessaggioSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        personaggio_id = self.request.query_params.get('personaggio_id')
        user = self.request.user
        if not personaggio_id: return Messaggio.objects.none()
        try:
            target_pg = Personaggio.objects.get(id=personaggio_id)
        except Personaggio.DoesNotExist: return Messaggio.objects.none()
        if target_pg.proprietario != user and not user.is_staff: return Messaggio.objects.none()
        q_broadcast = Q(tipo_messaggio=Messaggio.TIPO_BROADCAST)
        q_individuale = Q(tipo_messaggio=Messaggio.TIPO_INDIVIDUALE) & Q(destinatario_personaggio=target_pg)
        gruppi_id = target_pg.gruppi_appartenenza.values_list('id', flat=True)
        q_gruppo = Q(tipo_messaggio=Messaggio.TIPO_GRUPPO) & Q(destinatario_gruppo__id__in=gruppi_id)
        return Messaggio.objects.filter(q_broadcast | q_individuale | q_gruppo).order_by('-data_invio')

class MessaggioAdminSentListView(generics.ListAPIView):
    serializer_class = MessaggioSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    def get_queryset(self):
        return Messaggio.objects.filter(mittente=self.request.user, salva_in_cronologia=True).order_by('-data_invio')

class MessaggioBroadcastCreateView(generics.CreateAPIView):
    serializer_class = MessaggioBroadcastCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser] 
    def perform_create(self, serializer):
        serializer.save(mittente=self.request.user, tipo_messaggio=Messaggio.TIPO_BROADCAST)
        
class WebPushSubscribeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            keys = data.get('keys', {})
            endpoint = data.get('endpoint')
            p256dh = keys.get('p256dh')
            auth = keys.get('auth')
            if not endpoint or not p256dh or not auth: return Response({"error": "Dati sottoscrizione incompleti"}, status=400)
            user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
            browser_info = user_agent[:100] if user_agent else 'Unknown' 
            subscription, created = SubscriptionInfo.objects.get_or_create(endpoint=endpoint, defaults={'browser': browser_info, 'auth': auth, 'p256dh': p256dh})
            if not created:
                subscription.auth = auth
                subscription.p256dh = p256dh
                subscription.browser = browser_info
                subscription.save()
            PushInformation.objects.get_or_create(user=request.user, subscription=subscription)
            return Response({"status": "success", "message": "Sottoscrizione salvata."}, status=201)
        except Exception as e:
            print(f"Errore salvataggio WebPush: {e}")
            return Response({"error": str(e)}, status=400)

# --- NUOVE VIEW PER GESTIONE MODELLI AURA ---        
        
class ModelliAuraListView(APIView):
    """
    GET /api/punteggio/<int:aura_id>/modelli/
    Restituisce i modelli disponibili per una certa aura.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, aura_id):
        modelli = ModelloAura.objects.filter(aura_id=aura_id).prefetch_related('mattoni_proibiti')
        serializer = ModelloAuraSerializer(modelli, many=True, context={'request': request})
        return Response(serializer.data)

class SelezionaModelloAuraView(APIView):
    """
    POST /api/personaggio/me/seleziona_modello_aura/
    Body: { "personaggio_id": 1, "modello_id": 5 }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        pg_id = request.data.get('personaggio_id')
        mod_id = request.data.get('modello_id')
        
        personaggio = get_object_or_404(Personaggio, id=pg_id, proprietario=request.user)
        modello = get_object_or_404(ModelloAura, id=mod_id)
        
        # Verifica se ha già un modello per questa aura
        esiste = PersonaggioModelloAura.objects.filter(
            personaggio=personaggio, 
            modello_aura__aura=modello.aura
        ).exists()
        
        if esiste:
            return Response({"error": "Hai già scelto un modello per questa aura. La scelta è definitiva."}, status=status.HTTP_400_BAD_REQUEST)
            
        PersonaggioModelloAura.objects.create(personaggio=personaggio, modello_aura=modello)
        personaggio.aggiungi_log(f"Ha scelto il modello di aura: {modello.nome} per {modello.aura.nome}")
        
        # Ritorna il personaggio aggiornato
        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data)
    
class PropostaTecnicaViewSet(viewsets.ModelViewSet):
    serializer_class = PropostaTecnicaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        character_id = self.request.query_params.get('char_id')
        user = self.request.user
        
        if character_id:
            return PropostaTecnica.objects.filter(personaggio_id=character_id, personaggio__proprietario=user)
        
        # Default fallback (sicurezza)
        return PropostaTecnica.objects.filter(personaggio__proprietario=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Necessario per create() nel serializer
        if self.request.method == 'POST':
            char_id = self.request.data.get('personaggio_id')
            if char_id:
                try:
                    pg = Personaggio.objects.get(id=char_id, proprietario=self.request.user)
                    context['personaggio'] = pg
                except Personaggio.DoesNotExist:
                    pass
        return context

    def perform_destroy(self, instance):
        if instance.stato != STATO_PROPOSTA_BOZZA:
            raise serializers.ValidationError("Non puoi cancellare una proposta già inviata.")
        instance.delete()

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def invia_proposta(self, request, pk=None):
        """
        Action custom per inviare la proposta (Bozza -> Valutazione)
        Deduce i crediti e valida i vincoli.
        """
        proposta = self.get_object()
        personaggio = proposta.personaggio
        
        if proposta.stato != STATO_PROPOSTA_BOZZA:
            return Response({"error": "La proposta non è in stato di bozza."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Calcolo Costo
        livello = proposta.livello
        if livello == 0:
            return Response({"error": "La proposta deve avere almeno un mattone."}, status=status.HTTP_400_BAD_REQUEST)
            
        costo_invio = livello * 10
        
        if personaggio.crediti < costo_invio:
            return Response({"error": f"Crediti insufficienti. Richiesti: {costo_invio} CR."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Validazioni Logiche (Anti-Cheat / Coerenza)
        
        # A. Aura Posseduta e Cap Livello
        val_aura = personaggio.get_valore_aura_effettivo(proposta.aura)
        if val_aura < 1:
            return Response({"error": "Non possiedi l'aura selezionata."}, status=status.HTTP_400_BAD_REQUEST)
        if livello > val_aura:
            return Response({"error": f"Troppi mattoni ({livello}) per il valore della tua aura ({val_aura})."}, status=status.HTTP_400_BAD_REQUEST)

        # B. Mattoni Validi e Cap Caratteristica
        mattoni_objs = [pm.mattone for pm in proposta.propostatecnicamattone_set.select_related('mattone__caratteristica_associata').all().order_by('ordine')]
        mattoni_ids = [m.id for m in mattoni_objs]
        counter_mattoni = Counter(mattoni_ids)
        punteggi_pg = personaggio.caratteristiche_base
        
        for m in mattoni_objs:
            # Controllo aura mattone
            if m.aura_id != proposta.aura_id:
                 return Response({"error": f"Il mattone {m.nome} non appartiene all'aura della proposta."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Controllo Caratteristica Posseduta (>=1)
            caratt_nome = m.caratteristica_associata.nome
            val_caratt = punteggi_pg.get(caratt_nome, 0)
            if val_caratt < 1:
                return Response({"error": f"Non possiedi la caratteristica {caratt_nome} per il mattone {m.nome}."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Controllo Quantità <= Valore Caratteristica
            qty = counter_mattoni[m.id]
            if qty > val_caratt:
                return Response({"error": f"Hai usato il mattone {m.nome} {qty} volte, ma hai solo {val_caratt} in {caratt_nome}."}, status=status.HTTP_400_BAD_REQUEST)

        # C. Validazione Modello Aura (Proibiti / Obbligatori)
        modello = personaggio.modelli_aura.filter(aura=proposta.aura).first()
        if modello:
            set_ids_proposta = set(mattoni_ids)
            
            # Proibiti
            proibiti_ids = set(modello.mattoni_proibiti.values_list('id', flat=True))
            if set_ids_proposta.intersection(proibiti_ids):
                return Response({"error": "La proposta contiene mattoni proibiti dal tuo modello aura."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Obbligatori (Tutti i tipi obbligatori devono essere presenti)
            obbligatori_ids = set(modello.mattoni_obbligatori.values_list('id', flat=True))
            if not obbligatori_ids.issubset(set_ids_proposta):
                return Response({"error": "La proposta non contiene tutti i mattoni obbligatori del tuo modello aura."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Esecuzione Pagamento e Cambio Stato
        personaggio.modifica_crediti(-costo_invio, f"Invio proposta {proposta.tipo}: {proposta.nome}")
        proposta.costo_invio_pagato = costo_invio
        proposta.stato = STATO_PROPOSTA_IN_VALUTAZIONE
        proposta.data_invio = timezone.now()
        proposta.save()
        
        return Response(PropostaTecnicaSerializer(proposta).data, status=status.HTTP_200_OK)