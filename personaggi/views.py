import string
from collections import Counter
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Count, Sum, Prefetch, OuterRef, Exists
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest
from rest_framework import serializers
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError

# --- IMPORT MODELLI AGGIORNATI ---
from .models import (
    OggettoInInventario, Abilita, Tier, QrCode, Oggetto, Attivata, Manifesto, 
    A_vista, Inventario, Infusione, Tessitura, Personaggio, TransazioneSospesa, 
    CreditoMovimento, PuntiCaratteristicaMovimento, Punteggio, CARATTERISTICA, 
    PersonaggioModelloAura, ModelloAura, PropostaTecnica, 
    # NUOVI MODELLI INTERMEDI
    PropostaTecnicaCaratteristica, InfusioneCaratteristica, TessituraCaratteristica,
    STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE, LetturaMessaggio, PersonaggioLog,
    STATO_TRANSAZIONE_IN_ATTESA, STATO_TRANSAZIONE_ACCETTATA, STATO_TRANSAZIONE_RIFIUTATA, STATO_TRANSAZIONE_CHOICES,
    Gruppo, Messaggio, Tabella, Mattone, 
    OggettoBase, ForgiaturaInCorso, 
    abilita_tier, abilita_requisito, abilita_sbloccata, 
    abilita_punteggio, abilita_prerequisito,
    # Costanti
    COSTO_PER_MATTONE_CREAZIONE, 
    COSTO_DEFAULT_INVIO_PROPOSTA,
    RichiestaAssemblaggio, STATO_RICHIESTA_PENDENTE,
)

import uuid 
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
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
from django.db import transaction
from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.http import JsonResponse
import requests
import os
from django.conf import settings
from webpush.models import PushInformation, SubscriptionInfo
import json

# --- IMPORT SERVICES ---
from .services import (
    # monta_potenziamento, crea_oggetto_da_infusione, 
    GestioneOggettiService, GestioneCraftingService 
)

# --- IMPORT SERIALIZERS ---
from .serializers import (
    OggettoSerializer, AttivataSerializer, InfusioneSerializer, TessituraSerializer,
    ManifestoSerializer, A_vistaSerializer, InventarioSerializer,
    PersonaggioDetailSerializer, CreditoMovimentoCreateSerializer, PersonaggioListSerializer, 
    PuntiCaratteristicaMovimentoCreateSerializer, TransazioneCreateSerializer, 
    TransazioneSospesaSerializer, TransazioneConfermaSerializer, RubaSerializer, 
    AcquisisciSerializer, PunteggioDetailSerializer, ModelloAuraSerializer,
    PropostaTecnicaSerializer, PersonaggioLogSerializer, PersonaggioAutocompleteSerializer,
    MessaggioCreateSerializer, MessaggioSerializer, MessaggioBroadcastCreateSerializer,
    AbilitaMasterListSerializer, PersonaggioPublicSerializer,
    AbilSerializer, AbilitaSerializer, AbilitaUpdateSerializer, TierSerializer, 
    PunteggioSerializer, TabellaSerializer,
    AbilitaTierSerializer, AbilitaRequisitoSerializer, AbilitaSbloccataSerializer,
    AbilitaPunteggioSerializer, AbilitaPrerequisitoSerializer, UserSerializer,
    OggettoBaseSerializer, RichiestaAssemblaggioSerializer,
)

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

