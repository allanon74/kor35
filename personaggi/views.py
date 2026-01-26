import string
from collections import Counter
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Count, Sum, Prefetch, OuterRef, Exists, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpRequest
from rest_framework import serializers
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
    PropostaTransazione,
    Gruppo, Messaggio, Tabella, Mattone, 
    OggettoBase, ForgiaturaInCorso, 
    abilita_tier, abilita_requisito, abilita_sbloccata, 
    abilita_punteggio, abilita_prerequisito,
    # Costanti
    COSTO_PER_MATTONE_CREAZIONE, 
    COSTO_DEFAULT_INVIO_PROPOSTA,
    RichiestaAssemblaggio, STATO_RICHIESTA_PENDENTE,
    ClasseOggetto, Statistica, 
    ConfigurazioneLivelloAura, Cerimoniale,
    StatoTimerAttivo,
    TipologiaPersonaggio,
)

import uuid 
import qrcode
import io
import base64
from django.utils.html import escape
from datetime import timedelta

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
    ChangePasswordSerializer, OggettoSerializer, AttivataSerializer, InfusioneSerializer, TessituraSerializer,
    ManifestoSerializer, A_vistaSerializer, InventarioSerializer,
    PersonaggioDetailSerializer, CreditoMovimentoCreateSerializer, PersonaggioListSerializer,
    TransazioneSospesaSerializer, PropostaTransazioneSerializer, 
    PuntiCaratteristicaMovimentoCreateSerializer, TransazioneCreateSerializer, 
    TransazioneSospesaSerializer, TransazioneConfermaSerializer, PropostaTransazioneSerializer,
    RubaSerializer, 
    AcquisisciSerializer, PunteggioDetailSerializer, ModelloAuraSerializer,
    PropostaTecnicaSerializer, PersonaggioLogSerializer, PersonaggioAutocompleteSerializer,
    MessaggioCreateSerializer, MessaggioSerializer, MessaggioBroadcastCreateSerializer,
    AbilitaMasterListSerializer, PersonaggioPublicSerializer,
    AbilSerializer, AbilitaSerializer, AbilitaUpdateSerializer, TierSerializer, 
    PunteggioSerializer, TabellaSerializer,
    AbilitaTierSerializer, AbilitaRequisitoSerializer, AbilitaSbloccataSerializer,
    AbilitaPunteggioSerializer, AbilitaPrerequisitoSerializer, UserSerializer,
    OggettoBaseSerializer, RichiestaAssemblaggioSerializer,
    ClasseOggettoSerializer, CerimonialeSerializer, StatoTimerSerializer,
    StatisticaSerializer, TipologiaPersonaggioSerializer, 
    PersonaggioManageSerializer, SSOUserSerializer,
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
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
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
    # queryset = Punteggio.objects.all()
    serializer_class = PunteggioSerializer
    authentication_classes = (TokenAuthentication,)
    
    def get_queryset(self):
        """
        Questa query è ottimizzata per scaricare in 2 sole query SQL:
        1. Tutte le Aure e le loro Configurazioni Livelli.
        2. Tutte le Abilità 'Tratto' collegate, inclusa la loro caratteristica.
        """
        
        # 1. Prepariamo la regola per scaricare i TRATTI (le opzioni selezionabili)
        #    e li mettiamo nell'attributo 'tratti_aura_prefetched' che il Serializer cerca.
        prefetch_tratti = Prefetch(
            'tratti_collegati',  # Questo deve essere il related_name in Abilita.aura_riferimento
            queryset=Abilita.objects.filter(is_tratto_aura=True)
            .select_related('caratteristica')
            .prefetch_related('abilitastatistica_set__statistica'),
            to_attr='tratti_aura_prefetched'
        )

        # 2. Prepariamo la regola per scaricare la CONFIGURAZIONE (Archetipo, Sottotipo...)
        #    ordinata per livello
        prefetch_config = Prefetch(
            'configurazione_livelli', # related_name in ConfigurazioneLivelloAura.aura
            queryset=ConfigurazioneLivelloAura.objects.order_by('livello')
        )

        # 3. Eseguiamo la query principale unendo i pezzi
        return Punteggio.objects.all().prefetch_related(
            prefetch_config,
            prefetch_tratti
        ).order_by('tipo', 'ordine', 'nome')
        
    @action(detail=True, methods=['get'])
    def mattoni(self, request, pk=None):
        """Restituisce solo i mattoni legati a questa specifica Aura."""
        aura = self.get_object()
        # Filtriamo i mattoni dell'aura e carichiamo la caratteristica associata
        mattoni = Mattone.objects.filter(aura=aura).select_related('caratteristica_associata')
        
        # Costruiamo una risposta semplice con i dati necessari al frontend
        data = []
        for m in mattoni:
            data.append({
                'id': m.id,
                'nome': m.nome,
                'sigla': m.sigla, # Sigla del mattone (es. DRD)
                'caratteristica_associata': {
                    'id': m.caratteristica_associata.id,
                    'nome': m.caratteristica_associata.nome,
                    'sigla': m.caratteristica_associata.sigla, # Sigla caratteristica (es. MIR)
                }
            })
        return Response(data)

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
    
