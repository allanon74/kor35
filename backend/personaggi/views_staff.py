from rest_framework import viewsets, permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from gestione_plot.permissions import IsStaffOrMaster
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q, Sum, Prefetch, OuterRef, Subquery
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import re

from .models import (
    PropostaTecnica, Personaggio, Messaggio, Punteggio,
    Infusione, Tessitura, Cerimoniale, Mattone,
    PersonaggioInfusione, PersonaggioTessitura, PersonaggioCerimoniale,
    QrCode, Oggetto, OggettoBase, ClasseOggetto, Abilita, Inventario, Manifesto, Nodo, NodoRewardConfig, InnescoTimer,
    A_vista, Attivata, MinigiocoQrConfig, MinigiocoBibliotecaImmagine,
    STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_APPROVATA, STATO_PROPOSTA_IN_VALUTAZIONE,
    TIPO_PROPOSTA_INFUSIONE, TIPO_PROPOSTA_TESSITURA, TIPO_PROPOSTA_CERIMONIALE, Tier, 
    abilita_tier,
    TipologiaEffetto, EffettoCasuale,
    Era, Prefettura, Regione, Korp, Carriera, TipoCarriera, Carica,
    PersonaggioCarrieraMembership, CarrieraTierSblocco,
    Dichiarazione,
    Campagna, CampagnaFeaturePolicy,
    RegolaTransazioneCategoria,
    PersonaggioLog,
    FEATURE_ABILITA, FEATURE_TESSITURE, FEATURE_INFUSIONI, FEATURE_OGGETTI_BASE, FEATURE_CERIMONIALI,
    FEATURE_MODE_SHARED,
)

from decimal import Decimal

from .acquisto_costi import calcola_costo_creazione_proposta
from .qr_logic import annotate_staff_avista_qr
from .services import GestioneCraftingService
from .formula_builder import (
    FORMULA_BUILDER_SCHEMA,
    build_formula_template,
    build_stats_by_selection,
    render_formula_preview,
)

from .serializers import (
    InfusioneFullEditorSerializer,
    OggettoBaseFullEditorSerializer,
    OggettoFullEditorSerializer, 
    TessituraFullEditorSerializer, 
    CerimonialeFullEditorSerializer,
    OggettoSerializer,
    OggettoBaseSerializer,
    ClasseOggettoSerializer,
    InfusioneSerializer,
    TessituraSerializer,
    CerimonialeSerializer,
    InfusioneStaffListSerializer,
    TessituraStaffListSerializer,
    CerimonialeStaffListSerializer,
    PropostaTecnicaSerializer,
    AbilitaFullEditorSerializer,
    AbilitaStaffListSerializer,
    TierStaffSerializer,
    AbilitaSimpleSerializer,
    InventarioStaffSerializer,
    TipologiaEffettoStaffSerializer, EffettoCasualeStaffSerializer,
    EraStaffSerializer, PrefetturaStaffSerializer, RegioneStaffSerializer,
    TipoCarrieraStaffSerializer, CarrieraStaffSerializer, CaricaStaffSerializer,
    PersonaggioCarrieraMembershipStaffSerializer,
    DichiarazioneStaffSerializer,
    ManifestoStaffSerializer,
    NodoStaffSerializer,
    NodoRewardConfigStaffSerializer,
    InnescoTimerStaffSerializer,
    A_vistaSerializer,
    AttivataSerializer,
    PersonaggioPublicSerializer,
    PersonaggioEliminatoStaffSerializer,
    PersonaggioStaffListSerializer,
    PersonaggioStaffDetailSerializer,
    RegolaTransazioneCategoriaStaffSerializer,
    CreditoMovimentoSerializer,
    PuntiCaratteristicaMovimentoListSerializer,
)


class AbilitaStaffPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


def _get_default_campaign():
    return Campagna.objects.filter(slug="kor35").first() or Campagna.objects.filter(is_default=True).first()


def _get_active_campaign(request):
    slug = (request.headers.get("X-Campagna") or request.query_params.get("campagna") or "kor35").strip().lower()
    campagna = Campagna.objects.filter(slug=slug, attiva=True).first()
    return campagna or _get_default_campaign()


def _feature_mode_for_campaign(campagna, feature_key):
    if not campagna or campagna.slug == "kor35":
        return FEATURE_MODE_SHARED
    row = CampagnaFeaturePolicy.objects.filter(campagna=campagna, feature_key=feature_key).first()
    return row.mode if row else FEATURE_MODE_SHARED


def _campaign_feature_filter(request, qs, feature_key):
    active = _get_active_campaign(request)
    base = _get_default_campaign()
    if not active:
        return qs
    mode = _feature_mode_for_campaign(active, feature_key)
    if mode == FEATURE_MODE_SHARED and base:
        return qs.filter(Q(campagna=active) | Q(campagna=base))
    return qs.filter(campagna=active)


def _staff_qr_inspect_payload(qr, request):
    """
    Risolve il contenuto del QR come in QrCodeDetailView: `vista` punta sempre ad A_vista,
    ma l'oggetto reale è una sottoclasse (Nodo, Manifesto, …); qui non si attiva gameplay.
    """
    ctx = {"request": request}
    base = {"id": qr.id, "testo_raw": qr.testo}

    minigioco = getattr(qr, "configurazione_minigioco", None)
    if minigioco is not None:
        req = request
        img_url = None
        if minigioco.immagine:
            try:
                img_url = req.build_absolute_uri(minigioco.immagine.url) if req else minigioco.immagine.url
            except Exception:
                img_url = None
        base["minigioco_config"] = {
            "sezione_attiva": minigioco.sezione_attiva,
            "attivo": minigioco.attivo,
            "tipi_abilitati": minigioco.tipi_abilitati or [],
            "difficolta": minigioco.difficolta,
            "requisiti_attivazione": minigioco.requisiti_attivazione or [],
            "messaggio_accesso_negato": minigioco.messaggio_accesso_negato or "",
            "esclusioni_minigioco": minigioco.esclusioni_minigioco or [],
            "regole_difficolta": minigioco.regole_difficolta or [],
            "messaggio_pre": minigioco.messaggio_pre,
            "messaggio_vittoria": minigioco.messaggio_vittoria,
            "timer_secondi": minigioco.timer_secondi,
            "timer_scadenza_azione": minigioco.timer_scadenza_azione,
            "immagine_url": img_url,
        }

    timer = getattr(qr, "configurazione_timer", None)
    if timer is not None:
        tip = getattr(timer.tipologia, "nome", "?")
        return {
            **base,
            "tipo_contenuto": "timer_legacy",
            "nome_contenuto": f"Timer {tip} ({timer.durata_secondi}s)",
            "elemento_id": str(qr.id),
            "dati": {
                "tipologia_timer_id": str(timer.tipologia_id),
                "tipologia_nome": tip,
                "durata_secondi": timer.durata_secondi,
                "ultima_attivazione": timer.ultima_attivazione.isoformat()
                if timer.ultima_attivazione
                else None,
            },
        }

    vista_obj = qr.vista
    if not vista_obj:
        return {**base, "tipo_contenuto": "Vuoto", "nome_contenuto": "Nessuno", "elemento_id": None, "dati": None}

    pk = vista_obj.pk

    inn = InnescoTimer.objects.filter(pk=pk).first()
    if inn:
        return {
            **base,
            "tipo_contenuto": "innesco_timer",
            "nome_contenuto": inn.nome,
            "elemento_id": str(inn.id),
            "dati": InnescoTimerStaffSerializer(inn, context=ctx).data,
        }

    nodo = Nodo.objects.filter(pk=pk).first()
    if nodo:
        return {
            **base,
            "tipo_contenuto": "nodo",
            "nome_contenuto": nodo.nome,
            "elemento_id": str(nodo.id),
            "dati": NodoStaffSerializer(nodo, context=ctx).data,
        }

    pg = Personaggio.objects.filter(inventario_ptr_id=pk).select_related("tipologia").first()
    if pg:
        return {
            **base,
            "tipo_contenuto": "personaggio",
            "nome_contenuto": pg.nome,
            "elemento_id": str(pg.id),
            "dati": PersonaggioPublicSerializer(pg, context=ctx).data,
        }

    og = Oggetto.objects.filter(pk=pk).first()
    if og:
        return {
            **base,
            "tipo_contenuto": "oggetto",
            "nome_contenuto": og.nome,
            "elemento_id": str(og.id),
            "dati": OggettoFullEditorSerializer(og, context=ctx).data,
        }

    att = Attivata.objects.filter(pk=pk).first()
    if att:
        return {
            **base,
            "tipo_contenuto": "attivata",
            "nome_contenuto": att.nome,
            "elemento_id": str(att.id),
            "dati": AttivataSerializer(att, context=ctx).data,
        }

    inf = Infusione.objects.filter(pk=pk).first()
    if inf:
        return {
            **base,
            "tipo_contenuto": "infusione",
            "nome_contenuto": inf.nome,
            "elemento_id": str(inf.id),
            "dati": InfusioneSerializer(inf, context=ctx).data,
        }

    tes = Tessitura.objects.filter(pk=pk).first()
    if tes:
        return {
            **base,
            "tipo_contenuto": "tessitura",
            "nome_contenuto": tes.nome,
            "elemento_id": str(tes.id),
            "dati": TessituraSerializer(tes, context=ctx).data,
        }

    cer = Cerimoniale.objects.filter(pk=pk).first()
    if cer:
        return {
            **base,
            "tipo_contenuto": "cerimoniale",
            "nome_contenuto": cer.nome,
            "elemento_id": str(cer.id),
            "dati": CerimonialeSerializer(cer, context=ctx).data,
        }

    man = Manifesto.objects.filter(pk=pk).first()
    if man:
        return {
            **base,
            "tipo_contenuto": "manifesto",
            "nome_contenuto": man.nome,
            "elemento_id": str(man.id),
            "dati": ManifestoStaffSerializer(man, context=ctx).data,
        }

    inv = Inventario.objects.filter(pk=pk).first()
    if inv and not Personaggio.objects.filter(inventario_ptr_id=pk).exists():
        return {
            **base,
            "tipo_contenuto": "inventario",
            "nome_contenuto": inv.nome,
            "elemento_id": str(inv.id),
            "dati": InventarioStaffSerializer(inv, context=ctx).data,
        }

    return {
        **base,
        "tipo_contenuto": "a_vista",
        "nome_contenuto": vista_obj.nome,
        "elemento_id": str(vista_obj.id),
        "dati": A_vistaSerializer(vista_obj, context=ctx).data,
        "nota": "Record A_vista senza sottoclasse nota (legacy o modello non mappato in ispezione).",
    }