# --- VIEWSETS ORIGINALI ---

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
        except Personaggio.MultipleObjectsReturned: return Response({"error": "Errore interno: Trovati personaggi multipli con lo stesso ID per l'utente."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
        
        cache.delete(f"acquirable_skills_{personaggio.id}")
        
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

        cache_key = f"acquirable_skills_{character_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
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
        cache.set(cache_key, final_data, timeout=600)
        return Response(final_data, status=status.HTTP_200_OK)

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
        
        # MODIFICA: Uso Sum('componenti__valore') per calcolare il livello
        tutte_infusioni = Infusione.objects.exclude(id__in=possedute_ids).annotate(
            livello_calc=Sum('componenti__valore')
        ).select_related(
            'aura_richiesta', 'aura_infusione'
        ).prefetch_related(
            'componenti__caratteristica',
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
            # MODIFICA: Prefetch su componenti
            infusione = Infusione.objects.prefetch_related('componenti').get(id=infusione_id)
        except (Personaggio.DoesNotExist, Infusione.DoesNotExist): return Response({"error": "Personaggio o Infusione non trovati."}, status=status.HTTP_404_NOT_FOUND)

        is_valid, error_msg = personaggio.valida_acquisto_tecnica(infusione)
        if not is_valid: return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        if personaggio.infusioni_possedute.filter(id=infusione.id).exists(): return Response({"error": "Infusione già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        costo = infusione.costo_crediti 
        if personaggio.crediti < costo: return Response({"error": f"Crediti insufficienti. Richiesti: {costo}"}, status=status.HTTP_400_BAD_REQUEST)

        personaggio.modifica_crediti(-costo, f"Acquisito infusione: {infusione.nome}")
        personaggio.infusioni_possedute.add(infusione)
        personaggio.aggiungi_log(f"Ha appreso l'infusione '{infusione.nome}' (Liv. {infusione.livello}).")
        
        if hasattr(infusione, 'proposta_creazione') and infusione.proposta_creazione:
            creatore = infusione.proposta_creazione.personaggio
            if creatore.id != personaggio.id:
                royalty = int(round(costo * 0.10))
                if royalty > 0:
                    creatore.modifica_crediti(royalty, f"Royalty per l'acquisto di '{infusione.nome}' da parte di {personaggio.nome}")
                    creatore.aggiungi_log(f"Ha ricevuto {royalty} CR di royalty per la tecnica '{infusione.nome}'.")

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
        
        # MODIFICA: Uso Sum('componenti__valore') per calcolare il livello
        tutte_tessiture = Tessitura.objects.exclude(id__in=possedute_ids).annotate(
            livello_calc=Sum('componenti__valore')
        ).select_related(
            'aura_richiesta', 'elemento_principale'
        ).prefetch_related(
            'componenti__caratteristica',
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
            # MODIFICA: Prefetch su componenti
            tessitura = Tessitura.objects.prefetch_related('componenti').get(id=tessitura_id)
        except (Personaggio.DoesNotExist, Tessitura.DoesNotExist): return Response({"error": "Oggetto non trovato."}, status=status.HTTP_404_NOT_FOUND)

        is_valid, error_msg = personaggio.valida_acquisto_tecnica(tessitura)
        if not is_valid: return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        if personaggio.tessiture_possedute.filter(id=tessitura.id).exists(): return Response({"error": "Tessitura già posseduta."}, status=status.HTTP_400_BAD_REQUEST)

        costo = tessitura.costo_crediti
        if personaggio.crediti < costo: return Response({"error": f"Crediti insufficienti. Richiesti: {costo}"}, status=status.HTTP_400_BAD_REQUEST)

        personaggio.modifica_crediti(-costo, f"Acquisito tessitura: {tessitura.nome}")
        personaggio.tessiture_possedute.add(tessitura)
        personaggio.aggiungi_log(f"Ha appreso la tessitura '{tessitura.nome}' (Liv. {tessitura.livello}).")
        
        if hasattr(tessitura, 'proposta_creazione') and tessitura.proposta_creazione:
            creatore = tessitura.proposta_creazione.personaggio
            if creatore.id != personaggio.id:
                royalty = int(round(costo * 0.10))
                if royalty > 0:
                    creatore.modifica_crediti(royalty, f"Royalty per l'acquisto di '{tessitura.nome}' da parte di {personaggio.nome}")
                    creatore.aggiungi_log(f"Ha ricevuto {royalty} CR di royalty per la tecnica '{tessitura.nome}'.")

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
            # MODIFICA: Prefetch aggiornati per usare componenti__caratteristica
            personaggio = Personaggio.objects.select_related(
                'tipologia', 'inventario_ptr'
            ).prefetch_related(
                'movimenti_credito', 'movimenti_pc', 
                'abilita_possedute', 'attivate_possedute__statistiche_base__statistica', 'attivate_possedute__elementi__elemento',
                
                # Aggiornato da __mattoni__mattone a __componenti__caratteristica
                'infusioni_possedute__statistiche_base__statistica', 'infusioni_possedute__componenti__caratteristica',
                'tessiture_possedute__statistiche_base__statistica', 'tessiture_possedute__componenti__caratteristica',
                
                Prefetch(
                    'inventario_ptr__tracciamento_oggetti',
                    queryset=OggettoInInventario.objects.filter(data_fine__isnull=True).select_related(
                        'oggetto__aura'
                    ).prefetch_related(
                        'oggetto__oggettostatisticabase_set__statistica', 
                        'oggetto__oggettostatistica_set__statistica', 
                        'oggetto__componenti__caratteristica',
                    ),
                    to_attr='tracciamento_oggetti_correnti'
                ),
                'abilita_possedute__statistiche__statistica', 
                'abilita_possedute__punteggio_acquisito__modifica_statistiche__statistica_modificata', 
                'inventario_ptr__tracciamento_oggetti__oggetto__statistiche__statistica',
            ).get(proprietario=request.user)
        
        except Personaggio.DoesNotExist: 
            return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class PersonaggioLogsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonaggioLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return PersonaggioLog.objects.filter(
            personaggio__proprietario=self.request.user
        ).order_by('-data')

class PersonaggioTransazioniListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransazioneSospesaSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        tipo = self.request.query_params.get('tipo', 'entrata')
        char_id = self.request.query_params.get('char_id')
        
        qs_pg = Personaggio.objects.filter(proprietario=user)
        if char_id:
            qs_pg = qs_pg.filter(id=char_id)
            
        if not qs_pg.exists():
            return TransazioneSospesa.objects.none()

        pg_ids = list(qs_pg.values_list('id', flat=True))
        inventari_ids = list(qs_pg.values_list('inventario_ptr_id', flat=True))

        if tipo == 'uscita':
            return TransazioneSospesa.objects.filter(mittente__id__in=inventari_ids).order_by('-data_richiesta')
        else:
            return TransazioneSospesa.objects.filter(richiedente__id__in=pg_ids).order_by('-data_richiesta')

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
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        personaggio_id = self.request.query_params.get('personaggio_id')
        if personaggio_id:
            try:
                context['personaggio'] = Personaggio.objects.get(id=personaggio_id)
            except Personaggio.DoesNotExist:
                pass
        return context
    
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
        messaggi = Messaggio.objects.filter(q_broadcast | q_individuale | q_gruppo).order_by('-data_invio')

        ids_cancellati = LetturaMessaggio.objects.filter(
            personaggio=target_pg, 
            cancellato=True
        ).values_list('messaggio_id', flat=True)

        lettura_esistente = LetturaMessaggio.objects.filter(
            messaggio=OuterRef('pk'),
            personaggio=target_pg,
            letto=True
        )
        return messaggi.exclude(id__in=ids_cancellati).annotate(is_letto_db=Exists(lettura_esistente))
    
class MessaggioActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action_type):
        personaggio_id = request.data.get('personaggio_id')
        if not personaggio_id: return Response({"error": "personaggio_id mancante"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            personaggio = Personaggio.objects.get(id=personaggio_id, proprietario=request.user)
            messaggio = Messaggio.objects.get(pk=pk) 
        except (Personaggio.DoesNotExist, Messaggio.DoesNotExist):
            return Response({"error": "Dati non validi"}, status=status.HTTP_404_NOT_FOUND)

        stato, created = LetturaMessaggio.objects.get_or_create(messaggio=messaggio, personaggio=personaggio)

        if action_type == 'leggi':
            stato.letto = True
            if not stato.data_lettura: stato.data_lettura = timezone.now()
            stato.save()
            return Response({"status": "Messaggio segnato come letto"})
        elif action_type == 'cancella':
            stato.cancellato = True
            stato.save()
            return Response({"status": "Messaggio cancellato"})
        return Response({"error": "Azione non valida"}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": str(e)}, status=400)
        
class ModelliAuraListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, aura_id):
        modelli = ModelloAura.objects.filter(aura_id=aura_id).prefetch_related('mattoni_proibiti')
        serializer = ModelloAuraSerializer(modelli, many=True, context={'request': request})
        return Response(serializer.data)

class SelezionaModelloAuraView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        pg_id = request.data.get('personaggio_id')
        mod_id = request.data.get('modello_id')
        personaggio = get_object_or_404(Personaggio, id=pg_id, proprietario=request.user)
        modello = get_object_or_404(ModelloAura, id=mod_id)
        esiste = PersonaggioModelloAura.objects.filter(personaggio=personaggio, modello_aura__aura=modello.aura).exists()
        if esiste: return Response({"error": "Hai già scelto un modello per questa aura. La scelta è definitiva."}, status=status.HTTP_400_BAD_REQUEST)
        PersonaggioModelloAura.objects.create(personaggio=personaggio, modello_aura=modello)
        personaggio.aggiungi_log(f"Ha scelto il modello di aura: {modello.nome} per {modello.aura.nome}")
        serializer = PersonaggioDetailSerializer(personaggio, context={'request': request})
        return Response(serializer.data)
    
class PropostaTecnicaViewSet(viewsets.ModelViewSet):
    serializer_class = PropostaTecnicaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        character_id = self.request.query_params.get('char_id')
        user = self.request.user
        if character_id: return PropostaTecnica.objects.filter(personaggio_id=character_id, personaggio__proprietario=user)
        return PropostaTecnica.objects.filter(personaggio__proprietario=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            char_id = self.request.data.get('personaggio_id')
            if char_id:
                try:
                    pg = Personaggio.objects.get(id=char_id, proprietario=self.request.user)
                    context['personaggio'] = pg
                except Personaggio.DoesNotExist: pass
        return context

    def perform_destroy(self, instance):
        if instance.stato != STATO_PROPOSTA_BOZZA: raise serializers.ValidationError("Non puoi cancellare una proposta già inviata.")
        instance.delete()

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def invia_proposta(self, request, pk=None):
        # LOGICA AGGIORNATA PER USARE COMPONENTI INVECE DI MATTONI
        proposta = self.get_object()
        personaggio = proposta.personaggio
        if proposta.stato != STATO_PROPOSTA_BOZZA: return Response({"error": "La proposta non è in stato di bozza."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Livello calcolato sui valori delle caratteristiche
        livello = proposta.livello
        if livello == 0: return Response({"error": "La proposta deve avere almeno un componente."}, status=status.HTTP_400_BAD_REQUEST)
        
# --- CALCOLO COSTO INVIO (BUROCRAZIA) ---
        costo_base = COSTO_DEFAULT_INVIO_PROPOSTA # Default 10
        
        if proposta.tipo == 'INF':
             # Cerca la statistica specifica per l'invio proposta INF
             if proposta.aura.stat_costo_invio_proposta_infusione:
                 val = proposta.aura.stat_costo_invio_proposta_infusione.valore_base_predefinito
                 if val > 0: costo_base = val
        else: # TES
             # Cerca la statistica specifica per l'invio proposta TES
             if proposta.aura.stat_costo_invio_proposta_tessitura:
                 val = proposta.aura.stat_costo_invio_proposta_tessitura.valore_base_predefinito
                 if val > 0: costo_base = val
                 
        costo_invio = livello * costo_base

        if personaggio.crediti < costo_invio: 
            return Response({"error": f"Crediti insufficienti. Richiesti: {costo_invio} CR."}, status=status.HTTP_400_BAD_REQUEST)

        val_aura = personaggio.get_valore_aura_effettivo(proposta.aura)
        if val_aura < 1: return Response({"error": "Non possiedi l'aura selezionata."}, status=status.HTTP_400_BAD_REQUEST)
        if livello > val_aura: return Response({"error": f"Troppi componenti ({livello}) per il valore della tua aura ({val_aura})."}, status=status.HTTP_400_BAD_REQUEST)

        # CHECK CARATTERISTICHE
        componenti = proposta.componenti.select_related('caratteristica').all()
        punteggi_pg = personaggio.caratteristiche_base
        
        # Insieme dei mattoni virtuali usati (Aura Proposta + Caratteristica Componente)
        # Ci serve per i check del Modello Aura
        caratteristiche_usate_ids = set()

        for comp in componenti:
            caratt = comp.caratteristica
            caratteristiche_usate_ids.add(caratt.id)
            
            val_richiesto = comp.valore
            val_posseduto = punteggi_pg.get(caratt.nome, 0)
            
            if val_posseduto < val_richiesto:
                return Response({"error": f"Non hai abbastanza {caratt.nome} per sostenere questa tecnica (Richiesto: {val_richiesto}, Hai: {val_posseduto})."}, status=status.HTTP_400_BAD_REQUEST)

        # CHECK MODELLO AURA
        modello = personaggio.modelli_aura.filter(aura=proposta.aura).first()
        if modello:
            # 1. Mattoni Proibiti
            # Se esiste un mattone proibito che corrisponde a (Aura Proposta, Caratteristica Usata) -> ERRORE
            proibiti_ids = set(modello.mattoni_proibiti.values_list('id', flat=True))
            if proibiti_ids:
                # Troviamo se tra i componenti c'è una caratteristica che forma un mattone proibito
                # Un mattone è definito da (aura, caratteristica_associata)
                # Quindi cerchiamo Mattone where id in proibiti AND aura = proposta.aura AND caratt in usate
                mattoni_violati = Mattone.objects.filter(
                    id__in=proibiti_ids,
                    aura=proposta.aura,
                    caratteristica_associata__id__in=caratteristiche_usate_ids
                )
                if mattoni_violati.exists():
                    nomi = ", ".join([m.nome for m in mattoni_violati])
                    return Response({"error": f"La proposta usa combinazioni (mattoni) proibite dal modello: {nomi}."}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Mattoni Obbligatori
            # Per ogni mattone obbligatorio, deve esserci la caratteristica corrispondente nella proposta
            mattoni_obbligatori = modello.mattoni_obbligatori.all()
            if mattoni_obbligatori.exists():
                for m_obb in mattoni_obbligatori:
                    # Se il mattone obbligatorio richiede caratteristica X, la proposta deve avere X nei componenti
                    if m_obb.caratteristica_associata.id not in caratteristiche_usate_ids:
                        return Response({"error": f"La proposta manca di un componente obbligatorio: {m_obb.nome} ({m_obb.caratteristica_associata.nome})."}, status=status.HTTP_400_BAD_REQUEST)

        personaggio.modifica_crediti(-costo_invio, f"Invio proposta {proposta.tipo}: {proposta.nome}")
        proposta.costo_invio_pagato = costo_invio
        proposta.stato = STATO_PROPOSTA_IN_VALUTAZIONE
        proposta.data_invio = timezone.now()
        proposta.save()
        return Response(PropostaTecnicaSerializer(proposta).data, status=status.HTTP_200_OK)
    
class AdminPendingProposalsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not (request.user.is_staff or request.user.is_superuser): return Response({"count": 0})
        count = PropostaTecnica.objects.filter(stato=STATO_PROPOSTA_IN_VALUTAZIONE).count()
        return Response({"count": count})
    
class PersonaggioAutocompleteView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonaggioAutocompleteSerializer
    pagination_class = None
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        current_char_id = self.request.query_params.get('current_char_id')
        if len(query) < 2: return Personaggio.objects.none()
        qs = Personaggio.objects.filter(nome__icontains=query)
        if current_char_id: qs = qs.exclude(id=current_char_id)
        return qs[:10]

class MessaggioPrivateCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessaggioCreateSerializer
    def perform_create(self, serializer): serializer.save(mittente=self.request.user)
        
        
class OggettoViewSet(viewsets.ModelViewSet):
    queryset = Oggetto.objects.all()
    serializer_class = OggettoSerializer

    def get_queryset(self): return super().get_queryset()

    @action(detail=False, methods=['post'])
    def craft(self, request):
        infusione_id = request.data.get('infusione_id')
        if not infusione_id: return Response({'error': 'infusione_id mancante'}, status=status.HTTP_400_BAD_REQUEST)
        infusione = get_object_or_404(Infusione, pk=infusione_id)
        if not hasattr(request.user, 'personaggi'): return Response({'error': 'Utente senza personaggi associati'}, status=status.HTTP_400_BAD_REQUEST)
        personaggio = request.user.personaggi.first() 
        if not personaggio: return Response({'error': 'Nessun personaggio trovato per questo utente'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            nuovo_oggetto = GestioneOggettiService.crea_oggetto_da_infusione(infusione, personaggio)
            serializer = self.get_serializer(nuovo_oggetto)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e: return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e: return Response({'error': f"Errore interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # @action(detail=True, methods=['post'])
    # def monta(self, request, pk=None):
    #     oggetto_ospite = self.get_object() 
    #     potenziamento_id = request.data.get('potenziamento_id')
    #     if not potenziamento_id: return Response({'error': 'potenziamento_id mancante'}, status=status.HTTP_400_BAD_REQUEST)
    #     potenziamento = get_object_or_404(Oggetto, pk=potenziamento_id)
    #     personaggio = request.user.personaggi.first() # O logica migliore se ne ha più di uno
    #     if not personaggio:
    #         return Response({'error': 'Nessun personaggio attivo.'}, status=400)
    #     try:
    #         GestioneOggettiService.assembla_mod(personaggio, oggetto_ospite, potenziamento)
    #         serializer = self.get_serializer(oggetto_ospite)
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     except ValidationError as e: return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def smonta(self, request, pk=None):
        oggetto_ospite = self.get_object()
        potenziamento_id = request.data.get('potenziamento_id')
        if not potenziamento_id: return Response({'error': 'potenziamento_id mancante'}, status=status.HTTP_400_BAD_REQUEST)
        potenziamento = get_object_or_404(Oggetto, pk=potenziamento_id, ospitato_su=oggetto_ospite)
        try:
            with transaction.atomic():
                potenziamento.ospitato_su = None
                potenziamento.save()
                inventario_destinazione = oggetto_ospite.inventario_corrente
                if inventario_destinazione: potenziamento.sposta_in_inventario(inventario_destinazione)
            serializer = self.get_serializer(oggetto_ospite)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e: return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def usa_carica(self, request, pk=None):
        oggetto = self.get_object()
        if oggetto.cariche_attuali <= 0: return Response({'error': 'Oggetto scarico o privo di cariche.'}, status=status.HTTP_400_BAD_REQUEST)
        oggetto.cariche_attuali -= 1
        oggetto.save()
        durata_secondi = 0
        if oggetto.infusione_generatrice: durata_secondi = oggetto.infusione_generatrice.durata_attivazione
        return Response({'status': 'success', 'cariche_residue': oggetto.cariche_attuali, 'timer_durata': durata_secondi})

    @action(detail=True, methods=['post'])
    def ricarica(self, request, pk=None):
        oggetto = self.get_object()
        infusione = oggetto.infusione_generatrice
        if not infusione or not infusione.statistica_cariche: return Response({'error': 'Questo oggetto non supporta la ricarica.'}, status=status.HTTP_400_BAD_REQUEST)
        max_cariche = infusione.statistica_cariche.valore_predefinito 
        cariche_mancanti = max_cariche - oggetto.cariche_attuali
        if cariche_mancanti <= 0: return Response({'message': 'Oggetto già completamente carico.'}, status=status.HTTP_200_OK)
        costo_totale = cariche_mancanti * infusione.costo_ricarica_crediti
        inventario = oggetto.inventario_corrente
        personaggio = None
        if inventario:
            if hasattr(inventario, 'personaggio'): personaggio = inventario.personaggio
            elif hasattr(inventario, 'personaggio_ptr'): personaggio = inventario.personaggio_ptr
        if not personaggio: return Response({'error': 'Impossibile determinare il proprietario per il pagamento.'}, status=status.HTTP_400_BAD_REQUEST)
        if personaggio.crediti < costo_totale: return Response({'error': f'Crediti insufficienti. Servono {costo_totale} crediti, ne hai {personaggio.crediti}.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            personaggio.modifica_crediti(-costo_totale, f"Ricarica oggetto: {oggetto.nome}")
            oggetto.cariche_attuali = max_cariche
            oggetto.save()
        return Response({'status': 'success', 'cariche_attuali': oggetto.cariche_attuali, 'costo_pagato': costo_totale, 'crediti_residui': personaggio.crediti})
        
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def equipaggia_item_view(request):
    char_id = request.data.get('char_id')
    item_id = request.data.get('item_id')
    if request.user.is_staff: pg = get_object_or_404(Personaggio, id=char_id)
    else: pg = get_object_or_404(Personaggio, id=char_id, proprietario=request.user)
    oggetto = get_object_or_404(Oggetto, pk=item_id)
    try:
        stato = GestioneOggettiService.equipaggia_oggetto(pg, oggetto)
        return Response({"status": "success", "nuovo_stato": stato})
    except ValidationError as e:
        msg = e.message if hasattr(e, 'message') else str(e)
        return Response({"error": msg}, status=400)

@api_view(['POST'])
@authentication_classes([TokenAuthentication]) 
@permission_classes([IsAuthenticated])
def assembla_item_view(request):
    char_id = request.data.get('char_id')
    host_id = request.data.get('host_id')
    mod_id = request.data.get('mod_id')
    use_academy = request.data.get('use_academy', False) # NUOVO PARAMETRO

    if request.user.is_staff: 
        pg = get_object_or_404(Personaggio, id=char_id)
    else: 
        pg = get_object_or_404(Personaggio, id=char_id, proprietario=request.user)

    host = get_object_or_404(Oggetto, pk=host_id)
    mod = get_object_or_404(Oggetto, pk=mod_id)

    try:
        if use_academy:
            # --- LOGICA ACCADEMIA ---
            COSTO_ACCADEMIA = 100
            if pg.crediti < COSTO_ACCADEMIA:
                return Response({"error": f"Crediti insufficienti per l'Accademia. Servono {COSTO_ACCADEMIA} CR."}, status=400)
            
            with transaction.atomic():
                # 1. Pagamento
                pg.modifica_crediti(-COSTO_ACCADEMIA, "Pagamento servizio assemblaggio Accademia")
                
                # 2. Assemblaggio Forzato (check_skills=False)
                # L'Accademia ha sempre le skill necessarie.
                GestioneOggettiService.assembla_mod(pg, host, mod, check_skills=False)
                
            return Response({"status": "success", "message": "L'Accademia ha completato il lavoro."})
        
        else:
            # --- LOGICA STANDARD (Assemblaggio Fai-da-te) ---
            GestioneOggettiService.assembla_mod(pg, host, mod, check_skills=True)
            return Response({"status": "success", "message": "Assemblaggio completato"})

    except ValidationError as e:
        msg = e.message if hasattr(e, 'message') else str(e)
        return Response({"error": msg}, status=400)
    
    
@api_view(['POST'])
@authentication_classes([TokenAuthentication]) 
@permission_classes([IsAuthenticated])
def smonta_item_view(request):
    char_id = request.data.get('char_id')
    host_id = request.data.get('host_id')
    mod_id = request.data.get('mod_id')
    use_academy = request.data.get('use_academy', False)

    if request.user.is_staff: 
        pg = get_object_or_404(Personaggio, id=char_id)
    else: 
        pg = get_object_or_404(Personaggio, id=char_id, proprietario=request.user)

    host = get_object_or_404(Oggetto, pk=host_id)
    mod = get_object_or_404(Oggetto, pk=mod_id)

    try:
        if use_academy:
            # Costo fisso Accademia (es. 100 crediti anche per smontare)
            COSTO_ACCADEMIA = 100
            if pg.crediti < COSTO_ACCADEMIA:
                return Response({"error": f"Crediti insufficienti. Servono {COSTO_ACCADEMIA} CR."}, status=400)
            
            with transaction.atomic():
                pg.modifica_crediti(-COSTO_ACCADEMIA, "Servizio smontaggio Accademia")
                # Skip skill check
                GestioneOggettiService.rimuovi_mod(pg, host, mod, check_skills=False)
                
            return Response({"status": "success", "message": "Smontaggio completato dall'Accademia."})
        else:
            # Fai da te (con check skill)
            GestioneOggettiService.rimuovi_mod(pg, host, mod, check_skills=True)
            return Response({"status": "success", "message": "Oggetto smontato con successo."})

    except ValidationError as e:
        return Response({"error": str(e)}, status=400)
    

# --- NUOVE CLASSI AGGIUNTE PER NEGOZIO E CRAFTING ---

class NegozioViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def listino(self, request):
        """
        GET /api/negozio/listino/
        Restituisce tutti gli OggettiBase in vendita.
        """
        try:
            oggetti = OggettoBase.objects.filter(in_vendita=True).order_by('tipo_oggetto', 'costo')
            serializer = OggettoBaseSerializer(oggetti, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": f"Errore server: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def acquista(self, request):
        """
        POST /api/negozio/acquista/
        """
        char_id = request.data.get('char_id')
        oggetto_base_id = request.data.get('oggetto_id')
        
        personaggio = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        
        try:
            # Usa il service per creare l'oggetto fisico dal template
            nuovo_oggetto = GestioneCraftingService.acquista_da_negozio(personaggio, oggetto_base_id)
            serializer = OggettoSerializer(nuovo_oggetto, context={'personaggio': personaggio})
            
            return Response({
                "status": "success", 
                "nuovo_oggetto": serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CraftingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def avvia_forgiatura(self, request):
        char_id = request.data.get('char_id')
        inf_id = request.data.get('infusione_id')
        slot = request.data.get('slot_target')
        
        personaggio = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        infusione = get_object_or_404(Infusione, pk=inf_id)
        
        try:
            forgiatura = GestioneCraftingService.avvia_forgiatura(personaggio, infusione, slot)
            return Response({
                "status": "started", 
                "fine_prevista": forgiatura.data_fine_prevista,
                "id_forgiatura": forgiatura.id
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def completa_forgiatura(self, request):
        char_id = request.data.get('char_id')
        forg_id = request.data.get('forgiatura_id')
        
        personaggio = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        
        try:
            oggetto = GestioneCraftingService.completa_forgiatura(forg_id, personaggio)
            return Response({"status": "completed", "oggetto_id": oggetto.id}, status=200)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def coda_forgiatura(self, request):
        char_id = request.query_params.get('char_id')
        personaggio = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        
        coda = ForgiaturaInCorso.objects.filter(personaggio=personaggio)
        data = []
        now = timezone.now()
        for task in coda:
            data.append({
                "id": task.id,
                "infusione_nome": task.infusione.nome,
                "data_inizio": task.data_inizio,
                "data_fine": task.data_fine_prevista,
                "secondi_rimanenti": max(0, (task.data_fine_prevista - now).total_seconds()),
                "is_pronta": task.is_pronta
            })
        return Response(data)


    
class AssemblyValidationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Controlla se l'assemblaggio è possibile tra Host e Component.
        Restituisce info dettagliate: se possibile, se servono skill esterne, etc.
        """
        char_id = request.data.get('char_id')
        host_id = request.data.get('host_id')
        mod_id = request.data.get('mod_id')

        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        host = get_object_or_404(Oggetto, pk=host_id)
        mod = get_object_or_404(Oggetto, pk=mod_id)

        # 1. Verifica Logic/Hardware (senza skill check)
        try:
            # Usiamo assembla_mod in dry-run (simuliamo passando check_skills=False ma catchando errori logici)
            # Nota: assembla_mod modifica il DB, quindi non possiamo chiamarla direttamente.
            # Dobbiamo replicare parzialmente la logica o refactorizzare il service.
            # Per brevità, qui replico i check "hard" rapidi o uso un try/catch con rollback atomico (trick).
            pass
        except:
            pass
            
        # Verifica Skill PG Corrente
        can_do_self, msg_self = GestioneOggettiService.verifica_competenza_assemblaggio(pg, host, mod)
        
        # Simulazione Check Hardware (Limiti classe, slot, etc.)
        # Per semplicità, qui assumiamo che il Frontend abbia già filtrato per tipo.
        # Un check approfondito richiederebbe di duplicare la logica del service.
        # Per ora ci fidiamo del tentativo reale, ma restituiamo info skill.

        return Response({
            "can_assemble_self": can_do_self,
            "reason_self": msg_self,
            "host_name": host.nome,
            "mod_name": mod.nome
        })

class RichiestaAssemblaggioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # Serializer definito inline o in serializers.py. Per brevità lo definisco semplice qui o uso uno generico.
    # Assumiamo tu abbia creato RichiestaAssemblaggioSerializer in serializers.py
    # serializer_class = RichiestaAssemblaggioSerializer 

    def get_queryset(self):
        # Ritorna le richieste dove l'utente è committente o artigiano
        user = self.request.user
        return RichiestaAssemblaggio.objects.filter(
            Q(committente__proprietario=user) | Q(artigiano__proprietario=user)
        ).order_by('-data_creazione')

    @action(detail=False, methods=['post'])
    def crea(self, request):
        committente_id = request.data.get('committente_id')
        artigiano_nome = request.data.get('artigiano_nome') # O ID
        host_id = request.data.get('host_id')
        comp_id = request.data.get('comp_id')
        offerta = int(request.data.get('offerta', 0))

        committente = get_object_or_404(Personaggio, pk=committente_id, proprietario=request.user)
        
        # Trova artigiano (per nome esatto o parziale)
        artigiano = Personaggio.objects.filter(nome__iexact=artigiano_nome).exclude(pk=committente.id).first()
        if not artigiano:
            return Response({"error": "Artigiano non trovato."}, status=404)
            
        host = get_object_or_404(Oggetto, pk=host_id)
        comp = get_object_or_404(Oggetto, pk=comp_id)

        richiesta = RichiestaAssemblaggio.objects.create(
            committente=committente,
            artigiano=artigiano,
            oggetto_host=host,
            componente=comp,
            offerta_crediti=offerta
        )
        
        # Creiamo anche una notifica/messaggio per l'artigiano
        Messaggio.objects.create(
            mittente=request.user,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            destinatario_personaggio=artigiano,
            titolo="Richiesta di Lavoro",
            testo=f"{committente.nome} richiede il tuo intervento per assemblare {comp.nome} su {host.nome}. Offerta: {offerta} CR."
        )

        return Response({"status": "created", "id": richiesta.id}, status=201)

    @action(detail=True, methods=['post'])
    def accetta(self, request, pk=None):
        richiesta = self.get_object()
        if richiesta.artigiano.proprietario != request.user:
            return Response({"error": "Non autorizzato"}, status=403)
            
        try:
            GestioneOggettiService.elabora_richiesta_assemblaggio(richiesta.id, request.user)
            return Response({"status": "success", "message": "Lavoro completato!"})
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
            
    @action(detail=True, methods=['post'])
    def rifiuta(self, request, pk=None):
        richiesta = self.get_object()
        if richiesta.artigiano.proprietario != request.user:
             return Response({"error": "Non autorizzato"}, status=403)
        
        richiesta.stato = 'RIFI'
        richiesta.save()
        return Response({"status": "rejected"})
    
class AssemblyValidationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Controlla se l'assemblaggio è possibile tra Host e Component.
        """
        char_id = request.data.get('char_id')
        host_id = request.data.get('host_id')
        mod_id = request.data.get('mod_id')

        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        host = get_object_or_404(Oggetto, pk=host_id)
        mod = get_object_or_404(Oggetto, pk=mod_id)

        # Verifica Competenze tramite Service
        can_do_self, msg_self = GestioneOggettiService.verifica_competenza_assemblaggio(pg, host, mod)

        # Qui potresti aggiungere anche controlli hardware (slot liberi, classi) 
        # ma per ora ci fidiamo del filtro frontend + check finale

        return Response({
            "can_assemble_self": can_do_self,
            "reason_self": msg_self,
            "host_name": host.nome,
            "mod_name": mod.nome
        })

class RichiestaAssemblaggioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RichiestaAssemblaggioSerializer 

    def get_queryset(self):
        user = self.request.user
        return RichiestaAssemblaggio.objects.filter(
            Q(committente__proprietario=user) | Q(artigiano__proprietario=user)
        ).order_by('-data_creazione')

    @action(detail=False, methods=['post'])
    def crea(self, request):
        committente_id = request.data.get('committente_id')
        artigiano_nome = request.data.get('artigiano_nome')
        host_id = request.data.get('host_id')
        comp_id = request.data.get('comp_id')
        offerta = int(request.data.get('offerta', 0))
        
        # NUOVO: Leggi il tipo operazione (Default a 'INST')
        tipo_op = request.data.get('tipo_operazione', 'INST') 
        infusione_id = request.data.get('infusione_id')

        committente = get_object_or_404(Personaggio, pk=committente_id, proprietario=request.user)
        # Trova artigiano (case insensitive, escluso se stesso)
        artigiano = Personaggio.objects.filter(nome__iexact=artigiano_nome).exclude(pk=committente.id).first()

        host = None
        comp = None
        infusione = None

        if not artigiano:
            return Response({"error": "Artigiano non trovato."}, status=404)

        if tipo_op =='FORG':
            if not infusione_id: return Response({"error": "Infusione mancante"}, status=400)
            infusione = get_object_or_404(Infusione, pk=infusione_id)
        else:
            host = get_object_or_404(Oggetto, pk=host_id)
            comp = get_object_or_404(Oggetto, pk=comp_id)
        

        richiesta = RichiestaAssemblaggio.objects.create(
            committente=committente,
            artigiano=artigiano,
            oggetto_host=host,
            componente=comp,
            infusione=infusione,
            offerta_crediti=offerta,
            tipo_operazione=tipo_op
        )
        
        verbo = "---"
        if tipo_op == "RIMO":
            verbo = "rimuovere" 
        elif tipo_op == "FORG":
            verbo = "forgiare"
        else:
            verbo = "assemblare"
        
        Messaggio.objects.create(
            mittente=request.user,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            destinatario_personaggio=artigiano,
            titolo="Nuova Richiesta di Lavoro",
            testo=f"{committente.nome} richiede il tuo intervento per {verbo} {comp.nome} su {host.nome}. Offerta: {offerta} CR."
        )

        return Response({"status": "created", "id": richiesta.id}, status=201)

    @action(detail=True, methods=['post'])
    def accetta(self, request, pk=None):
        richiesta = self.get_object()
        
        # MODIFICA: Permetti l'azione se sei il proprietario O se sei Admin/Staff
        is_owner = richiesta.artigiano.proprietario == request.user
        is_admin = request.user.is_staff or request.user.is_superuser
        
        if not is_owner and not is_admin:
            return Response({"error": "Non autorizzato"}, status=403)
            
        try:
            # Passiamo l'utente che sta eseguendo l'azione (admin o proprietario)
            GestioneOggettiService.elabora_richiesta_assemblaggio(richiesta.id, request.user)
            return Response({"status": "success", "message": "Lavoro completato!"})
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def rifiuta(self, request, pk=None):
        richiesta = self.get_object()
        if richiesta.artigiano.proprietario != request.user:
             return Response({"error": "Non autorizzato"}, status=403)

        richiesta.stato = 'RIFI' # Usa la costante importata se disponibile
        richiesta.save()
        return Response({"status": "rejected"})
    
class CapableArtisansView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get('char_id')
        host_id = request.data.get('host_id')
        mod_id = request.data.get('mod_id')

        try:
            requester = Personaggio.objects.get(pk=char_id)
            host = Oggetto.objects.get(pk=host_id)
            mod = Oggetto.objects.get(pk=mod_id)
            
            # Filtro semplificato per DEBUG: Prende tutti tranne me
            # Rimuoviamo temporaneamente proprietario__is_active per testare
            candidati = Personaggio.objects.exclude(id=requester.id).filter(data_morte__isnull=True)
            
            print(f"--- DEBUG ARTIGIANI ---")
            print(f"Richiedente: {requester.nome}")
            print(f"Candidati trovati (grezzi): {candidati.count()}")
            
            # --- CORREZIONE QUI ---
            # Filtriamo i candidati:
            # 1. Escludiamo chi fa la richiesta (exclude id=requester.id)
            # 2. Escludiamo i personaggi morti (data_morte__isnull=True)
            # 3. (Opzionale) Escludiamo utenti bannati/inattivi (proprietario__is_active=True)
            candidati = Personaggio.objects.exclude(id=requester.id).filter(
                data_morte__isnull=True, 
                proprietario__is_active=True
            )
            
            capaci = []
            for artigiano in candidati:
                can_do, msg = GestioneOggettiService.verifica_competenza_assemblaggio(artigiano, host, mod)
                print(f"Check {artigiano.nome}: {can_do} -> {msg}") # VEDI QUESTO NEL LOG
                
                if can_do:
                    capaci.append({
                        "id": artigiano.id, 
                        "nome": artigiano.nome,
                    })
            
            return Response(capaci)

        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
# --- VIEW FORGIATURA AGGIORNATA ---
@api_view(['POST'])
@authentication_classes([TokenAuthentication]) 
@permission_classes([IsAuthenticated])
def forgia_item_view(request):
    """
    Avvia la forgiatura.
    - use_academy=True: Paga 200, ignora requisiti, avvia timer.
    - use_academy=False: Paga materiali, check requisiti, avvia timer.
    """
    char_id = request.data.get('char_id')
    infusione_id = request.data.get('infusione_id')
    use_academy = request.data.get('use_academy', False)

    if request.user.is_staff: pg = get_object_or_404(Personaggio, id=char_id)
    else: pg = get_object_or_404(Personaggio, id=char_id, proprietario=request.user)

    infusione = get_object_or_404(Infusione, pk=infusione_id)

    try:
        # Il Service gestisce tutto (costi differenziati e timer)
        GestioneCraftingService.avvia_forgiatura(
            personaggio=pg, 
            infusione=infusione, 
            is_academy=use_academy
        )
        
        msg = "Lavoro Accademia avviato." if use_academy else "Forgiatura avviata."
        return Response({"status": "success", "message": f"{msg} Controlla la coda di lavoro."})

    except ValidationError as e:
        return Response({"error": str(e)}, status=400)


# --- RICERCA ARTIGIANI ---
class CapableArtisansView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get('char_id')
        infusione_id = request.data.get('infusione_id')
        host_id = request.data.get('host_id')
        mod_id = request.data.get('mod_id')

        try:
            requester = Personaggio.objects.get(pk=char_id)
            candidati = Personaggio.objects.exclude(id=requester.id).filter(
                data_morte__isnull=True, proprietario__is_active=True
            )
            
            capaci = []
            
            if infusione_id:
                # --- LOGICA FORGIATURA COOPERATIVA ---
                inf = Infusione.objects.get(pk=infusione_id)
                
                # Check Preliminare: Il richiedente (Forgiatore) HA l'aura principale?
                # Se non ce l'ha, non può nemmeno chiedere aiuto.
                if requester.get_valore_aura_effettivo(inf.aura_richiesta) < inf.livello:
                    # Ritorna lista vuota o errore specifico? 
                    # Meglio lista vuota così il frontend capisce che non ci sono opzioni
                    return Response([]) 

                for p in candidati:
                    # Verifica se questo candidato (p), agendo come aiutante, completa i requisiti del richiedente
                    ok, _ = GestioneCraftingService.verifica_competenza_forgiatura(
                        forgiatore=requester, 
                        infusione=inf, 
                        aiutante=p
                    )
                    if ok: 
                        capaci.append({"id": p.id, "nome": p.nome})
                        
            else:
                # --- LOGICA ASSEMBLAGGIO (Invariata) ---
                host = Oggetto.objects.get(pk=host_id)
                mod = Oggetto.objects.get(pk=mod_id)
                for p in candidati:
                    # Qui l'artigiano fa tutto da solo
                    ok, _ = GestioneOggettiService.verifica_competenza_assemblaggio(p, host, mod)
                    if ok: capaci.append({"id": p.id, "nome": p.nome})
            
            return Response(capaci)

        except Exception as e:
            return Response({"error": str(e)}, status=400)