class CerimonialiAcquistabiliView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CerimonialeSerializer

    def get(self, request, format=None):
        character_id = request.query_params.get('char_id')
        if not character_id: 
            return Response({"error": "L'ID del personaggio è richiesto."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            personaggio = Personaggio.objects.select_related('tipologia').get(id=character_id)
        except Personaggio.DoesNotExist: 
            return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        
        if personaggio.proprietario != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)

        # Escludi quelli già posseduti
        possedute_ids = personaggio.cerimoniali_posseduti.values_list('id', flat=True)
        
        tutti_cerimoniali = Cerimoniale.objects.exclude(id__in=possedute_ids).select_related(
            'aura_richiesta'
        ).prefetch_related(
            'componenti__caratteristica'
        ).order_by('liv', 'nome')

        acquistabili = []
        for cer in tutti_cerimoniali:
            # Usa il metodo di validazione che abbiamo aggiornato nel modello Personaggio
            is_valid, _ = personaggio.valida_acquisto_tecnica(cer)
            if is_valid:
                acquistabili.append(cer)

        serializer = CerimonialeSerializer(acquistabili, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcquisisciCerimonialeView(APIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic 
    def post(self, request, format=None):
        personaggio_id = request.data.get('personaggio_id')
        cerimoniale_id = request.data.get('cerimoniale_id')
        
        if not personaggio_id or not cerimoniale_id: 
            return Response({"error": "Dati mancanti."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            personaggio = Personaggio.objects.get(id=personaggio_id, proprietario=request.user)
            cerimoniale = Cerimoniale.objects.prefetch_related('componenti').get(id=cerimoniale_id)
        except (Personaggio.DoesNotExist, Cerimoniale.DoesNotExist): 
            return Response({"error": "Oggetto non trovato."}, status=status.HTTP_404_NOT_FOUND)

        # Verifica requisiti
        is_valid, error_msg = personaggio.valida_acquisto_tecnica(cerimoniale)
        if not is_valid: 
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        if personaggio.cerimoniali_posseduti.filter(id=cerimoniale.id).exists(): 
            return Response({"error": "Cerimoniale già conosciuto."}, status=status.HTTP_400_BAD_REQUEST)

        costo = cerimoniale.costo_crediti
        if personaggio.crediti < costo: 
            return Response({"error": f"Crediti insufficienti. Richiesti: {costo}"}, status=status.HTTP_400_BAD_REQUEST)

        # Esegui transazione
        personaggio.modifica_crediti(-costo, f"Appreso cerimoniale: {cerimoniale.nome}")
        personaggio.cerimoniali_posseduti.add(cerimoniale)
        personaggio.aggiungi_log(f"Ha appreso il cerimoniale '{cerimoniale.nome}' (Liv. {cerimoniale.livello}).")
        
        # Gestione Royalty (Opzionale, come per le altre tecniche)
        if hasattr(cerimoniale, 'proposta_creazione') and cerimoniale.proposta_creazione:
            creatore = cerimoniale.proposta_creazione.personaggio
            if creatore and creatore.id != personaggio.id:
                royalty = int(round(costo * 0.10))
                if royalty > 0:
                    creatore.modifica_crediti(royalty, f"Royalty per '{cerimoniale.nome}' da {personaggio.nome}")

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
        except QrCode.DoesNotExist:
            return Response({"error": "QrCode non trovato."}, status=status.HTTP_404_NOT_FOUND)
        
        # --- LOGICA NUOVA: Controllo se è un Timer ---
        configurazione_timer = getattr(qr_code, 'configurazione_timer', None)
        if configurazione_timer:
            return self.gestisci_scansione_timer(configurazione_timer)

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
    
    def gestisci_scansione_timer(self, config):
        ora_attuale = timezone.now()
        oggi = ora_attuale.date()
        
        # Logica di Stacking (Somma del tempo)
        stato, created = StatoTimerAttivo.objects.get_or_create(
            tipologia=config.tipologia,
            defaults={'data_fine': ora_attuale}
        )
        if config.ultima_attivazione == oggi:
            return Response({
                "error": "carica_esaurita",
                "message": "Carica esaurita per oggi! Questo componente può essere attivato solo una volta al giorno."
            }, status=status.HTTP_403_FORBIDDEN)
            
        if not created and stato.data_fine > ora_attuale:
            # Aggiungo la durata del QR al tempo rimanente del primo
            stato.data_fine += timedelta(seconds=config.durata_secondi)
        else:
            # Il timer era scaduto o nuovo, parte da ora + durata
            stato.data_fine = ora_attuale + timedelta(seconds=config.durata_secondi)
        
        # 3. SALVATAGGIO STATI
        with transaction.atomic():
            stato.save()
            # Registriamo l'attivazione per questo QR specifico
            config.ultima_attivazione = oggi
            config.save()
        
        stato.save()

        # BROADCAST via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'kor35_notifications', # Il gruppo che usi nel tuo NotificationConsumer
            {
                'type': 'send_notification',
                'message': {
                    'action': 'TIMER_SYNC',
                    'payload': {
                        'id': stato.id,
                        'nome': config.tipologia.nome,
                        'data_fine': stato.data_fine.isoformat(),
                        'alert_suono': config.tipologia.alert_suono,
                        'notifica_push': config.tipologia.notifica_push,
                        'messaggio_in_app': config.tipologia.messaggio_in_app,
                    }
                }
            }
        )

        return Response({
            "tipo_modello": "timer_attivato",
            "messaggio": f"Timer {config.tipologia.nome} avviato/esteso!",
            "dati": { "nome": config.tipologia.nome, "scadenza": stato.data_fine }
        })
    
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
        ).select_related('personaggio').order_by('-data')

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
            return TransazioneSospesa.objects.filter(mittente__id__in=inventari_ids).select_related(
                'mittente', 'richiedente', 'oggetto'
            ).order_by('-data_richiesta')
        else:
            return TransazioneSospesa.objects.filter(richiedente__id__in=pg_ids).select_related(
                'mittente', 'richiedente', 'oggetto'
            ).order_by('-data_richiesta')

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
            # Supporta sia sistema legacy che nuovo
            transazione = TransazioneSospesa.objects.filter(
                pk=pk, stato=STATO_TRANSAZIONE_IN_ATTESA
            ).filter(
                Q(mittente=personaggio_mittente.inventario_ptr) | 
                Q(destinatario=personaggio_mittente) |
                Q(iniziatore=personaggio_mittente)
            ).first()
            if not transazione:
                return Response({"error": "Transazione non trovata, già processata o non autorizzata."}, status=status.HTTP_404_NOT_FOUND)
        except TransazioneSospesa.DoesNotExist: return Response({"error": "Transazione non trovata, già processata o non autorizzata."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TransazioneConfermaSerializer(data=request.data, context={'transazione': transazione})
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"success": f"Transazione {serializer.validated_data['azione']}ta."}, status=status.HTTP_200_OK)
            except Exception as e: return Response({"error": f"Errore durante l'azione: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransazioneAvanzataCreateView(APIView):
    """Crea una nuova transazione avanzata con proposta iniziale"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, format=None):
        try:
            iniziatore = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        
        from .serializers import TransazioneAvanzataCreateSerializer
        serializer = TransazioneAvanzataCreateSerializer(data=request.data, context={'iniziatore': iniziatore})
        if serializer.is_valid():
            try:
                transazione = serializer.save()
                response_serializer = TransazioneSospesaSerializer(transazione)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": f"Errore durante la creazione: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TransazioneDetailView(APIView):
    """Dettaglio di una transazione con tutte le proposte"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk, format=None):
        try:
            personaggio = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response({"error": "Nessun personaggio trovato."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            transazione = TransazioneSospesa.objects.filter(
                pk=pk
            ).filter(
                Q(mittente=personaggio.inventario_ptr) | 
                Q(richiedente=personaggio) |
                Q(destinatario=personaggio) |
                Q(iniziatore=personaggio)
            ).prefetch_related('proposte__oggetti_da_dare', 'proposte__oggetti_da_ricevere', 'proposte__autore').first()
            
            if not transazione:
                return Response({"error": "Transazione non trovata o non autorizzata."}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = TransazioneSospesaSerializer(transazione)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TransazioneSospesa.DoesNotExist:
            return Response({"error": "Transazione non trovata."}, status=status.HTTP_404_NOT_FOUND)

class PropostaTransazioneCreateView(APIView):
    """Aggiunge una proposta (controproposta o rilancio) a una transazione"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk, format=None):
        try:
            autore = Personaggio.objects.get(proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response({"error": "Nessun personaggio trovato per questo utente."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            transazione = TransazioneSospesa.objects.filter(
                pk=pk, stato=STATO_TRANSAZIONE_IN_ATTESA
            ).filter(
                Q(destinatario=autore) | Q(iniziatore=autore)
            ).first()
            
            if not transazione:
                return Response({"error": "Transazione non trovata o non autorizzata."}, status=status.HTTP_404_NOT_FOUND)
            
            # Verifica che l'autore sia parte della transazione
            if transazione.iniziatore != autore and transazione.destinatario != autore:
                return Response({"error": "Non sei autorizzato a proporre per questa transazione."}, status=status.HTTP_403_FORBIDDEN)
            
            from .serializers import PropostaTransazioneCreateSerializer
            serializer = PropostaTransazioneCreateSerializer(
                data=request.data, 
                context={'transazione': transazione, 'autore': autore}
            )
            if serializer.is_valid():
                proposta = serializer.save()
                response_serializer = PropostaTransazioneSerializer(proposta)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except TransazioneSospesa.DoesNotExist:
            return Response({"error": "Transazione non trovata."}, status=status.HTTP_404_NOT_FOUND)
    
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
    
    def patch(self, request, pk, format=None):
        personaggio = get_object_or_404(Personaggio, pk=pk)
        
        # Controllo permessi (solo il proprietario o admin)
        if not (request.user.is_staff or request.user.is_superuser) and personaggio.proprietario != request.user:
            return Response({"error": "Non hai il permesso di modificare questo personaggio."}, status=status.HTTP_403_FORBIDDEN)
        
        # Usiamo il serializer esistente con partial=True per l'update parziale
        serializer = PersonaggioDetailSerializer(personaggio, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PersonaggioModificatoriDettagliatiView(APIView):
    """
    Restituisce i dettagli dei modificatori di un personaggio con la fonte di provenienza.
    Endpoint: GET /api/personaggi/<pk>/modificatori-dettagliati/
    Opzionale: ?parametro=<nome_parametro> per filtrare una singola statistica
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk, format=None):
        personaggio = get_object_or_404(Personaggio, pk=pk)
        user = request.user
        
        # Controllo permessi
        if not (user.is_staff or user.is_superuser) and personaggio.proprietario != user:
            return Response(
                {"error": "Non hai il permesso di visualizzare questo personaggio."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Ottieni i dettagli
        dettagli = personaggio.get_modificatori_dettagliati()
        
        # Filtro opzionale per una singola statistica
        parametro_filter = request.query_params.get('parametro', None)
        if parametro_filter:
            if parametro_filter in dettagli:
                return Response({parametro_filter: dettagli[parametro_filter]}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": f"Parametro '{parametro_filter}' non trovato."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(dettagli, status=status.HTTP_200_OK)
    
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

        # CORRETTO: Usa Subquery per ottenere il VALORE del campo 'letto'
        # Coalesce gestisce il caso None (quando non esiste il record) -> False
        lettura_stato = LetturaMessaggio.objects.filter(
            messaggio=OuterRef('pk'),
            personaggio=target_pg
        ).values('letto')[:1]
        
        return messaggi.exclude(id__in=ids_cancellati).annotate(
            is_letto_db=Coalesce(Subquery(lettura_stato), Value(False))
        )
    
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
        elif action_type == 'toggle_letto':
            stato.letto = not stato.letto
            if stato.letto and not stato.data_lettura:
                stato.data_lettura = timezone.now()
            stato.save()
            return Response({"status": "Stato lettura cambiato", "letto": stato.letto})
        elif action_type == 'cancella':
            stato.cancellato = True
            stato.save()
            return Response({"status": "Messaggio cancellato"})
        return Response({"error": "Azione non valida"}, status=status.HTTP_400_BAD_REQUEST)

class ConversazioniView(APIView):
    """View per ottenere messaggi organizzati per conversazione"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        personaggio_id = request.query_params.get('personaggio_id')
        if not personaggio_id:
            return Response({"error": "personaggio_id mancante"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            personaggio = Personaggio.objects.get(id=personaggio_id, proprietario=request.user)
        except Personaggio.DoesNotExist:
            return Response({"error": "Personaggio non trovato"}, status=status.HTTP_404_NOT_FOUND)
        
        # Recupera tutti i messaggi del personaggio (broadcast esclusi per le conversazioni)
        q_individuale_ricevuti = Q(tipo_messaggio=Messaggio.TIPO_INDIVIDUALE) & Q(destinatario_personaggio=personaggio)
        q_individuale_inviati = Q(tipo_messaggio=Messaggio.TIPO_STAFF) & Q(mittente_personaggio=personaggio)
        
        messaggi = Messaggio.objects.filter(q_individuale_ricevuti | q_individuale_inviati).select_related(
            'mittente', 'mittente_personaggio', 'destinatario_personaggio', 'in_risposta_a'
        )
        
        # Filtra messaggi cancellati
        ids_cancellati = LetturaMessaggio.objects.filter(
            personaggio=personaggio, 
            cancellato=True
        ).values_list('messaggio_id', flat=True)
        
        messaggi = messaggi.exclude(id__in=ids_cancellati)
        
        # Raggruppa per conversazione (thread)
        conversazioni = {}
        
        for msg in messaggi:
            # Trova il messaggio radice (se è una risposta, risale al primo messaggio)
            thread_id = msg.id
            current_msg = msg
            while current_msg.in_risposta_a:
                thread_id = current_msg.in_risposta_a.id
                current_msg = current_msg.in_risposta_a
            
            if thread_id not in conversazioni:
                conversazioni[thread_id] = {
                    'conversazione_id': thread_id,
                    'messaggi': [],
                    'partecipanti': set(),
                    'ultimo_messaggio': msg.data_invio,
                    'non_letti': 0
                }
            
            conversazioni[thread_id]['messaggi'].append(msg)
            
            # Aggiungi partecipanti
            if msg.mittente:
                conversazioni[thread_id]['partecipanti'].add(('user', msg.mittente.id, msg.mittente.username))
            if msg.mittente_personaggio:
                conversazioni[thread_id]['partecipanti'].add(('pg', msg.mittente_personaggio.id, msg.mittente_personaggio.nome))
            if msg.destinatario_personaggio:
                conversazioni[thread_id]['partecipanti'].add(('pg', msg.destinatario_personaggio.id, msg.destinatario_personaggio.nome))
            
            # Aggiorna timestamp ultimo messaggio
            if msg.data_invio > conversazioni[thread_id]['ultimo_messaggio']:
                conversazioni[thread_id]['ultimo_messaggio'] = msg.data_invio
            
            # Conta non letti
            lettura = LetturaMessaggio.objects.filter(messaggio=msg, personaggio=personaggio, letto=True).first()
            if not lettura:
                conversazioni[thread_id]['non_letti'] += 1
        
        # Converti conversazioni in lista e ordina
        risultato = []
        for conv_id, conv_data in conversazioni.items():
            # Ordina messaggi per data
            conv_data['messaggi'].sort(key=lambda x: x.data_invio)
            
            # Converti partecipanti da set a lista di dict
            conv_data['partecipanti'] = [
                {'tipo': p[0], 'id': p[1], 'nome': p[2]} 
                for p in conv_data['partecipanti']
            ]
            
            # Serializza messaggi
            messaggi_serializer = MessaggioSerializer(conv_data['messaggi'], many=True, context={'request': request})
            conv_data['messaggi'] = messaggi_serializer.data
            
            risultato.append(conv_data)
        
        # Ordina conversazioni per ultimo messaggio (più recente primo)
        risultato.sort(key=lambda x: x['ultimo_messaggio'], reverse=True)
        
        return Response(risultato)

class RispondiMessaggioView(APIView):
    """View per rispondere a un messaggio creando un thread"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, messaggio_id):
        personaggio_id = request.data.get('personaggio_id')
        testo = request.data.get('testo')
        titolo = request.data.get('titolo', '')
        
        if not personaggio_id or not testo:
            return Response(
                {"error": "personaggio_id e testo sono obbligatori"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            personaggio = Personaggio.objects.get(id=personaggio_id, proprietario=request.user)
            messaggio_originale = Messaggio.objects.get(pk=messaggio_id)
        except (Personaggio.DoesNotExist, Messaggio.DoesNotExist):
            return Response({"error": "Dati non validi"}, status=status.HTTP_404_NOT_FOUND)
        
        # Crea la risposta
        risposta = Messaggio.objects.create(
            mittente_personaggio=personaggio,
            tipo_messaggio=Messaggio.TIPO_STAFF,  # Risposta a staff
            titolo=titolo or f"Re: {messaggio_originale.titolo}",
            testo=testo,
            in_risposta_a=messaggio_originale,
            is_staff_message=False  # È una risposta del giocatore
        )
        
        serializer = MessaggioSerializer(risposta, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        if proposta.tipo == 'CER':
             # Per i cerimoniali usiamo il livello scelto manualmente
             livello = getattr(proposta, 'livello_proposto', 1)
        if livello == 0:
            return Response({"error": "La proposta deve avere almeno un componente."}, status=status.HTTP_400_BAD_REQUEST)

# --- CALCOLO COSTO INVIO (BUROCRAZIA) ---
        costo_base = COSTO_DEFAULT_INVIO_PROPOSTA # Default 10
        
        if proposta.tipo == 'INF':
             # Cerca la statistica specifica per l'invio proposta INF
             if proposta.aura.stat_costo_invio_proposta_infusione:
                 val = proposta.aura.stat_costo_invio_proposta_infusione.valore_base_predefinito
                 if val > 0: costo_base = val
        elif proposta.tipo == 'TES':
             # Cerca la statistica specifica per l'invio proposta TES
             if proposta.aura.stat_costo_invio_proposta_tessitura:
                 val = proposta.aura.stat_costo_invio_proposta_tessitura.valore_base_predefinito
                 if val > 0: costo_base = val
        elif proposta.tipo == 'CER':
             # Cerca la statistica specifica per l'invio proposta CER
             if proposta.aura.stat_costo_invio_proposta_cerimoniale:
                 val = proposta.aura.stat_costo_invio_proposta_cerimoniale.valore_base_predefinito
                 if val > 0: costo_base = val
        
                 
        costo_invio = livello * costo_base

        if personaggio.crediti < costo_invio: 
            return Response({"error": f"Crediti insufficienti. Richiesti: {costo_invio} CR."}, status=status.HTTP_400_BAD_REQUEST)

        val_aura = personaggio.get_valore_aura_effettivo(proposta.aura)
        if val_aura < 1: return Response({"error": "Non possiedi l'aura selezionata."}, status=status.HTTP_400_BAD_REQUEST)
        if livello > val_aura: return Response({"error": f"Troppi componenti ({livello}) per il valore della tua aura ({val_aura})."}, status=status.HTTP_400_BAD_REQUEST)
        
        if proposta.tipo == 'CER':
            valore_cco = personaggio.get_valore_statistica('CCO')
            if valore_cco < livello:
                return Response({"error": f"Coralità (CCO) insufficiente (Serve {livello}, hai {valore_cco})."}, status=400)

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
        query = self.request.query_params.get('q', '').strip() # Strip per pulire spazi vuoti
        current_char_id = self.request.query_params.get('current_char_id')
        infusione_id = self.request.query_params.get('infusione_id')

        # MODIFICA: Se c'è infusione_id (selezione candidato), permettiamo query vuota
        # Altrimenti (autocomplete normale), richiediamo almeno 2 caratteri
        if not infusione_id and len(query) < 2: 
            return Personaggio.objects.none()
        
        # 1. Filtro base
        qs = Personaggio.objects.all()
        
        # Se c'è una query di testo, filtriamo per nome
        if query:
            qs = qs.filter(nome__icontains=query)
            
        if current_char_id: 
            qs = qs.exclude(id=current_char_id)
        
        # 2. Filtro per compatibilità innesto
        if infusione_id:
            try:
                inf = Infusione.objects.get(pk=infusione_id)
                valid_ids = []
                # Limitiamo il check python a 50 candidati per performance
                candidates = qs[:50] 
                for pg in candidates:
                    if GestioneOggettiService.verifica_requisiti_supporto_innesto(pg, inf):
                        valid_ids.append(pg.id)
                qs = qs.filter(id__in=valid_ids)
            except Infusione.DoesNotExist:
                pass

        return qs[:10]

class MessaggioPrivateCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessaggioCreateSerializer
    
    def perform_create(self, serializer):
        # Recupera il personaggio mittente
        personaggio_mittente = Personaggio.objects.filter(proprietario=self.request.user).first()
        
        # Se is_staff_message è True, crea un messaggio allo staff
        if self.request.data.get('is_staff_message'):
            serializer.save(
                mittente=self.request.user,
                mittente_personaggio=personaggio_mittente,
                tipo_messaggio=Messaggio.TIPO_STAFF,
                is_staff_message=True,
                destinatario_personaggio=None  # Non c'è destinatario specifico per lo staff
            )
        else:
            # Messaggio normale a un altro personaggio
            serializer.save(
                mittente=self.request.user,
                mittente_personaggio=personaggio_mittente
            )
        
        
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
        slot_scelto = request.data.get('slot_scelto')
        target_id = request.data.get('target_id') # <--- LEGGI NUOVO PARAMETRO
        
        # Verifica chi sta chiamando (Il forgiatore)
        personaggio = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        
        # Verifica destinatario diretto (se presente)
        destinatario_obj = None
        if target_id:
            # SICUREZZA: Per l'installazione diretta, il target DEVE appartenere all'utente loggato.
            # Se fosse di un altro utente, bisognerebbe passare per il sistema di "Richiesta/Proposta".
            destinatario_obj = get_object_or_404(Personaggio, pk=target_id, proprietario=request.user)

        try:
            oggetto = GestioneCraftingService.completa_forgiatura(
                forg_id, 
                personaggio, 
                slot_scelto=slot_scelto,
                destinatario_diretto=destinatario_obj # <--- PASSA AL SERVICE
            )
            return Response({"status": "completed", "oggetto_id": oggetto.id}, status=200)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def coda_forgiatura(self, request):
        # ... (recupero pg come prima) ...
        char_id = request.query_params.get('char_id')
        if request.user.is_staff: pg = get_object_or_404(Personaggio, id=char_id)
        else: pg = get_object_or_404(Personaggio, id=char_id, proprietario=request.user)

        coda = ForgiaturaInCorso.objects.filter(
            Q(personaggio=pg) | Q(destinatario_finale=pg)
        ).select_related('infusione__aura_richiesta', 'personaggio', 'destinatario_finale')
        
        data = []
        now = timezone.now()
        for task in coda:
            # ... (calcolo info_extra come prima) ...
            info_extra = ""
            if task.destinatario_finale and task.destinatario_finale != pg:
                 info_extra = f"Per: {task.destinatario_finale.nome}"
            elif task.personaggio != pg:
                 info_extra = f"Artigiano: {task.personaggio.nome}"

            data.append({
                "id": task.id,
                "infusione_id": task.infusione.id, # <--- AGGIUNTO QUESTO CAMPO
                "infusione_nome": task.infusione.nome,
                "infusione_slot_permessi": task.infusione.slot_corpo_permessi,
                "data_inizio": task.data_inizio,
                "data_fine": task.data_fine_prevista,
                "secondi_rimanenti": max(0, (task.data_fine_prevista - now).total_seconds()),
                "is_pronta": task.is_pronta,
                "info_extra": info_extra,
                "can_collect": (task.is_pronta and (
                    (task.destinatario_finale and task.destinatario_finale.id == pg.id) or 
                    (not task.destinatario_finale and task.personaggio.id == pg.id)
                ))
            })
        return Response(data)


    
class AssemblyValidationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Controlla se l'assemblaggio è possibile tra Host e Component.
        Restituisce struttura compatibile con ItemAssemblyModal.jsx.
        """
        char_id = request.data.get('char_id')
        host_id = request.data.get('host_id')
        mod_id = request.data.get('mod_id')

        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        host = get_object_or_404(Oggetto, pk=host_id)
        mod = get_object_or_404(Oggetto, pk=mod_id)

        # 1. Verifica Hardware (Compatibilità Fisica/Regole Classe)
        # Questo controllo verifica se l'oggetto "entra" fisicamente e rispetta la classe
        is_hardware_ok, hw_msg = GestioneOggettiService.verifica_compatibilita_hardware(host, mod)

        # 2. Verifica Competenze (Skill Personaggio)
        # Questo controllo verifica se il personaggio ha le capacità (Aura/Stats)
        can_do_self, skill_msg = GestioneOggettiService.verifica_competenza_assemblaggio(pg, host, mod)

        # Costruzione Risposta per il Frontend
        # 'is_valid': True se l'operazione è tecnicamente possibile (Hardware OK)
        # 'can_do_self': True se l'utente corrente può farla (Skill OK)
        response_data = {
            "is_valid": is_hardware_ok,          
            "error_message": None,               
            "warning": None,                     
            
            "can_do_self": can_do_self,          
            "requires_skill": not can_do_self,   
            
            "can_use_academy": is_hardware_ok,   
            
            "host_name": host.nome,
            "mod_name": mod.nome,
            "required_skill_name": "Aura Tecnologica" if host.is_tecnologico else "Aura Mondana - Assemblatore"
        }

        if not is_hardware_ok:
            # Se l'hardware non è compatibile, è un errore bloccante
            response_data["error_message"] = hw_msg
        elif not can_do_self:
            # Se manca solo la skill, è un warning (puoi chiedere a un tecnico)
            response_data["warning"] = skill_msg

        return Response(response_data)

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
    
def post(self, request):
        """
        Controlla se l'assemblaggio è possibile tra Host e Component.
        Restituisce struttura compatibile con ItemAssemblyModal.jsx.
        """
        char_id = request.data.get('char_id')
        host_id = request.data.get('host_id')
        mod_id = request.data.get('mod_id')

        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        host = get_object_or_404(Oggetto, pk=host_id)
        mod = get_object_or_404(Oggetto, pk=mod_id)

        # 1. Verifica Hardware (Compatibilità Fisica/Regole Classe)
        is_hardware_ok, hw_msg = GestioneOggettiService.verifica_compatibilita_hardware(host, mod)

        # 2. Verifica Competenze (Skill Personaggio)
        # Nota: questo controllo include anche l'hardware internamente, ma lo separiamo per chiarezza UI
        can_do_self, skill_msg = GestioneOggettiService.verifica_competenza_assemblaggio(pg, host, mod)

        # Costruzione Risposta per il Frontend
        response_data = {
            "is_valid": is_hardware_ok,          # Se False, l'oggetto non entra proprio (blocca tutto)
            "error_message": None,               # Messaggio di errore bloccante
            "warning": None,                     # Warning non bloccante
            
            "can_do_self": can_do_self,          # Se True, mostra tasto "Fai da te"
            "requires_skill": not can_do_self,   # Se True, mostra info skill mancante
            
            "can_use_academy": is_hardware_ok,   # L'accademia può farlo se l'hardware è compatibile
            
            "host_name": host.nome,
            "mod_name": mod.nome,
            "required_skill_name": "Aura Tecnologica" if host.is_tecnologico else "Aura Mondana - Assemblatore"
        }

        if not is_hardware_ok:
            response_data["error_message"] = hw_msg
        elif not can_do_self:
            # Se hardware ok ma mancano skill, non è un errore bloccante (puoi chiedere a tecnico)
            # Ma mettiamo un warning o info skill
            response_data["warning"] = skill_msg

        return Response(response_data)

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
        # 1. Recupero Parametri Grezzi dal Frontend
        # Nota: Il frontend invia il target in 'committente_id' e se stesso in 'artigiano_nome'
        target_id_param = request.data.get('committente_id') 
        self_name_param = request.data.get('artigiano_nome')
        
        offerta = int(request.data.get('offerta', 0))
        tipo_op = request.data.get('tipo_operazione', 'INST')
        
        host_id = request.data.get('host_id')
        comp_id = request.data.get('comp_id')
        infusione_id = request.data.get('infusione_id')
        forgia_id = request.data.get('forgiatura_id')
        slot_dest = request.data.get('slot_destinazione')

        # 2. Risoluzione Oggetti Personaggio
        # Cerchiamo di capire chi sono i due attori senza assegnare ancora i ruoli DB
        pg_target = Personaggio.objects.filter(pk=target_id_param).first()
        pg_self = Personaggio.objects.filter(nome__iexact=self_name_param).first()

        if not pg_target or not pg_self:
             return Response({"error": "Personaggi non trovati."}, status=404)

        # 3. Assegnazione Ruoli DB e Logica Messaggio
        db_committente = None
        db_artigiano = None
        messaggio_testo = ""
        destinatario_msg = None
        
        # Variabili Oggetto
        host = None; comp = None; infusione = None; forgiatura_obj = None

        # --- CASO 3: INNESTO / MUTAZIONE (Logica Invertita) ---
        if tipo_op == 'GRAF':
            if not forgia_id or not slot_dest: return Response({"error": "Dati mancanti."}, status=400)
            forgiatura_obj = get_object_or_404(ForgiaturaInCorso, pk=forgia_id)
            if not forgiatura_obj.is_pronta: return Response({"error": "Oggetto non pronto."}, status=400)
            
            # SPECIFICA UTENTE: 
            # COMMITTENTE = Medico (Chi propone/Chi è loggato) -> pg_self
            # ARTIGIANO = Paziente (Chi riceve/Chi paga) -> pg_target
            
            db_committente = pg_self   # Il Dottore (Tu)
            db_artigiano = pg_target   # Il Paziente (Lui)
            
            messaggio_testo = f"Il Dr. {pg_self.nome} propone l'installazione di {forgiatura_obj.infusione.nome} su {slot_dest}. Costo: {offerta} CR."
            
            # Il messaggio va al Paziente, che abbiamo mappato su 'artigiano'
            destinatario_msg = db_artigiano 
            
            # Linkiamo infusione
            infusione = forgiatura_obj.infusione

        # --- CASO 1 & 2: MONTAGGIO / FORGIATURA STANDARD ---
        else:
            # SPECIFICA STANDARD:
            # COMMITTENTE = Chi chiede (Chi è loggato/Cliente) -> pg_self? 
            # No, il frontend in standard manda: committente_id=Me, artigiano_nome=Lui.
            # Quindi pg_target è ME (Cliente), pg_self è LUI (Artigiano).
            # Aspetta, controlliamo cosa manda il frontend in standard.
            # Se il frontend standard manda committente_id = ID_CLIENTE e artigiano_nome = NOME_ARTIGIANO...
            
            # Verifichiamo la proprietà per sicurezza
            if request.user == pg_target.proprietario:
                # Caso classico: Io (Target ID) chiedo a Lui (Name)
                db_committente = pg_target
                db_artigiano = pg_self
            elif request.user == pg_self.proprietario:
                # Caso inverso: Io (Name) chiedo a Lui (Target ID)
                db_committente = pg_self
                db_artigiano = pg_target
            
            if tipo_op == 'FORG':
                infusione = get_object_or_404(Infusione, pk=infusione_id)
                messaggio_testo = f"{db_committente.nome} richiede forgiatura: {infusione.nome}. Offerta: {offerta} CR."
            else:
                host = get_object_or_404(Oggetto, pk=host_id)
                comp = get_object_or_404(Oggetto, pk=comp_id)
                v = "rimuovere" if tipo_op == 'RIMO' else "assemblare"
                messaggio_testo = f"{db_committente.nome} chiede di {v} {comp.nome} su {host.nome}. Offerta: {offerta} CR."

            # Il messaggio va all'artigiano (chi esegue il lavoro)
            destinatario_msg = db_artigiano

        # 4. Salvataggio
        richiesta = RichiestaAssemblaggio.objects.create(
            committente=db_committente,
            artigiano=db_artigiano,
            oggetto_host=host,
            componente=comp,
            infusione=infusione,
            forgiatura_target=forgiatura_obj,
            slot_destinazione=slot_dest,
            offerta_crediti=offerta,
            tipo_operazione=tipo_op
        )
        
        # 5. Invio Messaggio
        Messaggio.objects.create(
            mittente=request.user,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            destinatario_personaggio=destinatario_msg,
            titolo="Proposta Operazione" if tipo_op == 'GRAF' else "Richiesta Lavoro",
            testo=messaggio_testo
        )

        return Response({"status": "created", "id": richiesta.id}, status=201)
    
    @action(detail=True, methods=['post'])
    def accetta(self, request, pk=None):
        richiesta = self.get_object()
        
        # Rimuoviamo i controlli rigidi qui e lasciamo fare al Service,
        # oppure facciamo un controllo preliminare corretto.
        
        user = request.user
        is_owner_artigiano = richiesta.artigiano.proprietario == user
        is_owner_committente = richiesta.committente.proprietario == user
        is_admin = user.is_staff or user.is_superuser
        
        # Controllo permessi preliminare (coerente col service)
        if richiesta.tipo_operazione == 'GRAF':
            if not is_owner_committente and not is_admin:
                return Response({"error": "Solo il paziente può accettare questa proposta."}, status=403)
        else:
            if not is_owner_artigiano and not is_admin:
                return Response({"error": "Solo l'artigiano può accettare questo lavoro."}, status=403)
            
        try:
            # Passiamo l'utente che sta eseguendo l'azione
            GestioneOggettiService.elabora_richiesta_assemblaggio(richiesta.id, request.user)
            return Response({"status": "success", "message": "Operazione completata con successo!"})
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
                # --- FORGIATURA COOPERATIVA ---
                inf = Infusione.objects.get(pk=infusione_id)
                
                # Il richiedente DEVE avere l'aura principale per poter chiedere aiuto
                if requester.get_valore_aura_effettivo(inf.aura_richiesta) < inf.livello:
                    # Se manca la base, nessuno può aiutarlo
                    return Response([])

                for p in candidati:
                    # Verifica se p (Aiutante) completa requester (Forgiatore)
                    ok, _ = GestioneCraftingService.verifica_competenza_forgiatura(
                        forgiatore=requester, 
                        infusione=inf, 
                        aiutante=p
                    )
                    if ok: capaci.append({"id": p.id, "nome": p.nome})
            
            else:
                # --- ASSEMBLAGGIO (Operatore Singolo) ---
                host = Oggetto.objects.get(pk=host_id)
                mod = Oggetto.objects.get(pk=mod_id)
                for p in candidati:
                    ok, _ = GestioneOggettiService.verifica_competenza_assemblaggio(p, host, mod)
                    if ok: capaci.append({"id": p.id, "nome": p.nome})
            
            return Response(capaci)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
class ForgingValidationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Controlla se il PG ha i requisiti per l'infusione."""
        char_id = request.data.get('char_id')
        inf_id = request.data.get('infusione_id')
        
        try:
            pg = Personaggio.objects.get(pk=char_id)
            inf = Infusione.objects.get(pk=inf_id)
            
            can_do, msg = GestioneCraftingService.verifica_competenza_forgiatura(pg, inf)
            
            return Response({
                "can_forge": can_do,
                "reason": msg if not can_do else "OK"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
class ClasseOggettoListView(generics.ListAPIView):
    """
    API per ottenere la lista delle classi oggetto e le loro regole di compatibilità.
    """
    queryset = ClasseOggetto.objects.all().order_by('nome')
    serializer_class = ClasseOggettoSerializer
    permission_classes = [IsAuthenticated]
    

class GameActionsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def modifica_stat_temp(self, request):
        char_id = request.data.get('char_id')
        stat_sigla = request.data.get('stat_sigla')
        mode = request.data.get('mode')
        # Leggiamo il max_value passato dal frontend (fondamentale per le zone del corpo)
        max_val_param = request.data.get('max_value') 
        
        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        
        # 1. Determina il Valore Massimo
        val_max = 0
        if max_val_param is not None:
            # Se il frontend ci dice qual è il massimo (es. PV totali), usiamo quello
            val_max = int(max_val_param)
        else:
            # Altrimenti cerchiamo nel DB. 
            # Gestiamo il caso di sigle composte (es. PV_TR -> cerca PV)
            base_sigla = stat_sigla.split('_')[0] 
            val_max = pg.get_valore_statistica(base_sigla)
            # Se fallisce anche questo, fallback di sicurezza
            if val_max == 0 and stat_sigla not in ['PG', 'PA', 'PV']: 
                val_max = 999 
        
        # 2. Inizializza la statistica nel JSON se non esiste
        # Se è la prima volta che colpiamo "Tronco", lo settiamo al massimo
        if stat_sigla not in pg.statistiche_temporanee:
            pg.statistiche_temporanee[stat_sigla] = val_max

        current = int(pg.statistiche_temporanee[stat_sigla])
        
        # 3. Applica la logica
        nuovo_valore = current
        
        if mode == 'consuma':
            nuovo_valore = max(0, current - 1)
        elif mode == 'add':  # <--- MANCAVA QUESTO!
            nuovo_valore = min(val_max, current + 1)
        elif mode == 'reset':
            nuovo_valore = val_max
            
        # 4. Salva nel DB
        pg.statistiche_temporanee[stat_sigla] = nuovo_valore
        pg.save(update_fields=['statistiche_temporanee']) 
        
        return Response({
            'status': 'ok',
            'stat_sigla': stat_sigla,
            'current': nuovo_valore, 
            'max': val_max,
            # Ritorniamo tutto l'oggetto aggiornato per sicurezza
            'statistiche_temporanee': pg.statistiche_temporanee 
        })

    @action(detail=False, methods=['post'])
    def usa_oggetto(self, request):
        """
        Usa una carica di un oggetto. Se ha durata, imposta la scadenza.
        """
        obj_id = request.data.get('oggetto_id')
        char_id = request.data.get('char_id') # Opzionale, per verifica owner
        
        obj = get_object_or_404(Oggetto, pk=obj_id)
        
        # Verifica che l'oggetto appartenga a un PG dell'utente (sicurezza base)
        if obj.inventario_corrente:
             # Controllo blando: se l'inventario è un PG, deve essere dell'utente
             if hasattr(obj.inventario_corrente, 'personaggio_ptr'):
                 if obj.inventario_corrente.personaggio_ptr.proprietario != request.user:
                     return Response({'error': 'Oggetto non tuo'}, status=403)

        if obj.cariche_attuali <= 0:
            return Response({'error': 'Oggetto scarico'}, status=400)
            
        # Consuma carica
        obj.cariche_attuali -= 1
        
        # Gestione Timer
        durata = 0
        if obj.infusione_generatrice and obj.infusione_generatrice.durata_attivazione > 0:
            durata = obj.infusione_generatrice.durata_attivazione
            obj.data_fine_attivazione = timezone.now() + timedelta(seconds=durata)
        
        obj.save()
        
        # Serializziamo per tornare i dati aggiornati al frontend
        serializer = OggettoSerializer(obj)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def ricarica_oggetto(self, request):
        """
        Ricarica le cariche di un oggetto pagando i crediti.
        """
        obj_id = request.data.get('oggetto_id')
        char_id = request.data.get('char_id')
        
        obj = get_object_or_404(Oggetto, pk=obj_id)
        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        
        infusione = obj.infusione_generatrice
        if not infusione or not infusione.statistica_cariche:
            return Response({'error': 'Oggetto non ricaricabile'}, status=400)
            
        # Calcolo costo
        max_cariche = infusione.statistica_cariche.valore_base_predefinito
        mancanti = max_cariche - obj.cariche_attuali
        
        if mancanti <= 0:
            return Response({'message': 'Già carico'}, status=200)
            
        costo = mancanti * infusione.costo_ricarica_crediti
        
        if pg.crediti < costo:
             return Response({'error': f'Crediti insufficienti. Servono {costo} CR.'}, status=400)
             
        with transaction.atomic():
            pg.modifica_crediti(-costo, f"Ricarica {obj.nome}")
            obj.cariche_attuali = max_cariche
            # Se ricarichi, il timer si resetta? Di solito no, o si spegne.
            # Per ora lasciamo il timer inalterato o lo spegniamo. Spegniamolo per coerenza (ricarica = reset).
            obj.data_fine_attivazione = None 
            obj.save()
            
        serializer = OggettoSerializer(obj)
        return Response(serializer.data)
    
class ActiveTimersViewSet(viewsets.ReadOnlyModelViewSet):
    """API per recuperare i timer attualmente attivi al caricamento dell'app"""
    serializer_class = StatoTimerSerializer

    def get_queryset(self):
        # Restituisce solo i timer la cui data di fine è nel futuro
        return StatoTimerAttivo.objects.filter(data_fine__gt=timezone.now())
    
class StatisticaViewSet(viewsets.ReadOnlyModelViewSet):
    """Visualizza l'elenco delle statistiche tecniche disponibili"""
    queryset = Statistica.objects.all()
    serializer_class = StatisticaSerializer
    # Le statistiche sono pubbliche in lettura per gli utenti autenticati
    permission_classes = [IsAuthenticated]
    
class TipologiaPersonaggioViewSet(viewsets.ReadOnlyModelViewSet):
    """Visualizza l'elenco delle tipologie di personaggi disponibili"""
    queryset = TipologiaPersonaggio.objects.all()
    serializer_class = TipologiaPersonaggioSerializer
    permission_classes = [IsAuthenticated]
    
# Aggiungi in personaggi/views.py

class PersonaggioManageViewSet(viewsets.ModelViewSet):
    """
    ViewSet per la gestione CRUD dei personaggi.
    Paginazione disabilitata per compatibilità con il frontend attuale.
    """
    serializer_class = PersonaggioManageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # <--- AGGIUNGI QUESTA RIGA: Disabilita la paginazione

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Personaggio.objects.all().select_related('tipologia', 'proprietario').order_by('nome')
        return Personaggio.objects.filter(proprietario=user).select_related('tipologia').order_by('nome')

    def perform_create(self, serializer):
        serializer.save(proprietario=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def add_resources(self, request, pk=None):
        personaggio = self.get_object()
        tipo = request.data.get('tipo')
        reason = request.data.get('reason', 'Intervento Staff')
        try:
            amount = int(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response({"error": "Importo non valido"}, status=400)

        if amount == 0:
            return Response({"error": "L'importo non può essere zero"}, status=400)

        if tipo == 'crediti':
            personaggio.modifica_crediti(amount, reason)
            val = personaggio.crediti
        elif tipo == 'pc':
            personaggio.modifica_pc(amount, reason)
            val = personaggio.punti_caratteristica
        else:
            return Response({"error": "Tipo risorsa non valido"}, status=400)
            
        return Response({"status": "success", "new_val": val, "msg": "Risorse aggiornate"})
    
    # OAUTH2 SSO per OSSN
    
class UserMeView(APIView):
# Questa classe garantisce che solo chi ha un token valido possa accedere
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = SSOUserSerializer(request.user)
        return Response(serializer.data)
    
    
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            # 1. FORZA is_active=False
            user = serializer.save(is_active=False)
            
            # 2. CREA MESSAGGIO PER LO STAFF
            # Testo con i tag speciali per i bottoni di attivazione ed eliminazione
            testo_msg = (
                f"Nuova registrazione:<br>"
                f"Utente: <b>{user.username}</b><br>"
                f"Email: {user.email}<br>"
                f"Nome: {user.first_name} {user.last_name}<br><br>"
                f"Azioni disponibili:<br>"
                f"[ACTIVATE_USER:{user.id}] [DELETE_USER:{user.id}]" 
            )

            # Crea il messaggio nel DB
            Messaggio.objects.create(
                mittente=None, # Messaggio di sistema
                destinatario_personaggio=None, # Nessun destinatario specifico
                titolo=f"Nuovo Utente: {user.username}",
                testo=testo_msg,
                tipo_messaggio='STAFF',
                is_staff_message=True # <--- Questo lo rende visibile nella Tab Staff
            )

            return Response(
                {"message": "Registrazione completata. In attesa di attivazione."}, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActivateUserView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser] # Solo Staff

    def post(self, request, user_id):
        try:
            user_to_activate = User.objects.get(pk=user_id)
            user_to_activate.is_active = True
            user_to_activate.save()
            return Response({"message": f"Utente {user_to_activate.username} attivato con successo."})
        except User.DoesNotExist:
            return Response({"error": "Utente non trovato."}, status=status.HTTP_404_NOT_FOUND)

class DeleteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser] # Solo Staff

    def delete(self, request, user_id):
        try:
            user_to_delete = User.objects.get(pk=user_id)
            username = user_to_delete.username
            user_to_delete.delete()
            return Response({"message": f"Utente {username} eliminato con successo."})
        except User.DoesNotExist:
            return Response({"error": "Utente non trovato."}, status=status.HTTP_404_NOT_FOUND)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password aggiornata con successo."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class StaffMessageListView(generics.ListAPIView):
    serializer_class = MessaggioSerializer
    permission_classes = [permissions.IsAdminUser] # Solo Staff/Admin

    def get_queryset(self):
        # Restituisce messaggi per lo staff, escludendo quelli cancellati
        return Messaggio.objects.filter(
            is_staff_message=True, 
            cancellato_staff=False
        ).order_by('-data_invio')

class StaffMessageMarkReadView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request, message_id):
        try:
            messaggio = Messaggio.objects.get(pk=message_id, is_staff_message=True)
            messaggio.letto_staff = True
            messaggio.save()
            return Response({"message": "Messaggio marcato come letto"})
        except Messaggio.DoesNotExist:
            return Response({"error": "Messaggio non trovato"}, status=status.HTTP_404_NOT_FOUND)

class StaffMessageDeleteView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request, message_id):
        try:
            messaggio = Messaggio.objects.get(pk=message_id, is_staff_message=True)
            messaggio.cancellato_staff = True
            messaggio.save()
            return Response({"message": "Messaggio eliminato"})
        except Messaggio.DoesNotExist:
            return Response({"error": "Messaggio non trovato"}, status=status.HTTP_404_NOT_FOUND)

class AssociaQrAVistaView(APIView):
    """
    Associa un QR code a un elemento derivato da A_vista 
    (Tessitura, Infusione, Cerimoniale, Oggetto, OggettoBase, Inventario, Manifesto)
    """
    permission_classes = [permissions.IsAdminUser]  # Solo Staff
    
    def post(self, request, a_vista_id):
        qr_id = request.data.get('qr_id')
        force = request.data.get('force', False)
        
        if not qr_id:
            return Response({'error': 'qr_id è richiesto'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verifica che l'elemento A_vista esista
            a_vista = A_vista.objects.get(pk=a_vista_id)
        except A_vista.DoesNotExist:
            return Response({'error': 'Elemento non trovato'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            qr = QrCode.objects.get(id=qr_id)
            
            # Se il QR è già associato e force=False, restituisci errore con dettagli
            if qr.vista and qr.vista != a_vista and not force:
                # Determina il tipo di elemento associato
                elemento_associato = None
                tipo_elemento = "Elemento"
                
                # Cerca in tutti i modelli che ereditano da A_vista
                if hasattr(qr.vista, 'tessitura'):
                    elemento_associato = qr.vista.tessitura
                    tipo_elemento = "Tessitura"
                elif hasattr(qr.vista, 'infusione'):
                    elemento_associato = qr.vista.infusione
                    tipo_elemento = "Infusione"
                elif hasattr(qr.vista, 'cerimoniale'):
                    elemento_associato = qr.vista.cerimoniale
                    tipo_elemento = "Cerimoniale"
                elif hasattr(qr.vista, 'oggetto'):
                    elemento_associato = qr.vista.oggetto
                    tipo_elemento = "Oggetto"
                elif hasattr(qr.vista, 'oggettobase'):
                    elemento_associato = qr.vista.oggettobase
                    tipo_elemento = "Oggetto Base"
                elif hasattr(qr.vista, 'inventario'):
                    elemento_associato = qr.vista.inventario
                    tipo_elemento = "Inventario"
                elif hasattr(qr.vista, 'manifesto'):
                    elemento_associato = qr.vista.manifesto
                    tipo_elemento = "Manifesto"
                
                nome_associato = elemento_associato.nome if elemento_associato else "Sconosciuto"
                
                return Response({
                    'error': 'QR già associato',
                    'already_associated': True,
                    'message': f'Questo QR è già associato a: {nome_associato} ({tipo_elemento}). Confermare per disassociarlo?'
                }, status=status.HTTP_409_CONFLICT)
            
            # Associa il QR all'elemento A_vista
            qr.vista = a_vista
            qr.save()
            
            return Response({
                'status': 'success',
                'message': 'QR associato con successo',
                'qr_id': qr.id,
                'a_vista_id': a_vista.id
            })
            
        except QrCode.DoesNotExist:
            return Response({'error': 'QR Code non trovato'}, status=status.HTTP_404_NOT_FOUND)