class QrInspectorView(APIView):
    """
    Strumento STAFF: Legge un QR e dice cos'è senza attivare nulla.
    """
    permission_classes = [IsStaffOrMaster]

    def get(self, request, qr_id):
        try:
            qr = QrCode.objects.select_related(
                "vista",
                "configurazione_timer",
                "configurazione_timer__tipologia",
                "configurazione_minigioco",
            ).get(id=qr_id)
            return Response(_staff_qr_inspect_payload(qr, request))
        except QrCode.DoesNotExist:
            return Response({'error': 'Non trovato'}, status=404)


class StaffQrInventoryScanView(APIView):
    """
    Inventario QR lato staff.
    - modalita "totale": opzionalmente azzera tutto, poi marca il QR scansionato come presente.
    - modalita "additiva": lascia invariati i non scansionati, aggiorna solo il QR corrente.
    """

    permission_classes = [IsStaffOrMaster]
    HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def post(self, request):
        qr_id = str(request.data.get("qr_id") or "").strip()
        modalita = str(request.data.get("modalita") or "additiva").strip().lower()
        reset_before_scan = bool(request.data.get("reset_before_scan", False))
        inventario_colore_codice = request.data.get("inventario_colore_codice")
        inventario_colore_sfondo = request.data.get("inventario_colore_sfondo")

        if not qr_id:
            return Response({"error": "qr_id obbligatorio"}, status=status.HTTP_400_BAD_REQUEST)
        if modalita not in {"totale", "additiva"}:
            return Response(
                {"error": "modalita non valida: usare 'totale' o 'additiva'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if modalita == "totale" and reset_before_scan:
                QrCode.objects.all().update(
                    inventario_presente=False,
                    inventario_colore_codice="",
                    inventario_colore_sfondo="",
                )

            try:
                qr = QrCode.objects.select_for_update().get(id=qr_id)
            except QrCode.DoesNotExist:
                return Response(
                    {"error": "QR sconosciuto", "qr_sconosciuto": True, "qr_id": qr_id},
                    status=status.HTTP_404_NOT_FOUND,
                )

            codice = str(inventario_colore_codice or "").strip().upper()
            sfondo = str(inventario_colore_sfondo or "").strip().upper()
            if not self.HEX_RE.match(codice):
                codice = "#FFFFFF"
            if not self.HEX_RE.match(sfondo):
                sfondo = "#000000"

            qr.inventario_presente = True
            qr.inventario_colore_codice = codice
            qr.inventario_colore_sfondo = sfondo
            qr.save(
                update_fields=[
                    "inventario_presente",
                    "inventario_colore_codice",
                    "inventario_colore_sfondo",
                    "updated_at",
                ]
            )

            presenti_count = QrCode.objects.filter(inventario_presente=True).count()

        return Response(
            {
                "status": "ok",
                "qr_id": qr.id,
                "modalita": modalita,
                "presente": True,
                "inventario_colore_codice": qr.inventario_colore_codice,
                "inventario_colore_sfondo": qr.inventario_colore_sfondo,
                "totale_presenti": presenti_count,
                "reset_applicato": bool(modalita == "totale" and reset_before_scan),
            },
            status=status.HTTP_200_OK,
        )

# class ApprovaPropostaView(APIView):
#     permission_classes = [IsAdminUser]

#     def post(self, request, proposta_id):
#         try:
#             proposta = PropostaTecnica.objects.get(pk=proposta_id)
#             if proposta.stato == 'APPROVATA':
#                 return Response({'error': 'Proposta già approvata'}, status=400)

#             nuova_istanza = None
            
#             # Logica differenziata per tipo
#             if proposta.tipo == 'TES':
#                 nuova_istanza = Tessitura.objects.create(
#                     nome=proposta.nome, testo=proposta.descrizione,
#                     aura_richiesta=proposta.aura, elemento_principale=proposta.aura_infusione,
#                     proposta_creazione=proposta
#                 )
#             elif proposta.tipo == 'INF':
#                 nuova_istanza = Infusione.objects.create(
#                     nome=proposta.nome, testo=proposta.descrizione,
#                     aura_richiesta=proposta.aura, aura_infusione=proposta.aura_infusione,
#                     proposta_creazione=proposta, 
#                     tipo_risultato=proposta.tipo_risultato_atteso or 'POT'
#                 )
#             elif proposta.tipo == 'CER':
#                 nuova_istanza = Cerimoniale.objects.create(
#                     nome=proposta.nome, prerequisiti=proposta.prerequisiti,
#                     svolgimento=proposta.svolgimento, effetto=proposta.effetto,
#                     aura_richiesta=proposta.aura, liv=proposta.livello_proposto,
#                     proposta_creazione=proposta
#                 )

#             if nuova_istanza:
#                 # Copia automatica dei componenti (mattoni/caratteristiche)
#                 for comp in proposta.componenti.all():
#                     nuova_istanza.componenti.create(
#                         caratteristica=comp.caratteristica, 
#                         valore=comp.valore
#                     )
                
#                 proposta.stato = 'APPROVATA'
#                 proposta.save()
#                 return Response({
#                     'status': 'approvata', 
#                     'tipo': proposta.tipo, 
#                     'id_generato': nuova_istanza.id
#                 })

#         except PropostaTecnica.DoesNotExist:
#             return Response({'error': 'Proposta non trovata'}, status=404)
        
class InfusioneMasterViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per le Infusioni, usato dai Master.
    Gestisce salvataggi atomici di componenti e statistiche.
    """
    queryset = Infusione.objects.all()
    serializer_class = InfusioneFullEditorSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return InfusioneStaffListSerializer
        return InfusioneFullEditorSerializer

    def get_queryset(self):
        if self.action == 'list':
            qs = (
                Infusione.objects
                .select_related('aura_richiesta')
                .annotate(livello_calc=Sum('componenti__valore'))
                .only(
                    'id',
                    'nome',
                    'aura_richiesta__id',
                    'aura_richiesta__nome',
                    'aura_richiesta__sigla',
                    'aura_richiesta__colore',
                    'aura_richiesta__icona',
                    'aura_richiesta__icona_nome_originale',
                    'aura_richiesta__ordine',
                )
            )
            qs = _campaign_feature_filter(self.request, qs, FEATURE_INFUSIONI)
            return annotate_staff_avista_qr(qs)

        qs = _campaign_feature_filter(self.request, Infusione.objects.all(), FEATURE_INFUSIONI)
        return annotate_staff_avista_qr(qs)

    def perform_create(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))

class TessituraMasterViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per le Tessiture, usato dai Master.
    """
    queryset = Tessitura.objects.all()
    serializer_class = TessituraFullEditorSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return TessituraStaffListSerializer
        return TessituraFullEditorSerializer

    def get_queryset(self):
        if self.action == 'list':
            qs = (
                Tessitura.objects
                .select_related('aura_richiesta')
                .prefetch_related('componenti__caratteristica')
                .annotate(livello_calc=Sum('componenti__valore'))
                .only(
                    'id',
                    'nome',
                    'componenti__valore',
                    'componenti__caratteristica__id',
                    'componenti__caratteristica__nome',
                    'aura_richiesta__id',
                    'aura_richiesta__nome',
                    'aura_richiesta__sigla',
                    'aura_richiesta__colore',
                    'aura_richiesta__icona',
                    'aura_richiesta__icona_nome_originale',
                    'aura_richiesta__ordine',
                )
            )
            qs = _campaign_feature_filter(self.request, qs, FEATURE_TESSITURE)
            return annotate_staff_avista_qr(qs)

        qs = _campaign_feature_filter(self.request, Tessitura.objects.all(), FEATURE_TESSITURE)
        return annotate_staff_avista_qr(qs)

    def perform_create(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))

class CerimonialeMasterViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per i Cerimoniali, usato dai Master.
    """
    queryset = Cerimoniale.objects.all()
    serializer_class = CerimonialeFullEditorSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return CerimonialeStaffListSerializer
        return CerimonialeFullEditorSerializer

    def get_queryset(self):
        if self.action == 'list':
            qs = (
                Cerimoniale.objects
                .select_related('aura_richiesta')
                .only(
                    'id',
                    'nome',
                    'liv',
                    'aura_richiesta__id',
                    'aura_richiesta__nome',
                    'aura_richiesta__sigla',
                    'aura_richiesta__colore',
                    'aura_richiesta__icona',
                    'aura_richiesta__icona_nome_originale',
                    'aura_richiesta__ordine',
                )
            )
            qs = _campaign_feature_filter(self.request, qs, FEATURE_CERIMONIALI)
            return annotate_staff_avista_qr(qs)

        qs = _campaign_feature_filter(self.request, Cerimoniale.objects.all(), FEATURE_CERIMONIALI)
        return annotate_staff_avista_qr(qs)

    def perform_create(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))
    
class OggettoStaffViewSet(viewsets.ModelViewSet):
    serializer_class = OggettoFullEditorSerializer
    permission_classes = [IsStaffOrMaster]

    def get_queryset(self):
        return annotate_staff_avista_qr(
            Oggetto.objects.all().select_related("aura", "classe_oggetto")
        )

class OggettoBaseStaffViewSet(viewsets.ModelViewSet):
    queryset = OggettoBase.objects.all().select_related('classe_oggetto')
    serializer_class = OggettoBaseFullEditorSerializer
    permission_classes = [IsStaffOrMaster]

    def get_queryset(self):
        qs = OggettoBase.objects.all().select_related('classe_oggetto')
        qs = _campaign_feature_filter(self.request, qs, FEATURE_OGGETTI_BASE)
        return annotate_staff_avista_qr(qs)

    def perform_create(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))

    @action(detail=True, methods=["post"], url_path="propaga-istanze")
    def propaga_istanze(self, request, pk=None):
        """Applica il template corrente a tutte le istanze Oggetto generate da questo OggettoBase."""
        template = self.get_object()
        dry_run = bool(request.data.get("dry_run"))
        result = GestioneCraftingService.applica_template_a_istanze(template, dry_run=dry_run)
        return Response(result, status=status.HTTP_200_OK)

class ClasseOggettoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClasseOggetto.objects.all()
    serializer_class = ClasseOggettoSerializer
    permission_classes = [IsStaffOrMaster]
    
class RifiutaPropostaView(APIView):
    permission_classes = [IsStaffOrMaster]

    def post(self, request, pk):
        proposta = get_object_or_404(PropostaTecnica, pk=pk)
        note_staff = request.data.get('note_staff', '')
        
        with transaction.atomic():
            proposta.stato = STATO_PROPOSTA_BOZZA
            proposta.note_staff = note_staff
            proposta.save()
            
            # Invia messaggio solo al personaggio che ha proposto la tecnica
            Messaggio.objects.create(
                mittente=request.user,
                tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
                destinatario_personaggio=proposta.personaggio,
                titolo=f"Proposta Rifiutata: {proposta.nome}",
                testo=f"La tua proposta per '{proposta.nome}' è stata rifiutata e riportata in bozza.\n\nNote Staff:\n{note_staff}"
            )
            
        return Response({'status': 'success', 'message': 'Proposta rifiutata'}, status=status.HTTP_200_OK)
    
class ProposteValutazioneList(generics.ListAPIView):
    permission_classes = [IsStaffOrMaster]
    serializer_class = PropostaTecnicaSerializer

    def get_queryset(self):
        campagna = _get_active_campaign(self.request)
        return PropostaTecnica.objects.filter(
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            personaggio__campagna=campagna,
        ).order_by('data_invio')

class ApprovaPropostaView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        proposta = get_object_or_404(PropostaTecnica, pk=pk)
        
        # Facciamo una copia mutabile dei dati ricevuti dal frontend
        data = request.data.copy()
        
        personaggio = proposta.personaggio
        tipo = proposta.tipo
        aura = proposta.aura
        
        livello_finale = data.get('livello', proposta.livello)
        if tipo == TIPO_PROPOSTA_CERIMONIALE:
             livello_finale = data.get('liv', proposta.livello_proposto) or 1

        _, costo_totale = calcola_costo_creazione_proposta(
            personaggio, proposta, livello_finale=livello_finale
        )

        # Verifica Crediti
        if personaggio.crediti < costo_totale:
            return Response(
                {'error': f"Crediti insufficienti. Richiesti: {costo_totale}, Posseduti: {personaggio.crediti}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- 2. Esecuzione Atomica ---
        try:
            with transaction.atomic():
                # A. Prepara i dati obbligatori per il salvataggio
                # Iniettiamo gli ID nei dati che passeremo al serializer
                data['proposta_creazione'] = proposta.id
                data['aura_richiesta'] = aura.id
                data['campagna'] = proposta.personaggio.campagna_id
                if not proposta.permetti_vendita:
                    data['escluso_negozio_ufficiale'] = True
                
                # Serializer Selection (Usiamo i FullEditor per abilitare la scrittura)
                serializer = None
                
                if tipo == TIPO_PROPOSTA_INFUSIONE:
                    if proposta.aura_infusione:
                        data['aura_infusione'] = proposta.aura_infusione.id
                    serializer = InfusioneFullEditorSerializer(data=data)
                    
                elif tipo == TIPO_PROPOSTA_TESSITURA:
                    if proposta.aura_infusione:
                        # Le tessiture usano 'elemento_principale'
                        data['elemento_principale'] = proposta.aura_infusione.id
                    serializer = TessituraFullEditorSerializer(data=data)
                    
                elif tipo == TIPO_PROPOSTA_CERIMONIALE:
                    # Assicuriamoci che il livello sia settato
                    if 'liv' not in data:
                        data['liv'] = livello_finale
                    serializer = CerimonialeFullEditorSerializer(data=data)
                
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                # B. Salva la Tecnica
                # I FullEditorSerializer gestiscono automaticamente anche il salvataggio dei componenti
                nuova_tecnica = serializer.save()
                
                costo_pagato = Decimal(costo_totale)

                # C. Assegna al Personaggio con costo pagato (per eventuale revoca)
                if tipo == TIPO_PROPOSTA_INFUSIONE:
                    PersonaggioInfusione.objects.create(
                        personaggio=personaggio,
                        infusione=nuova_tecnica,
                        costo_crediti_pagato=costo_pagato,
                    )
                elif tipo == TIPO_PROPOSTA_TESSITURA:
                    PersonaggioTessitura.objects.create(
                        personaggio=personaggio,
                        tessitura=nuova_tecnica,
                        costo_crediti_pagato=costo_pagato,
                    )
                elif tipo == TIPO_PROPOSTA_CERIMONIALE:
                    PersonaggioCerimoniale.objects.create(
                        personaggio=personaggio,
                        cerimoniale=nuova_tecnica,
                        costo_crediti_pagato=costo_pagato,
                    )

                # D. Paga i crediti
                if costo_totale > 0:
                    personaggio.modifica_crediti(-costo_pagato, f"Creazione {proposta.get_tipo_display()}: {nuova_tecnica.nome}")

                # E. Aggiorna Proposta
                proposta.stato = STATO_PROPOSTA_APPROVATA
                proposta.note_staff = data.get('note_staff', proposta.note_staff)
                proposta.save()

                # F. Invia messaggio solo al personaggio che ha proposto la tecnica
                Messaggio.objects.create(
                    mittente=request.user,
                    tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
                    destinatario_personaggio=personaggio,
                    titolo=f"Approvazione: {nuova_tecnica.nome}",
                    testo=(
                        f"La tua tecnica '{nuova_tecnica.nome}' è stata approvata e creata.\n"
                        f"Costo sostenuto: {costo_totale} crediti.\n\n"
                        f"NOTE STAFF:\n{proposta.note_staff}"
                    )
                )

            return Response({'status': 'success', 'id': nuova_tecnica.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class AbilitaStaffViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per le Abilità (Staff).
    """
    queryset = Abilita.objects.all()
    serializer_class = AbilitaFullEditorSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AbilitaStaffPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return AbilitaStaffListSerializer
        return AbilitaFullEditorSerializer

    def get_queryset(self):
        # Lista staff ottimizzata: payload ridotto, campi minimi e supporto ricerca.
        if self.action == 'list':
            queryset = (
                Abilita.objects
                .select_related('aura_riferimento')
                .only(
                    'id',
                    'sync_id',
                    'nome',
                    'costo_pc',
                    'costo_crediti',
                    'is_tratto_aura',
                    'nascondi_in_scheda_abilita',
                    'aura_riferimento__id',
                    'aura_riferimento__nome',
                    'aura_riferimento__sigla',
                    'aura_riferimento__colore',
                    'aura_riferimento__icona',
                    'aura_riferimento__icona_nome_originale',
                    'aura_riferimento__ordine',
                    'livello_riferimento',
                )
                .order_by('nome')
            )
            queryset = _campaign_feature_filter(self.request, queryset, FEATURE_ABILITA)
            search = self.request.query_params.get('search')
            if search:
                queryset = queryset.filter(nome__icontains=search)

            is_tratto_aura = self.request.query_params.get('is_tratto_aura')
            if is_tratto_aura is not None:
                if is_tratto_aura.lower() in ('1', 'true', 'yes'):
                    queryset = queryset.filter(is_tratto_aura=True)
                elif is_tratto_aura.lower() in ('0', 'false', 'no'):
                    queryset = queryset.filter(is_tratto_aura=False)
            return queryset

        return _campaign_feature_filter(self.request, Abilita.objects.select_related(
            'caratteristica',
            'caratteristica_2',
            'caratteristica_3',
            'aura_riferimento',
        ), FEATURE_ABILITA)


class TierStaffViewSet(viewsets.ModelViewSet):
    """
    Gestione completa dei Tier per lo staff.
    """
    serializer_class = TierStaffSerializer
    
    def get_queryset(self):
        # CORRETTO: Usa 'abilita' (il related_name definito nel model Abilita)
        return Tier.objects.prefetch_related('caratteristiche_visibili').annotate(
            abilita_count=Count('abilita') 
        ).order_by('tipo', 'nome')

    @action(detail=False, methods=['get'])
    def all_abilita(self, request):
        """Restituisce lista semplice di tutte le abilità per la combobox"""
        abilita = Abilita.objects.all().order_by('nome')
        serializer = AbilitaSimpleSerializer(abilita, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_abilita_list(self, request, pk=None):
        """
        Aggiorna la lista delle abilità collegate al Tier.
        """
        tier = self.get_object()
        data = request.data.get('abilita_list', [])
        
        # 1. Cancelliamo le vecchie associazioni
        # CORRETTO: Usa il campo 'tabella' (come definito in models.py)
        abilita_tier.objects.filter(tabella=tier).delete()
        
        # 2. Creiamo le nuove
        new_links = []
        for item in data:
            try:
                abilita_obj = Abilita.objects.get(pk=item['abilita_id'])
                new_links.append(abilita_tier(
                    tabella=tier,       # CORRETTO: campo 'tabella'
                    abilita=abilita_obj,
                    ordine=item.get('ordine', 0)
                ))
            except Abilita.DoesNotExist:
                continue
        
        abilita_tier.objects.bulk_create(new_links)
        
        # Ritorna il tier aggiornato
        serializer = self.get_serializer(tier)
        return Response(serializer.data)

class InventarioStaffViewSet(viewsets.ModelViewSet):
    """ViewSet per gestione inventari (solo inventari NON personaggio)"""
    serializer_class = InventarioStaffSerializer
    permission_classes = [IsStaffOrMaster]
    
    def get_queryset(self):
        # Esclude i personaggi (inventari che hanno proprietario)
        qs = Inventario.objects.exclude(
            id__in=Personaggio.all_objects.values_list('inventario_ptr_id', flat=True)
        ).order_by('-id')
        return annotate_staff_avista_qr(qs)
    
    @action(detail=True, methods=['get'])
    def oggetti(self, request, pk=None):
        """Lista oggetti in questo inventario"""
        inventario = self.get_object()
        oggetti = inventario.get_oggetti()
        serializer = OggettoSerializer(oggetti, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def aggiungi_oggetto(self, request, pk=None):
        """Aggiunge un oggetto a questo inventario"""
        inventario = self.get_object()
        oggetto_id = request.data.get('oggetto_id')
        
        if not oggetto_id:
            return Response({"error": "oggetto_id richiesto"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            oggetto = Oggetto.objects.get(id=oggetto_id)
            oggetto.sposta_in_inventario(inventario)
            return Response({"success": f"Oggetto {oggetto.nome} aggiunto all'inventario {inventario.nome}"}, status=status.HTTP_200_OK)
        except Oggetto.DoesNotExist:
            return Response({"error": "Oggetto non trovato"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def rimuovi_oggetto(self, request, pk=None):
        """Rimuove un oggetto da questo inventario (lo mette senza posizione)"""
        inventario = self.get_object()
        oggetto_id = request.data.get('oggetto_id')
        
        if not oggetto_id:
            return Response({"error": "oggetto_id richiesto"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            oggetto = Oggetto.objects.get(id=oggetto_id, inventario_corrente=inventario)
            oggetto.sposta_in_inventario(None)  # None = senza posizione
            return Response({"success": f"Oggetto {oggetto.nome} rimosso dall'inventario"}, status=status.HTTP_200_OK)
        except Oggetto.DoesNotExist:
            return Response({"error": "Oggetto non trovato in questo inventario"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OggettiSenzaPosizioneView(APIView):
    """Lista oggetti senza inventario (senza posizione)"""
    permission_classes = [IsStaffOrMaster]
    
    def get(self, request):
        # Oggetti senza tracciamento attivo (non sono in nessun inventario)
        # Gli oggetti hanno tracciamento quando esiste un OggettoInInventario con data_fine=null
        from django.db.models import Q, Exists, OuterRef
        from .models import OggettoInInventario
        
        # Subquery per trovare se esiste un tracciamento attivo
        tracciamento_attivo = OggettoInInventario.objects.filter(
            oggetto=OuterRef('pk'),
            data_fine__isnull=True
        )
        
        # Oggetti senza tracciamento attivo
        oggetti = Oggetto.objects.annotate(
            ha_inventario=Exists(tracciamento_attivo)
        ).filter(ha_inventario=False)
        
        serializer = OggettoSerializer(oggetti, many=True)
        return Response(serializer.data)


class TipologiaEffettoViewSet(viewsets.ModelViewSet):
    """CRUD per Tipologie Effetto Casuale (Staff)."""
    queryset = TipologiaEffetto.objects.all().select_related('aura_collegata')
    serializer_class = TipologiaEffettoStaffSerializer
    permission_classes = [IsStaffOrMaster]


class EffettoCasualeViewSet(viewsets.ModelViewSet):
    """CRUD per Effetti Casuali (Staff)."""
    queryset = EffettoCasuale.objects.all().select_related('tipologia', 'elemento_principale')
    serializer_class = EffettoCasualeStaffSerializer
    permission_classes = [IsStaffOrMaster]
    filterset_fields = ['tipologia']


class DichiarazioneStaffViewSet(viewsets.ModelViewSet):
    """CRUD per Dichiarazioni e voci di Glossario (Staff)."""
    queryset = Dichiarazione.objects.all().order_by('tipo', 'nome')
    serializer_class = DichiarazioneStaffSerializer
    permission_classes = [IsStaffOrMaster]
    filterset_fields = ['tipo']
    search_fields = ['nome', 'dichiarazione', 'descrizione']


class EraStaffViewSet(viewsets.ModelViewSet):
    queryset = Era.objects.all().order_by("ordine", "nome")
    serializer_class = EraStaffSerializer
    permission_classes = [IsStaffOrMaster]


class PrefetturaStaffViewSet(viewsets.ModelViewSet):
    queryset = Prefettura.objects.select_related("era").all().order_by("era__ordine", "ordine", "nome")
    serializer_class = PrefetturaStaffSerializer
    permission_classes = [IsStaffOrMaster]


class RegioneStaffViewSet(viewsets.ModelViewSet):
    queryset = Regione.objects.all().order_by("ordine", "nome")
    serializer_class = RegioneStaffSerializer
    permission_classes = [IsStaffOrMaster]


class TipoCarrieraStaffViewSet(viewsets.ModelViewSet):
    queryset = TipoCarriera.objects.all().order_by("ordine", "nome")
    serializer_class = TipoCarrieraStaffSerializer
    permission_classes = [IsStaffOrMaster]


class CarrieraStaffViewSet(viewsets.ModelViewSet):
    queryset = Carriera.objects.select_related("tipo_carriera").prefetch_related("tiers_sblocco").order_by(
        "tipo_carriera__ordine", "nome"
    )
    serializer_class = CarrieraStaffSerializer
    permission_classes = [IsStaffOrMaster]
    filterset_fields = ["tipo_carriera__codice", "tipo"]
    search_fields = ["nome", "descrizione"]

    @action(detail=False, methods=["get"])
    def tiers_selezionabili(self, request):
        from personaggi.carriere_tier_sblocco import tiers_selezionabili_per_sblocco_carriera

        qs = tiers_selezionabili_per_sblocco_carriera()
        data = [{"id": t.id, "nome": t.nome, "tipo": t.tipo} for t in qs]
        return Response(data)

    def _invalidate_carriera_members_cache(self, carriera):
        from personaggi.carriere_tier_sblocco import invalidate_acquirable_skills_cache

        for pid in PersonaggioCarrieraMembership.objects.filter(
            carriera=carriera, data_a__isnull=True
        ).values_list("personaggio_id", flat=True):
            invalidate_acquirable_skills_cache(pid)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._invalidate_carriera_members_cache(serializer.instance)


class CaricaStaffViewSet(viewsets.ModelViewSet):
    queryset = Carica.objects.select_related("carriera", "carriera__tipo_carriera").order_by(
        "carriera__nome", "ordine", "nome"
    )
    serializer_class = CaricaStaffSerializer
    permission_classes = [IsStaffOrMaster]
    filterset_fields = ["carriera", "carriera__tipo_carriera__codice", "attiva"]
    search_fields = ["nome", "carriera__nome"]


class PersonaggioCarrieraMembershipStaffViewSet(viewsets.ModelViewSet):
    queryset = PersonaggioCarrieraMembership.objects.select_related(
        "personaggio", "carriera", "carica", "tipo_carriera"
    ).order_by("-data_da", "-id")
    serializer_class = PersonaggioCarrieraMembershipStaffSerializer
    permission_classes = [IsStaffOrMaster]
    filterset_fields = ["personaggio", "carriera", "tipo_carriera__codice", "data_a"]
    search_fields = ["personaggio__nome", "carriera__nome", "carica__nome"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        chiudi_korp = request.data.get("chiudi_korp_precedenti") in (True, "true", "1", 1)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tipo = serializer.validated_data.get("tipo_carriera")
        personaggio = serializer.validated_data.get("personaggio")
        if chiudi_korp and tipo and tipo.codice == "korp" and personaggio:
            now = timezone.now()
            PersonaggioCarrieraMembership.objects.filter(
                personaggio=personaggio,
                tipo_carriera__codice="korp",
                data_a__isnull=True,
            ).update(data_a=now)
        self.perform_create(serializer)
        from personaggi.carriere_tier_sblocco import invalidate_acquirable_skills_cache

        invalidate_acquirable_skills_cache(serializer.instance.personaggio_id)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        from personaggi.carriere_tier_sblocco import invalidate_acquirable_skills_cache

        invalidate_acquirable_skills_cache(serializer.instance.personaggio_id)

    def perform_destroy(self, instance):
        personaggio_id = instance.personaggio_id
        super().perform_destroy(instance)
        from personaggi.carriere_tier_sblocco import invalidate_acquirable_skills_cache

        invalidate_acquirable_skills_cache(personaggio_id)


class MattoniMagiciListView(APIView):
    """Lista mattoni con aura magica (per dropdown elemento principale negli effetti casuali)."""
    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        mattoni = Mattone.objects.filter(
            Q(aura__nome__icontains='magica') | Q(aura__sigla__iexact='mag')
        ).select_related('aura').order_by('aura__ordine', 'nome').values('id', 'nome', 'aura_id')
        return Response(list(mattoni))


class SelezionaEffettoCasualeView(APIView):
    """Seleziona un effetto casuale dalla tipologia e opzionalmente lo applica al personaggio."""
    permission_classes = [IsStaffOrMaster]

    def post(self, request):
        from .effetti_casuali import seleziona_effetto_casuale
        tipologia_id = request.data.get('tipologia_id')
        personaggio_id = request.data.get('personaggio_id')
        if not tipologia_id:
            return Response({"error": "tipologia_id richiesto"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tipologia = TipologiaEffetto.objects.get(pk=tipologia_id)
        except TipologiaEffetto.DoesNotExist:
            return Response({"error": "Tipologia non trovata"}, status=status.HTTP_404_NOT_FOUND)
        personaggio = None
        if personaggio_id:
            try:
                personaggio = Personaggio.objects.get(pk=personaggio_id)
            except Personaggio.DoesNotExist:
                pass
        risultato = seleziona_effetto_casuale(tipologia, personaggio)
        if 'errore' in risultato:
            return Response(risultato, status=status.HTTP_400_BAD_REQUEST)
        out = {'nome': risultato['nome'], 'descrizione': risultato['descrizione'], 'formula': risultato.get('formula', '')}
        if 'oggetto_creato' in risultato:
            out['oggetto_creato_id'] = risultato['oggetto_creato'].id
        if 'consumabile_creato' in risultato:
            out['consumabile_creato_id'] = risultato['consumabile_creato'].id
        return Response(out, status=status.HTTP_200_OK)


class ManifestoStaffViewSet(viewsets.ModelViewSet):
    """CRUD manifesti (contenuto in `testo`, requisiti JSON opzionali)."""

    serializer_class = ManifestoStaffSerializer
    permission_classes = [IsStaffOrMaster]

    def get_queryset(self):
        return annotate_staff_avista_qr(Manifesto.objects.all().order_by("-id"))


class NodoStaffViewSet(viewsets.ModelViewSet):
    """CRUD nodi QR (cooldown + tipo minore/maggiore)."""

    serializer_class = NodoStaffSerializer
    permission_classes = [IsStaffOrMaster]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Nodo.objects.all().order_by("-id")
        active = _get_active_campaign(self.request)
        base = _get_default_campaign()
        if not active:
            return annotate_staff_avista_qr(qs)
        if active == base:
            return annotate_staff_avista_qr(qs.filter(campagna=active))
        return annotate_staff_avista_qr(qs.filter(Q(campagna=active) | Q(campagna=base)))

    def perform_create(self, serializer):
        camp = _get_active_campaign(self.request) or _get_default_campaign()
        serializer.save(campagna=camp)


class NodoRewardConfigStaffViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista configurazioni reward nodo disponibili per l'editor staff nodi."""

    serializer_class = NodoRewardConfigStaffSerializer
    permission_classes = [IsStaffOrMaster]

    def get_queryset(self):
        qs = NodoRewardConfig.objects.filter(attiva=True).order_by("nome")
        active = _get_active_campaign(self.request)
        base = _get_default_campaign()
        if not active:
            return qs
        if base and active.id != base.id:
            return qs.filter(Q(campagna=active) | Q(campagna=base))
        return qs.filter(campagna=active)


class InnescoTimerStaffViewSet(viewsets.ModelViewSet):
    """CRUD inneschi timer QR (target globale o per era/regione/KORP)."""

    serializer_class = InnescoTimerStaffSerializer
    permission_classes = [IsStaffOrMaster]

    def get_queryset(self):
        qs = InnescoTimer.objects.prefetch_related("target_ere", "target_regioni", "target_korps").order_by(
            "-id"
        )
        active = _get_active_campaign(self.request)
        base = _get_default_campaign()
        if not active:
            return annotate_staff_avista_qr(qs)
        if base and active.id != base.id:
            return annotate_staff_avista_qr(qs.filter(Q(campagna=active) | Q(campagna=base)))
        return annotate_staff_avista_qr(qs.filter(campagna=active))

    @staticmethod
    def _apply_target_lists(obj, data):
        if "target_ere_ids" in data:
            ids = data.get("target_ere_ids") or []
            obj.target_ere.set(Era.objects.filter(pk__in=ids))
        if "target_regioni_ids" in data:
            ids = data.get("target_regioni_ids") or []
            obj.target_regioni.set(Regione.objects.filter(pk__in=ids))
        if "target_korps_ids" in data:
            ids = data.get("target_korps_ids") or []
            obj.target_korps.set(Korp.objects.filter(pk__in=ids))

    def perform_create(self, serializer):
        camp = _get_active_campaign(self.request) or _get_default_campaign()
        with transaction.atomic():
            obj = serializer.save(campagna=camp)
            self._apply_target_lists(obj, self.request.data)

    def perform_update(self, serializer):
        with transaction.atomic():
            obj = serializer.save()
            self._apply_target_lists(obj, self.request.data)


class FormulaBuilderSchemaView(APIView):
    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        return Response(FORMULA_BUILDER_SCHEMA)


class FormulaBuilderPreviewView(APIView):
    permission_classes = [IsStaffOrMaster]

    @staticmethod
    def _build_preview_context(payload):
        from .models import FORMULA_SCOPE_ATTACK, FORMULA_SCOPE_WEAVE, Punteggio

        context = dict(payload.get("context") or {})
        selections = payload.get("selections") or {}
        formula_type = payload.get("formula_type") or "attack"
        if formula_type == "weave":
            context.setdefault("formula_kind", FORMULA_SCOPE_WEAVE)
            context["allow_implicit_formula_source"] = False
        elif formula_type == "capacity":
            context.setdefault("formula_kind", FORMULA_SCOPE_ATTACK)
            context["allow_implicit_formula_source"] = False
        else:
            context.setdefault("formula_kind", FORMULA_SCOPE_ATTACK)
            context["allow_implicit_formula_source"] = True

        source_ids = selections.get("formula_source")
        if isinstance(source_ids, str):
            source_ids = [source_ids]
        source_ids = source_ids or []
        wants_element = any(
            str(sid).strip().lower() in ("elemento", "elemento_principale")
            for sid in source_ids
        )
        element_id = selections.get("source_element_id")
        if wants_element and element_id and not context.get("elemento"):
            elemento = Punteggio.objects.filter(pk=element_id).first()
            if elemento:
                context["elemento"] = elemento
        entity_name = (selections.get("entity_name") or context.get("entity_name") or "").strip()
        if entity_name:
            context["entity_name"] = entity_name
        return context

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        formula = payload.get("formula")
        formula_type = payload.get("formula_type") or "attack"
        current_stats = payload.get("stats_by_param") or {}
        selections = payload.get("selections") or {}
        custom_text = payload.get("custom_text") or ""
        context = self._build_preview_context(payload)

        formula_template = (formula or "").strip() or build_formula_template(formula_type, selections)
        merged_stats = build_stats_by_selection(current_stats=current_stats, selections=selections)
        rendered = render_formula_preview(formula=formula_template, stats_by_param=merged_stats, context=context)
        if custom_text:
            rendered = f"{rendered} {custom_text}".strip()

        return Response(
            {
                "formula_rendered": rendered,
                "stats_by_param": merged_stats,
                "formula_template": formula_template,
                "custom_text": custom_text,
            }
        )


class FormulaSemanticOptionsView(APIView):
    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        mattoni = (
            Mattone.objects.filter(aura__sigla__iexact="AMA")
            .select_related("aura")
            .order_by("nome")
        )
        data = [
            {
                "id": m.id,
                "nome": m.nome,
                "dichiarazione": m.dichiarazione or "",
                "label": (m.dichiarazione or m.nome or "").strip(),
            }
            for m in mattoni
        ]
        return Response({"elementi_mattoni": data})


class StaffMinigiocoQrConfigView(APIView):
    """GET/PUT configurazione minigioco per un QrCode."""

    permission_classes = [IsStaffOrMaster]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @staticmethod
    def _parse_json_list(raw):
        import json

        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw) if raw.strip() else []
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _sanitize_gruppi_requisiti(items):
        out = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            reqs = item.get("requisiti") or []
            if not isinstance(reqs, list) or not reqs:
                continue
            op = (item.get("operator") or "AND").strip().upper()
            if op not in ("AND", "OR"):
                op = "AND"
            out.append({"operator": op, "requisiti": reqs})
        return out

    @staticmethod
    def _sanitize_regole_difficolta(items):
        out = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            reqs = item.get("requisiti") or []
            if not isinstance(reqs, list) or not reqs:
                continue
            try:
                diff = max(1, min(4, int(item.get("difficolta") or 4)))
            except (TypeError, ValueError):
                continue
            op = (item.get("operator") or "AND").strip().upper()
            if op not in ("AND", "OR"):
                op = "AND"
            out.append({"operator": op, "requisiti": reqs, "difficolta": diff})
        return out

    def _serialize(self, config, request):
        img_url = None
        if config.immagine:
            try:
                img_url = request.build_absolute_uri(config.immagine.url)
            except Exception:
                img_url = None
        return {
            "sezione_attiva": config.sezione_attiva,
            "attivo": config.attivo,
            "tipi_abilitati": config.tipi_abilitati or list(MinigiocoQrConfig.TIPI_DEFAULT),
            "difficolta": config.difficolta,
            "requisiti_attivazione": config.requisiti_attivazione or [],
            "messaggio_accesso_negato": config.messaggio_accesso_negato or "",
            "esclusioni_minigioco": config.esclusioni_minigioco or [],
            "regole_difficolta": config.regole_difficolta or [],
            "messaggio_pre": config.messaggio_pre or "",
            "messaggio_vittoria": config.messaggio_vittoria or "",
            "timer_secondi": config.timer_secondi,
            "timer_scadenza_azione": config.timer_scadenza_azione,
            "usa_biblioteca_se_vuota": config.usa_biblioteca_se_vuota,
            "modalita_sblocco": config.modalita_sblocco,
            "sblocco_secondi": config.sblocco_secondi,
            "usa_default_pagina": config.usa_default_pagina,
            "immagine_url": img_url,
        }

    def get(self, request, qr_id):
        qr = get_object_or_404(QrCode, pk=qr_id)
        config = getattr(qr, "configurazione_minigioco", None)
        if not config:
            return Response(
                {
                    "qr_id": qr.id,
                    "config": None,
                }
            )
        return Response({"qr_id": qr.id, "config": self._serialize(config, request)})

    @transaction.atomic
    def put(self, request, qr_id):
        qr = get_object_or_404(QrCode, pk=qr_id)
        config, _created = MinigiocoQrConfig.objects.get_or_create(
            qr_code=qr,
            defaults={
                "tipi_abilitati": list(MinigiocoQrConfig.TIPI_DEFAULT),
                "difficolta_min": 1,
                "difficolta": 4,
            },
        )

        data = request.data
        if "sezione_attiva" in data:
            config.sezione_attiva = data.get("sezione_attiva") in (True, "true", "1", 1, "on")
        if "attivo" in data:
            config.attivo = data.get("attivo") in (True, "true", "1", 1, "on")
        if "usa_biblioteca_se_vuota" in data:
            config.usa_biblioteca_se_vuota = data.get("usa_biblioteca_se_vuota") in (
                True,
                "true",
                "1",
                1,
                "on",
            )
        if "usa_default_pagina" in data:
            config.usa_default_pagina = data.get("usa_default_pagina") in (
                True,
                "true",
                "1",
                1,
                "on",
            )
        if "tipi_abilitati" in data:
            import json

            raw_tipi = data.get("tipi_abilitati")
            if isinstance(raw_tipi, str):
                try:
                    raw_tipi = json.loads(raw_tipi) if raw_tipi.strip() else []
                except json.JSONDecodeError:
                    return Response(
                        {"error": "tipi_abilitati JSON non valido."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            if isinstance(raw_tipi, list):
                tipi = [str(t).strip() for t in raw_tipi if str(t).strip() in dict(MinigiocoQrConfig.TIPO_CHOICES)]
                if tipi:
                    config.tipi_abilitati = tipi
        if "difficolta" in data:
            try:
                config.difficolta = max(1, min(4, int(data.get("difficolta"))))
            except (TypeError, ValueError):
                pass
        if "esclusioni_minigioco" in data:
            parsed = self._parse_json_list(data.get("esclusioni_minigioco"))
            if parsed is None:
                return Response(
                    {"error": "esclusioni_minigioco JSON non valido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config.esclusioni_minigioco = self._sanitize_gruppi_requisiti(parsed)
        if "regole_difficolta" in data:
            parsed = self._parse_json_list(data.get("regole_difficolta"))
            if parsed is None:
                return Response(
                    {"error": "regole_difficolta JSON non valido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config.regole_difficolta = self._sanitize_regole_difficolta(parsed)
        if "messaggio_pre" in data:
            config.messaggio_pre = str(data.get("messaggio_pre") or "")
        if "messaggio_vittoria" in data:
            config.messaggio_vittoria = str(data.get("messaggio_vittoria") or "")
        if "timer_secondi" in data:
            raw = data.get("timer_secondi")
            if raw in (None, "", "null"):
                config.timer_secondi = None
            else:
                try:
                    config.timer_secondi = max(1, int(raw))
                except (TypeError, ValueError):
                    pass
        if "timer_scadenza_azione" in data:
            az = str(data.get("timer_scadenza_azione") or "").strip()
            if az in dict(MinigiocoQrConfig.TIMER_SAZIONE_CHOICES):
                config.timer_scadenza_azione = az
        if "modalita_sblocco" in data:
            mod = str(data.get("modalita_sblocco") or "").strip()
            if mod in dict(MinigiocoQrConfig.SBLOCCO_CHOICES):
                config.modalita_sblocco = mod
        if "sblocco_secondi" in data:
            raw = data.get("sblocco_secondi")
            if raw in (None, "", "null"):
                config.sblocco_secondi = None
            else:
                try:
                    config.sblocco_secondi = max(1, int(raw))
                except (TypeError, ValueError):
                    pass
        if config.modalita_sblocco == MinigiocoQrConfig.SBLOCCO_TEMPORANEO:
            if not config.sblocco_secondi:
                return Response(
                    {"error": "sblocco_secondi obbligatorio con modalità temporaneo."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if "requisiti_attivazione" in data:
            import json

            raw_req = data.get("requisiti_attivazione")
            if isinstance(raw_req, str):
                try:
                    raw_req = json.loads(raw_req) if raw_req.strip() else []
                except json.JSONDecodeError:
                    return Response(
                        {"error": "requisiti_attivazione JSON non valido."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            if isinstance(raw_req, list):
                config.requisiti_attivazione = raw_req
        if "messaggio_accesso_negato" in data:
            config.messaggio_accesso_negato = str(data.get("messaggio_accesso_negato") or "")
        if "rimuovi_immagine" in data and data.get("rimuovi_immagine") in (True, "true", "1", 1):
            if config.immagine:
                config.immagine.delete(save=False)
            config.immagine = None
        if request.FILES.get("immagine"):
            config.immagine = request.FILES["immagine"]

        config.save()
        return Response({"qr_id": qr.id, "config": self._serialize(config, request)})


class StaffMinigiocoBibliotecaView(APIView):
    """GET elenco libreria immagini minigioco (staff)."""

    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        from personaggi.minigioco_biblioteca import (
            BIBLIOTECA_TARGET,
            biblioteca_immagine_count,
            openverse_config_status,
        )

        rows = MinigiocoBibliotecaImmagine.objects.order_by("-aggiunta_at")[:120]
        items = []
        for row in rows:
            img_url = None
            if row.immagine:
                try:
                    img_url = request.build_absolute_uri(row.immagine.url)
                except Exception:
                    img_url = None
            items.append(
                {
                    "id": str(row.id),
                    "titolo": row.titolo,
                    "autore": row.autore,
                    "licenza": row.licenza,
                    "fonte": row.fonte,
                    "immagine_url": img_url,
                    "source_page_url": row.source_page_url,
                }
            )
        ultima = MinigiocoBibliotecaImmagine.objects.order_by("-aggiunta_at").first()
        return Response(
            {
                "count": biblioteca_immagine_count(),
                "target": BIBLIOTECA_TARGET,
                "ultimo_aggiornamento": ultima.aggiunta_at.isoformat() if ultima else None,
                "openverse": openverse_config_status(),
                "items": items,
            }
        )


class StaffMinigiocoOpenverseSalvaView(APIView):
    """POST salva credenziali Openverse (dopo registrazione dal browser o incolla manuale)."""

    permission_classes = [IsStaffOrMaster]

    def post(self, request):
        from personaggi.minigioco_biblioteca import salva_openverse_credenziali

        result = salva_openverse_credenziali(
            client_id=(request.data.get("client_id") or "").strip(),
            client_secret=(request.data.get("client_secret") or "").strip(),
            name=(request.data.get("name") or "").strip(),
            description=(request.data.get("description") or "").strip(),
            email=(request.data.get("email") or "").strip(),
            api_message=(request.data.get("api_message") or "").strip(),
        )
        if not result.get("ok"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class StaffMinigiocoOpenverseRegistraView(APIView):
    """POST registra app OAuth su Openverse e salva credenziali sul nodo."""

    permission_classes = [IsStaffOrMaster]

    def post(self, request):
        from personaggi.minigioco_biblioteca import registra_openverse_app

        result = registra_openverse_app(
            name=(request.data.get("name") or "").strip(),
            description=(request.data.get("description") or "").strip(),
            email=(request.data.get("email") or "").strip(),
        )
        if not result.get("ok"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class StaffMinigiocoOpenverseVerificaView(APIView):
    """POST verifica token OAuth e ricerca immagini Openverse."""

    permission_classes = [IsStaffOrMaster]

    def post(self, request):
        from personaggi.minigioco_biblioteca import verifica_openverse_connessione

        result = verifica_openverse_connessione()
        if not result.get("ok"):
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(result, status=status.HTTP_200_OK)


class StaffMinigiocoBibliotecaAggiornaView(APIView):
    """POST scarica ~100 immagini open license da Openverse."""

    permission_classes = [IsStaffOrMaster]

    def post(self, request):
        from personaggi.minigioco_biblioteca import BIBLIOTECA_TARGET, aggiorna_biblioteca_immagini

        raw_target = request.data.get("target")
        try:
            target = max(10, min(150, int(raw_target))) if raw_target not in (None, "") else BIBLIOTECA_TARGET
        except (TypeError, ValueError):
            target = BIBLIOTECA_TARGET

        try:
            result = aggiorna_biblioteca_immagini(target=target)
        except Exception as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not result.get("ok"):
            return Response(
                result,
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result, status=status.HTTP_200_OK)


class PersonaggioStaffPagination(PageNumberPagination):
    page_size = 40
    page_size_query_param = 'page_size'
    max_page_size = 200


class PersonaggioStaffViewSet(viewsets.ModelViewSet):
    """
    Hub staff per personaggi: lista leggera con filtri, dettaglio completo in modale.
    """

    permission_classes = [IsStaffOrMaster]
    pagination_class = PersonaggioStaffPagination
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def _staff_personaggi_queryset(self):
        from personaggi.views import _can_operate_in_campaign, _get_default_campaign

        user = self.request.user
        active_campaign = _get_active_campaign(self.request)
        default_campaign = _get_default_campaign()

        membership_qs = PersonaggioCarrieraMembership.objects.filter(
            data_a__isnull=True
        ).select_related('carriera', 'carica', 'tipo_carriera')

        qr_sub = QrCode.objects.filter(vista_id=OuterRef('pk')).values('id')[:1]

        qs = (
            Personaggio.objects.select_related(
                'tipologia', 'proprietario', 'era', 'prefettura', 'campagna', 'social_profile'
            )
            .prefetch_related(
                Prefetch('carriere_membership', queryset=membership_qs, to_attr='_prefetched_membership'),
            )
            .annotate(qrcode_id_ann=Subquery(qr_sub))
        )

        if active_campaign and default_campaign and active_campaign.id != default_campaign.id:
            qs = qs.filter(
                Q(campagna=active_campaign) | Q(campagna=default_campaign, tipologia__giocante=False)
            )
        elif active_campaign:
            qs = qs.filter(campagna=active_campaign)

        if not user.is_superuser and not _can_operate_in_campaign(
            user, active_campaign, needs_master=True
        ):
            return Personaggio.objects.none()

        params = self.request.query_params
        tipo = (params.get('tipo') or 'all').lower()
        if tipo == 'pg':
            qs = qs.filter(tipologia__giocante=True)
        elif tipo == 'png':
            qs = qs.filter(tipologia__giocante=False)

        q = (params.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(proprietario__username__icontains=q)
                | Q(proprietario__first_name__icontains=q)
                | Q(proprietario__last_name__icontains=q)
                | Q(costume__icontains=q)
            )

        era_id = params.get('era')
        if era_id:
            qs = qs.filter(era_id=era_id)

        carriera_id = params.get('carriera') or params.get('korp')
        if carriera_id:
            qs = qs.filter(
                carriere_membership__carriera_id=carriera_id,
                carriere_membership__data_a__isnull=True,
            )

        morto = (params.get('morto') or 'vivo').lower()
        if morto == 'vivo':
            qs = qs.filter(data_morte__isnull=True)
        elif morto == 'morto':
            qs = qs.filter(data_morte__isnull=False)

        return qs.distinct().order_by('nome')

    def get_queryset(self):
        return self._staff_personaggi_queryset()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PersonaggioStaffDetailSerializer
        return PersonaggioStaffListSerializer

    def get_object(self):
        obj = super().get_object()
        obj.carriere_membership_active = list(
            PersonaggioCarrieraMembership.objects.filter(
                personaggio=obj, data_a__isnull=True
            ).select_related('carriera', 'carica', 'tipo_carriera').order_by('-data_da')
        )
        obj._prefetched_qrcode = list(QrCode.objects.filter(vista_id=obj.pk)[:1])
        obj.sync_recuperi_automatici()
        obj._staff_movimenti_credito = list(obj.movimenti_credito.order_by('-data')[:20])
        obj._staff_movimenti_pc = list(obj.movimenti_pc.order_by('-data')[:20])
        return obj

    def _serialize_detail(self, instance, request):
        serializer = PersonaggioStaffDetailSerializer(instance, context={'request': request})
        data = serializer.data
        data['movimenti_credito'] = CreditoMovimentoSerializer(
            instance._staff_movimenti_credito, many=True
        ).data
        data['movimenti_pc'] = PuntiCaratteristicaMovimentoListSerializer(
            instance._staff_movimenti_pc, many=True
        ).data
        return data

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self._serialize_detail(instance, request))

    def partial_update(self, request, *args, **kwargs):
        personaggio = self.get_object()
        allowed = {
            'nome', 'testo', 'costume', 'note_master', 'watch_enabled',
            'peso_influencer', 'badge_instafame', 'era', 'prefettura',
            'prefettura_esterna', 'tipologia', 'impostazioni_ui',
            'foto_trucco', 'foto_outfit', 'clear_foto_trucco', 'clear_foto_outfit',
        }
        payload = {k: v for k, v in request.data.items() if k in allowed}
        for key in ('foto_trucco', 'foto_outfit'):
            if key in request.FILES:
                payload[key] = request.FILES[key]
        if not payload and not any(k in request.FILES for k in ('foto_trucco', 'foto_outfit')):
            clear_flags = (
                str(request.data.get('clear_foto_trucco', '')).lower() in ('1', 'true', 'yes')
                or str(request.data.get('clear_foto_outfit', '')).lower() in ('1', 'true', 'yes')
            )
            if not clear_flags:
                return Response({'detail': 'Nessun campo aggiornabile.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PersonaggioStaffDetailSerializer(
            personaggio, data=payload, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        from personaggi.views import _is_master_in_campaign
        user = request.user
        changing_era = any(k in payload for k in ('era', 'prefettura', 'prefettura_esterna'))
        if changing_era and not (user.is_superuser or _is_master_in_campaign(user, personaggio.campagna)):
            return Response(
                {'detail': 'Solo i master possono modificare Era/Prefettura.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if changing_era and not personaggio.can_edit_era_prefettura():
            if not (user.is_superuser or _is_master_in_campaign(user, personaggio.campagna)):
                return Response(
                    {'detail': 'Era/Prefettura bloccate dopo l\'inizio del primo evento.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            personaggio = serializer.save()
            from personaggi.serializers import _apply_personaggio_costume_photo_clears
            _apply_personaggio_costume_photo_clears(personaggio, request)
            if changing_era:
                try:
                    personaggio.assegna_era_e_prefettura(
                        era=personaggio.era,
                        prefettura=personaggio.prefettura,
                        prefettura_esterna=personaggio.prefettura_esterna,
                        force=bool(user.is_superuser or _is_master_in_campaign(user, personaggio.campagna)),
                    )
                except Exception as exc:
                    return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return self.retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['patch'],
        url_path='social-profile',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def patch_social_profile(self, request, pk=None):
        from social.models import SocialProfile
        from social.serializers import SocialProfileStaffSerializer

        personaggio = self.get_object()
        profile, _ = SocialProfile.objects.select_related(
            "personaggio",
            "personaggio__era",
            "personaggio__prefettura",
            "personaggio__prefettura__regione",
            "personaggio__segno_zodiacale",
        ).get_or_create(personaggio=personaggio)

        payload = {}
        for key in ("nickname", "descrizione", "professioni"):
            if key in request.data:
                payload[key] = request.data.get(key)
        if "foto_principale" in request.FILES:
            payload["foto_principale"] = request.FILES["foto_principale"]

        if not payload and str(request.data.get("clear_foto_principale", "")).lower() not in (
            "1",
            "true",
            "yes",
        ):
            return Response({"detail": "Nessun campo aggiornabile."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SocialProfileStaffSerializer(
            profile, data=payload, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            serializer.save()
            if str(request.data.get("clear_foto_principale", "")).lower() in ("1", "true", "yes"):
                if profile.foto_principale:
                    profile.foto_principale.delete(save=False)
                profile.foto_principale = None
                profile.save(update_fields=["foto_principale", "updated_at"])

        profile.refresh_from_db()
        return Response(
            SocialProfileStaffSerializer(profile, context={"request": request}).data
        )

    @action(detail=True, methods=['post'], url_path='add-resources')
    def add_resources(self, request, pk=None):
        personaggio = self.get_object()
        tipo = request.data.get('tipo')
        reason = request.data.get('reason', 'Intervento Staff')
        try:
            amount = int(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response({'error': 'Importo non valido'}, status=status.HTTP_400_BAD_REQUEST)
        if amount == 0:
            return Response({'error': "L'importo non può essere zero"}, status=status.HTTP_400_BAD_REQUEST)
        if tipo == 'crediti':
            personaggio.modifica_crediti(amount, reason)
            val = personaggio.crediti
        elif tipo == 'pc':
            personaggio.modifica_pc(amount, reason)
            val = personaggio.punti_caratteristica
        else:
            return Response({'error': 'Tipo risorsa non valido'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'success', 'new_val': val, 'msg': 'Risorse aggiornate'})

    @action(detail=True, methods=['post'], url_path='crea-oggetto-da-base')
    def crea_oggetto_da_base(self, request, pk=None):
        """Crea un'istanza Oggetto da OggettoBase e la mette nell'inventario del personaggio."""
        personaggio = self.get_object()
        oggetto_base_id = request.data.get('oggetto_base_id')
        motivo = (request.data.get('motivo') or 'Assegnazione staff').strip()
        if not oggetto_base_id:
            return Response({'detail': 'oggetto_base_id obbligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            template = OggettoBase.objects.get(pk=oggetto_base_id)
        except OggettoBase.DoesNotExist:
            return Response({'detail': 'Oggetto base non trovato.'}, status=status.HTTP_404_NOT_FOUND)
        if not _campaign_feature_filter(
            request, OggettoBase.objects.filter(pk=template.pk), FEATURE_OGGETTI_BASE
        ).exists():
            return Response({'detail': 'Template non disponibile per la campagna attiva.'}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            nuovo = GestioneCraftingService.crea_istanza_da_oggetto_base(template, personaggio)
            personaggio.aggiungi_log(f"Ricevuto oggetto «{nuovo.nome}» ({motivo}).")
        return Response({
            'id': nuovo.id,
            'nome': nuovo.nome,
            'tipo_oggetto': nuovo.tipo_oggetto,
            'detail': f'Istanza «{nuovo.nome}» creata nell\'inventario di {personaggio.nome}.',
        }, status=status.HTTP_201_CREATED)

    def _oggetto_in_inventario_personaggio(self, personaggio, oggetto):
        inv = oggetto.inventario_corrente
        return inv is not None and inv.pk == personaggio.inventario_ptr_id

    @action(detail=True, methods=['post'], url_path='aggiungi-oggetto')
    def aggiungi_oggetto(self, request, pk=None):
        """Sposta un'istanza Oggetto esistente nell'inventario del personaggio."""
        personaggio = self.get_object()
        oggetto_id = request.data.get('oggetto_id')
        motivo = (request.data.get('motivo') or 'Assegnazione staff').strip()
        if not oggetto_id:
            return Response({'detail': 'oggetto_id obbligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            oggetto = Oggetto.objects.get(pk=oggetto_id)
        except Oggetto.DoesNotExist:
            return Response({'detail': 'Oggetto non trovato.'}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            oggetto.sposta_in_inventario(personaggio)
            personaggio.aggiungi_log(f"Ricevuto oggetto «{oggetto.nome}» ({motivo}).")
        return Response({
            'id': oggetto.id,
            'nome': oggetto.nome,
            'detail': f'«{oggetto.nome}» aggiunto all\'inventario di {personaggio.nome}.',
        })

    @action(detail=True, methods=['post'], url_path='rimuovi-oggetto')
    def rimuovi_oggetto(self, request, pk=None):
        """Toglie l'oggetto dall'inventario del personaggio (senza cancellarlo)."""
        personaggio = self.get_object()
        oggetto_id = request.data.get('oggetto_id')
        motivo = (request.data.get('motivo') or 'Rimozione staff').strip()
        if not oggetto_id:
            return Response({'detail': 'oggetto_id obbligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            oggetto = Oggetto.objects.get(pk=oggetto_id)
        except Oggetto.DoesNotExist:
            return Response({'detail': 'Oggetto non trovato.'}, status=status.HTTP_404_NOT_FOUND)
        if not self._oggetto_in_inventario_personaggio(personaggio, oggetto):
            return Response(
                {'detail': 'L\'oggetto non è nell\'inventario di questo personaggio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            oggetto.sposta_in_inventario(None)
            personaggio.aggiungi_log(f"Oggetto «{oggetto.nome}» rimosso dall'inventario ({motivo}).")
        return Response({'detail': f'«{oggetto.nome}» rimosso dall\'inventario (oggetto conservato).'})

    @action(detail=True, methods=['post'], url_path='distruggi-oggetto')
    def distruggi_oggetto(self, request, pk=None):
        """Elimina definitivamente un'istanza Oggetto dall'inventario del personaggio."""
        personaggio = self.get_object()
        oggetto_id = request.data.get('oggetto_id')
        motivo = (request.data.get('motivo') or 'Distruzione staff').strip()
        if not oggetto_id:
            return Response({'detail': 'oggetto_id obbligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            oggetto = Oggetto.objects.get(pk=oggetto_id)
        except Oggetto.DoesNotExist:
            return Response({'detail': 'Oggetto non trovato.'}, status=status.HTTP_404_NOT_FOUND)
        if not self._oggetto_in_inventario_personaggio(personaggio, oggetto):
            return Response(
                {'detail': 'L\'oggetto non è nell\'inventario di questo personaggio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        nome = oggetto.nome
        with transaction.atomic():
            if oggetto.is_equipaggiato:
                oggetto.is_equipaggiato = False
                oggetto.slot_equip = None
                oggetto.save(update_fields=['is_equipaggiato', 'slot_equip', 'updated_at'])
            oggetto.sposta_in_inventario(None)
            oggetto.delete()
            personaggio.aggiungi_log(f"Oggetto «{nome}» distrutto ({motivo}).")
        return Response({'detail': f'«{nome}» eliminato definitivamente.'})

    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        personaggio = self.get_object()
        from personaggi.serializers import PersonaggioLogSerializer
        qs = PersonaggioLog.objects.filter(personaggio=personaggio).order_by('-data')
        page = self.paginate_queryset(qs)
        ser = PersonaggioLogSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    @action(detail=True, methods=['post'], url_path='rigenera-like-influencer')
    def rigenera_like_influencer(self, request, pk=None):
        from social.influencer import RigeneraLikeInfluencerError, rigenera_like_personaggio
        personaggio = self.get_object()
        try:
            post_n, comment_n = rigenera_like_personaggio(personaggio)
        except RigeneraLikeInfluencerError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'detail': f'Like InstaFame rigenerati: {post_n} post, {comment_n} commenti.',
            'post_likes': post_n,
            'comment_likes': comment_n,
        })

    @action(detail=True, methods=['get'], url_path='creazione-guidata/riepilogo')
    def creazione_guidata_riepilogo(self, request, pk=None):
        from gestione_plot.creazione_guidata_helpers import _parse_effetti_param
        from personaggi.creazione_guidata_riepilogo import build_wizard_riepilogo
        personaggio = self.get_object()
        effetti = _parse_effetti_param(request.query_params.get('effetti'))
        return Response(build_wizard_riepilogo(personaggio, effetti))

    @action(detail=True, methods=['get'], url_path='creazione-guidata/proposte')
    def creazione_guidata_proposte(self, request, pk=None):
        from personaggi.creazione_guidata_proposte import load_wizard_proposte
        personaggio = self.get_object()
        effetti, trail = load_wizard_proposte(personaggio)
        return Response({'effetti': effetti, 'trail': trail})

    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        personaggio = self.get_object()
        titolo = (request.data.get('titolo') or '').strip()
        testo = (request.data.get('testo') or '').strip()
        if not titolo or not testo:
            return Response({'detail': 'Titolo e testo obbligatori.'}, status=status.HTTP_400_BAD_REQUEST)
        msg = Messaggio.objects.create(
            mittente=request.user,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            destinatario_personaggio=personaggio,
            titolo=titolo,
            testo=testo,
            campagna=personaggio.campagna,
            mostra_proprietario_giocatore=False,
        )
        return Response({'id': msg.id, 'detail': 'Messaggio inviato.'})


class RegolaTransazioneCategoriaStaffViewSet(viewsets.ModelViewSet):
    """Regole globali per scambi tra giocatori, per categoria e campagna attiva."""

    serializer_class = RegolaTransazioneCategoriaStaffSerializer
    permission_classes = [IsStaffOrMaster]
    pagination_class = None
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        from personaggi.regole_transazione import ensure_regole_transazione_campagna
        campagna = _get_active_campaign(self.request)
        if not campagna:
            return RegolaTransazioneCategoria.objects.none()
        ensure_regole_transazione_campagna(campagna)
        return RegolaTransazioneCategoria.objects.filter(campagna=campagna).order_by('ordine', 'codice')

    def partial_update(self, request, *args, **kwargs):
        allowed = {
            'vendibile_giocatori', 'requisiti_gruppo',
            'solo_posseduti', 'trasferimento_copia', 'rispetta_non_insegnabile',
        }
        payload = {k: v for k, v in request.data.items() if k in allowed}
        if not payload:
            return Response({'detail': 'Nessun campo aggiornabile.'}, status=status.HTTP_400_BAD_REQUEST)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        from personaggi.regole_transazione import REGOLA_TX_CODICI_CATALOGO_OBBLIGATORIO
        if instance.codice in REGOLA_TX_CODICI_CATALOGO_OBBLIGATORIO and not instance.solo_posseduti:
            instance.solo_posseduti = True
            instance.save(update_fields=['solo_posseduti', 'updated_at'])
        return Response(serializer.data)


class PersonaggioEliminatiStaffViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Personaggi archiviati (soft-delete). Solo master/head master possono
    ripristinarli o eliminarli definitivamente dal database.
    """

    serializer_class = PersonaggioEliminatoStaffSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def _master_queryset(self):
        from personaggi.views import _can_operate_in_campaign, _get_active_campaign, _get_default_campaign

        user = self.request.user
        active_campaign = _get_active_campaign(self.request)
        default_campaign = _get_default_campaign()
        if not _can_operate_in_campaign(user, active_campaign, needs_master=True) and not user.is_superuser:
            return Personaggio.all_objects.none()

        qs = (
            Personaggio.all_objects.filter(eliminato_at__isnull=False)
            .select_related("proprietario", "tipologia", "campagna")
            .order_by("-eliminato_at", "nome")
        )
        if active_campaign and default_campaign and active_campaign.id != default_campaign.id:
            qs = qs.filter(
                Q(campagna=active_campaign) | Q(campagna=default_campaign, tipologia__giocante=False)
            )
        elif active_campaign:
            qs = qs.filter(campagna=active_campaign)
        return qs

    def get_queryset(self):
        return self._master_queryset()

    def _ensure_master(self, personaggio):
        from personaggi.views import _can_operate_in_campaign

        user = self.request.user
        if user.is_superuser:
            return
        if not _can_operate_in_campaign(user, personaggio.campagna, needs_master=True):
            raise permissions.PermissionDenied("Solo i master possono gestire i personaggi eliminati.")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def restore(self, request, pk=None):
        personaggio = get_object_or_404(self._master_queryset(), pk=pk)
        self._ensure_master(personaggio)
        personaggio.eliminato_at = None
        personaggio.save(update_fields=["eliminato_at", "updated_at"])
        personaggio.aggiungi_log(f"Personaggio ripristinato da {request.user.username}.")
        serializer = self.get_serializer(personaggio)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="hard-delete")
    @transaction.atomic
    def hard_delete(self, request, pk=None):
        personaggio = get_object_or_404(self._master_queryset(), pk=pk)
        self._ensure_master(personaggio)
        nome = personaggio.nome
        personaggio_id = personaggio.pk
        personaggio.delete()
        return Response(
            {"ok": True, "message": f"Personaggio «{nome}» (id {personaggio_id}) eliminato definitivamente."},
            status=status.HTTP_200_OK,
        )