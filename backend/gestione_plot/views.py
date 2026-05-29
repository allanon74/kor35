from rest_framework import mixins, viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError

from django.shortcuts import get_object_or_404
import os
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape
from PIL import Image
import re
from pathlib import Path

from django.db.models import Prefetch
from django.db import transaction
import logging
from personaggi.models import (
    Abilita,
    Cerimoniale,
    Dichiarazione,
    Infusione,
    Inventario,
    Manifesto,
    Mattone,
    ModelloAura,
    Oggetto,
    Personaggio,
    Punteggio,
    QrCode,
    Tabella,
    Tessitura,
    Tier,
    TierPluginModel,
    Campagna,
    CampagnaUtente,
    CAMPAGNA_ROLE_REDACTOR,
    CAMPAGNA_ROLE_STAFFER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_HEAD_MASTER,
    Era,
    EraAbilita,
)

from personaggi.serializers import (
    InventarioSerializer, ManifestoSerializer, 
    PersonaggioListSerializer, PersonaggioAutocompleteSerializer, PersonaggioSerializer,
    TabellaSerializer, AbilitaSerializer, ModelloAuraSerializer,
    TessituraSerializer, InfusioneSerializer, CerimonialeSerializer, OggettoSerializer,
                                    )
from .models import (
    Evento, PaginaRegolamento, Quest, QuestMostro, QuestVista, GiornoEvento, MostroTemplate,
    PngAssegnato, StaffOffGame, QuestFase, QuestTask, WikiImmagine, WikiTierWidget,
    WikiTierCollectionWidget, WikiButtonWidget, WikiButton, WikiMattoniWidget,
    ConfigurazioneSito, LinkSocial, ManualePdf, ManualePdfBatchJob, ManualePdfGenerazione,
)
from .serializers import (
    EventoSerializer, EventoPubblicoSerializer, PaginaRegolamentoSerializer, PaginaRegolamentoSmallSerializer, QuestMostroSerializer, QuestVistaSerializer, 
    GiornoEventoSerializer, QuestSerializer, PngAssegnatoSerializer, 
    MostroTemplateSerializer, StaffOffGameSerializer, QuestFaseSerializer, QuestTaskSerializer, WikiImmagineSerializer, WikiTierWidgetSerializer, WikiTierCollectionWidgetSerializer, WikiButtonWidgetSerializer,
    ConfigurazioneSitoSerializer, LinkSocialSerializer, WikiTierSerializer, UserShortSerializer
    ,     WikiMattoniWidgetSerializer,
    MattoneWikiSerializer,
    PunteggioWikiSerializer,
    PublicDichiarazioneGlossarioSerializer,
    ManualePdfSerializer,
    PublicManualePdfSerializer,
    ManualePdfGenerazioneSerializer,
    ManualePdfBatchJobSerializer,
)
from .wiki_pdf import (
    build_manuale_html_for_request,
    generate_manuale_pdf,
    get_current_pdf_stile,
    wiki_manual_latest_path,
    wiki_manual_legacy_latest_path,
)
from .wiki_pdf_service import (
    BUNDLE_ZIP_NAME,
    build_manuali_zip_bundle,
    compute_wiki_pdf_diagnostica,
    create_batch_job,
    enqueue_batch_job,
    esegui_generazione_manuale,
    _triggered_by_email_from_request,
)


from django.contrib.auth.models import AnonymousUser, User

from .permissions import IsStaffOrMaster

logger = logging.getLogger(__name__)
WIDGET_TOKEN_RE = re.compile(r"{{WIDGET_([A-Z_]+):([A-Za-z0-9-]+)}}")

class IsMasterOrReadOnly(permissions.BasePermission):
    """
    Gli Staffer leggono e scrivono, gli utenti non staff non vedono nulla.
    """
    def has_permission(self, request, view):
        if not _is_campaign_staff_plus(request):
            return False
        # Permetti GET/HEAD/OPTIONS a tutto lo staff
        if request.method in permissions.SAFE_METHODS:
            return True
        # Scrittura solo a Master/Head Master/Admin
        return _is_campaign_master_plus(request)


def _is_campaign_wiki_editor_plus(request):
    if _is_global_admin(request.user):
        return True
    role = _campaign_role_for_request(request)
    return role in (
        CAMPAGNA_ROLE_REDACTOR,
        CAMPAGNA_ROLE_STAFFER,
        CAMPAGNA_ROLE_MASTER,
        CAMPAGNA_ROLE_HEAD_MASTER,
    )


class IsWikiEditorOrMasterForStaffOnly(permissions.BasePermission):
    """
    Regole wiki:
    - Player: nessun accesso ai CRUD staff wiki.
    - Redactor/Staffer/Master/Head Master/Admin: CRUD su pagine non staff-only.
    - Staff-only: CRUD solo Master/Head Master/Admin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return _is_campaign_wiki_editor_plus(request)

        # Create: valuta il flag staff-only nel payload.
        raw_staff_only = request.data.get("visibile_solo_staff", False)
        is_staff_only = str(raw_staff_only).strip().lower() in ("1", "true", "yes", "on")
        if is_staff_only:
            return _is_campaign_master_plus(request)
        return _is_campaign_wiki_editor_plus(request)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return _is_campaign_wiki_editor_plus(request)

        # Update/Delete su pagina staff-only riservati ai master-plus.
        if getattr(obj, "visibile_solo_staff", False):
            return _is_campaign_master_plus(request)
        return _is_campaign_wiki_editor_plus(request)

class EventoViewSet(viewsets.ModelViewSet):
    serializer_class = EventoSerializer
    permission_classes = [IsMasterOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        
        base_queryset = Evento.objects.all().prefetch_related(
            'iscrizione_opzioni',
            'giorni__quests__mostri_presenti',
            'giorni__quests__png_richiesti',
            'giorni__quests__viste_previste__manifesto',
            'giorni__quests__viste_previste__inventario',
            'giorni__quests__viste_previste__personaggio',
            'giorni__quests__viste_previste__oggetto',
            'giorni__quests__viste_previste__tessitura',
            'giorni__quests__viste_previste__infusione',
            'giorni__quests__viste_previste__cerimoniale',
            'giorni__quests__staff_offgame',
            'giorni__quests__fasi__tasks'
        )
        
        if user.is_superuser:
            return base_queryset
        return base_queryset.filter(staff_assegnato=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        role = _campaign_role_for_request(self.request)
        is_staffer_only = role == CAMPAGNA_ROLE_STAFFER and not _is_global_admin(self.request.user)
        context["plot_staffer_limited"] = bool(is_staffer_only)
        context["plot_staff_user_id"] = self.request.user.id if is_staffer_only else None
        return context

    @action(detail=True, methods=["post"])
    def inizia(self, request, pk=None):
        evento = self.get_object()
        if evento.started_at and not evento.ended_at:
            return Response({"detail": "Evento già in corso."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        with transaction.atomic():
            evento.started_at = now
            evento.ended_at = None
            evento.save(update_fields=["started_at", "ended_at", "updated_at"])
            from .evento_premi import applica_premio_presenza_personaggio

            premi_applicati = 0
            for pg in evento.partecipanti.all():
                if applica_premio_presenza_personaggio(evento, pg, when=now):
                    premi_applicati += 1
        return Response(
            {
                "ok": True,
                "evento_id": evento.id,
                "started_at": now,
                "premi_applicati": premi_applicati,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def termina(self, request, pk=None):
        evento = self.get_object()
        if not evento.started_at or evento.ended_at:
            return Response({"detail": "Evento non in corso."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        evento.ended_at = now
        evento.save(update_fields=["ended_at", "updated_at"])
        return Response(
            {
                "ok": True,
                "evento_id": evento.id,
                "ended_at": now,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def report_ricompense(self, request, pk=None):
        evento = self.get_object()
        from .evento_premi import report_ricompense_evento

        data = report_ricompense_evento(evento)
        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def a_vista_disponibili(self, request):
        """
        Restituisce TUTTI gli oggetti A_vista con tipo calcolato.
        """
        from personaggi.models import (
            A_vista, Personaggio, Inventario, Manifesto, 
            Oggetto, Tessitura, Infusione, Cerimoniale
        )
        
        risultati = []
        tipo_mapping = {
            'PG': 'Personaggio (PG)',
            'PNG': 'Personaggio Non Giocante (PNG)',
            'INV': 'Inventario',
            'OGG': 'Oggetto',
            'TES': 'Tessitura',
            'INF': 'Infusione',
            'CER': 'Cerimoniale',
            'MAN': 'Manifesto',
            'NEG': 'Negozio alternativo (QR)',
        }
        
        # Carica Personaggi con tipologia
        for p in Personaggio.objects.select_related('tipologia').all():
            tipo = 'PG' if (p.tipologia and p.tipologia.giocante) else 'PNG'
            risultati.append({
                'id': p.id,
                'nome': p.nome,
                'tipo': tipo,
                'tipo_display': tipo_mapping[tipo]
            })
        
        # Inventari NON personaggi (filtra usando personaggio__isnull=True)
        for inv in Inventario.objects.filter(personaggio__isnull=True):
            risultati.append({
                'id': inv.id,
                'nome': inv.nome,
                'tipo': 'INV',
                'tipo_display': tipo_mapping['INV']
            })
        
        # Manifesti
        for m in Manifesto.objects.all():
            risultati.append({
                'id': m.id,
                'nome': m.nome,
                'tipo': 'MAN',
                'tipo_display': tipo_mapping['MAN']
            })
        
        # Oggetti
        for o in Oggetto.objects.all():
            risultati.append({
                'id': o.id,
                'nome': o.nome,
                'tipo': 'OGG',
                'tipo_display': tipo_mapping['OGG']
            })
        
        # Tessiture
        for t in Tessitura.objects.all():
            risultati.append({
                'id': t.id,
                'nome': t.nome,
                'tipo': 'TES',
                'tipo_display': tipo_mapping['TES']
            })
        
        # Infusioni
        for i in Infusione.objects.all():
            risultati.append({
                'id': i.id,
                'nome': i.nome,
                'tipo': 'INF',
                'tipo_display': tipo_mapping['INF']
            })
        
        # Cerimoniali
        for c in Cerimoniale.objects.all():
            risultati.append({
                'id': c.id,
                'nome': c.nome,
                'tipo': 'CER',
                'tipo_display': tipo_mapping['CER']
            })

        from personaggi.negozio_mercante_models import NEGOZIO_TIPO_ALTERNATIVO, NegozioMercante

        for n in NegozioMercante.objects.filter(tipo_negozio=NEGOZIO_TIPO_ALTERNATIVO).order_by('nome'):
            risultati.append({
                'id': str(n.id),
                'nome': n.nome,
                'tipo': 'NEG',
                'tipo_display': 'Negozio alternativo (QR)',
            })
        
        return Response({'a_vista': risultati})
    
    def _negozi_mercante_risorse_editor(self):
        from personaggi.negozio_mercante_models import NEGOZIO_TIPO_ALTERNATIVO, NegozioMercante
        from personaggi.negozio_mercante_readiness import valuta_prontezza_negozio

        out = []
        for n in NegozioMercante.objects.filter(tipo_negozio=NEGOZIO_TIPO_ALTERNATIVO).order_by('nome'):
            out.append({
                'id': str(n.id),
                'nome': n.nome,
                'qr_code': n.qr_code_id,
                'readiness': valuta_prontezza_negozio(n),
            })
        return out

    @action(detail=False, methods=['get'])
    def risorse_editor(self, request):
        """
        Versione ottimizzata e filtrata.
        Esclude inventari di Personaggi/PnG e carica solo i dati minimi.
        Ottimizzato con select_related e only() per ridurre le query.
        """
        try:
            # Ottimizzazione: select_related per evitare N+1 queries
            # NOTA: 'crediti' e 'punti_caratteristica' sono @property, non vanno in only()
            png_queryset = Personaggio.objects.select_related(
                'tipologia', 'proprietario'
            ).only(
                'id', 'nome', 'testo', 'costume', 'data_nascita', 'data_morte',
                'tipologia', 'proprietario'
            )
            
            # Filtra inventari per escludere personaggi (che ereditano da Inventario)
            inventari_non_personaggi = Inventario.objects.filter(
                personaggio__isnull=True
            ).only('id', 'nome')
            
            # Oggetti: serializza solo id e nome per performance
            oggetti_data = [{'id': o.id, 'nome': o.nome} for o in Oggetto.objects.only('id', 'nome')]
            
            return Response({
                'png': PersonaggioSerializer(png_queryset, many=True).data,
                'templates': MostroTemplateSerializer(MostroTemplate.objects.all(), many=True).data,
                'manifesti': ManifestoSerializer(Manifesto.objects.all(), many=True).data,
                'inventari': InventarioSerializer(inventari_non_personaggi, many=True).data,
                'tessiture': TessituraSerializer(Tessitura.objects.all().select_related('aura_richiesta', 'elemento_principale'), many=True).data,
                'infusioni': InfusioneSerializer(Infusione.objects.all().select_related('aura_richiesta', 'aura_infusione'), many=True).data,
                'cerimoniali': CerimonialeSerializer(Cerimoniale.objects.all(), many=True).data,
                'oggetti': oggetti_data,
                'staff': UserShortSerializer(User.objects.filter(is_staff=True).only('id', 'username', 'first_name', 'last_name'), many=True).data,
                'negozi_mercante': self._negozi_mercante_risorse_editor(),
            })
        except Exception:
            logger.exception("Errore nel caricamento risorse editor plot")
            return Response(
                {'detail': 'Errore interno durante il caricamento delle risorse editor.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GiornoEventoViewSet(viewsets.ModelViewSet):
    queryset = GiornoEvento.objects.all()
    serializer_class = GiornoEventoSerializer
    permission_classes = [IsMasterOrReadOnly]

class QuestViewSet(viewsets.ModelViewSet):
    serializer_class = QuestSerializer
    permission_classes = [IsMasterOrReadOnly]
    
    def get_queryset(self):
        return Quest.objects.all().prefetch_related(
            'mostri_presenti',
            'png_richiesti',
            'viste_previste__manifesto',
            'viste_previste__inventario',
            'viste_previste__personaggio',
            'viste_previste__oggetto',
            'viste_previste__tessitura',
            'viste_previste__infusione',
            'viste_previste__cerimoniale',
            'staff_offgame',
            'fasi__tasks'
        )

class QuestMostroViewSet(viewsets.ModelViewSet):
    """
    Gestione istanze mostri. Permette di aggiornare PV/Armatura in tempo reale.
    """
    queryset = QuestMostro.objects.all()
    serializer_class = QuestMostroSerializer
    permission_classes = [IsStaffOrMaster]

    @action(detail=True, methods=['post'])
    def modifica_hp(self, request, pk=None):
        mostro = self.get_object()
        delta = request.data.get('delta', 0) # Es: +1 o -1
        mostro.punti_vita = max(0, mostro.punti_vita + int(delta))
        mostro.save()
        return Response({'status': 'ok', 'punti_vita': mostro.punti_vita})

class QuestVistaViewSet(viewsets.ModelViewSet):
    queryset = QuestVista.objects.all()
    serializer_class = QuestVistaSerializer
    permission_classes = [IsStaffOrMaster]
    
    def perform_create(self, serializer):
        """
        Gestisce la creazione intelligente: riceve a_vista_id e tipo,
        e assegna al campo FK corretto cercando nel modello specifico.
        """
        from personaggi.models import (
            Personaggio, Inventario, Manifesto, 
            Oggetto, Tessitura, Infusione, Cerimoniale
        )
        from personaggi.negozio_mercante_models import NegozioMercante
        
        a_vista_id = self.request.data.get('a_vista_id') or self.request.data.get('contentId')
        tipo = self.request.data.get('tipo')
        
        if not a_vista_id:
            raise ValidationError({'error': 'a_vista_id o contentId richiesto'})
        
        # Mappa tipo -> (modello, campo FK)
        type_mapping = {
            'PG': (Personaggio, 'personaggio'),
            'PNG': (Personaggio, 'personaggio'),
            'INV': (Inventario, 'inventario'),
            'OGG': (Oggetto, 'oggetto'),
            'TES': (Tessitura, 'tessitura'),
            'INF': (Infusione, 'infusione'),
            'CER': (Cerimoniale, 'cerimoniale'),
            'MAN': (Manifesto, 'manifesto'),
            'NEG': (NegozioMercante, 'negozio_mercante'),
        }
        
        if tipo not in type_mapping:
            raise ValidationError({'error': f'Tipo non valido: {tipo}'})
        
        model_class, field_name = type_mapping[tipo]
        
        try:
            vista_obj = model_class.objects.get(id=a_vista_id)
        except model_class.DoesNotExist:
            raise ValidationError({'error': f'{tipo} con id {a_vista_id} non trovato'})
        
        # Salva con il campo FK appropriato
        serializer.save(**{field_name: vista_obj})

    @action(detail=True, methods=['post'])
    def associa_qr(self, request, pk=None):
        """
        FUNZIONE CRUCIALE: Associa un QR fisico scansionato a questa vista prevista.
        Se force=true, disassocia il QR dall'elemento precedente.
        Per tipo NEG collega il QR al NegozioMercante (scan apre il negozio, non A_vista).
        """
        vista_quest = self.get_object()
        qr_id = request.data.get('qr_id')
        force = request.data.get('force', False)
        
        try:
            qr = QrCode.objects.get(id=qr_id)

            if vista_quest.tipo == 'NEG' and vista_quest.negozio_mercante_id:
                return self._associa_qr_negozio_mercante(vista_quest, qr, force)

            # CONTROLLO: Se il QR è già associato ad un'altra vista, avvisa l'utente
            if qr.vista and not force:
                from personaggi.qr_logic import descrivi_avista_per_associazione_qr

                info = descrivi_avista_per_associazione_qr(qr.vista) or {
                    "tipo": "a_vista",
                    "nome": qr.vista.nome,
                    "elemento_id": str(qr.vista.pk),
                }
                return Response(
                    {
                        "error": "QR già associato",
                        "already_associated": True,
                        "qr_id": str(qr.id),
                        "associazione_attuale": info,
                        "current_vista": {
                            "id": info.get("elemento_id"),
                            "nome": info.get("nome"),
                            "tipo": info.get("tipo"),
                        },
                        "message": (
                            f'Questo QR è già associato a «{info["nome"]}» ({info["tipo"]}). '
                            "Confermi di volerlo spostare su questa vista di quest?"
                        ),
                    },
                    status=409,
                )
            
            # Colleghiamo il QR alla "Vista" appropriata in base al tipo
            target_vista = (vista_quest.manifesto or vista_quest.inventario or 
                          vista_quest.personaggio or vista_quest.oggetto or
                          vista_quest.tessitura or vista_quest.infusione or 
                          vista_quest.cerimoniale)
            
            if not target_vista:
                return Response({'error': 'Nessun contenuto definito per questa vista'}, status=400)
            
            # Aggiorniamo il QR Code reale nel database dei personaggi
            qr.vista = target_vista
            qr.save()
            
            # Salviamo il riferimento anche nel plot per tracciamento
            vista_quest.qr_code = qr
            vista_quest.save()
            
            return Response({'status': 'success', 'content': str(target_vista)})
        except QrCode.DoesNotExist:
            return Response({'error': 'QR Code non trovato'}, status=404)

    def _associa_qr_negozio_mercante(self, vista_quest, qr, force):
        from personaggi.negozio_mercante_avista import associa_qr_a_negozio

        negozio = vista_quest.negozio_mercante
        if not negozio:
            return Response({'error': 'Nessun negozio collegato a questa vista'}, status=400)

        ok, conflict = associa_qr_a_negozio(negozio, qr, force=force)
        if not ok:
            return Response(conflict, status=409)

        vista_quest.qr_code = qr
        vista_quest.save(update_fields=['qr_code', 'updated_at'])
        return Response({'status': 'success', 'content': negozio.nome, 'tipo': 'negozio_mercante'})
        
class MostroTemplateViewSet(viewsets.ModelViewSet): # Cambiato da ReadOnlyModelViewSet a ModelViewSet
    queryset = MostroTemplate.objects.all().prefetch_related('attacchi')
    serializer_class = MostroTemplateSerializer
    permission_classes = [IsStaffOrMaster]

class PngAssegnatoViewSet(viewsets.ModelViewSet):
    queryset = PngAssegnato.objects.all()
    serializer_class = PngAssegnatoSerializer
    permission_classes = [IsMasterOrReadOnly]
    
class StaffOffGameViewSet(viewsets.ModelViewSet):
    queryset = StaffOffGame.objects.all()
    serializer_class = StaffOffGameSerializer
    
class QuestFaseViewSet(viewsets.ModelViewSet):
    queryset = QuestFase.objects.all()
    serializer_class = QuestFaseSerializer
    permission_classes = [permissions.IsAuthenticated]

class QuestTaskViewSet(viewsets.ModelViewSet):
    queryset = QuestTask.objects.all()
    serializer_class = QuestTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Logica automatica per mostri: le stats vengono già gestite nel model.save()
        serializer.save()

class PaginaRegolamentoViewSet(viewsets.ModelViewSet):
    queryset = PaginaRegolamento.objects.all()
    serializer_class = PaginaRegolamentoSerializer
    permission_classes = [IsWikiEditorOrMasterForStaffOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _manuali_pdf_ids_from_request(self):
        if not hasattr(self.request.data, 'getlist'):
            return None
        if 'manuali_pdf' not in self.request.data and not self.request.data.getlist('manuali_pdf'):
            return None
        raw = self.request.data.getlist('manuali_pdf')
        if raw == [''] or (len(raw) == 1 and raw[0] == ''):
            return []
        return [int(x) for x in raw if str(x).strip().isdigit()]

    def perform_create(self, serializer):
        manuali_ids = self._manuali_pdf_ids_from_request()
        instance = serializer.save()
        if manuali_ids is not None:
            instance.manuali_pdf.set(manuali_ids)

    def perform_update(self, serializer):
        manuali_ids = self._manuali_pdf_ids_from_request()
        instance = serializer.save()
        if manuali_ids is not None:
            instance.manuali_pdf.set(manuali_ids)


class ManualePdfViewSet(viewsets.ModelViewSet):
    queryset = ManualePdf.objects.all().order_by('ordine', 'titolo')
    serializer_class = ManualePdfSerializer
    permission_classes = [IsWikiEditorOrMasterForStaffOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'slug'
    pagination_class = None

    @action(detail=True, methods=['post'], url_path='genera')
    def genera(self, request, slug=None):
        manuale = self.get_object()
        try:
            log = esegui_generazione_manuale(
                manuale,
                request,
                _render_wiki_widgets_for_pdf,
                triggered_by_email=_triggered_by_email_from_request(request),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ImportError:
            return Response(
                {"detail": "Servizio PDF non disponibile: dipendenze di rendering mancanti nel container."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Errore generazione manuale PDF %s", slug)
            return Response({"detail": "Errore durante la generazione del PDF."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        manuale.refresh_from_db()
        serializer = self.get_serializer(manuale)
        return Response(
            {
                "ok": True,
                "generated_at": manuale.ultimo_generato_at.isoformat() if manuale.ultimo_generato_at else None,
                "download_url": serializer.data.get('download_url'),
                "path": log.file_path,
                "generazione": ManualePdfGenerazioneSerializer(log).data,
                "manuale": serializer.data,
            }
        )

    @action(detail=True, methods=['get'], url_path='storico')
    def storico(self, request, slug=None):
        manuale = self.get_object()
        qs = ManualePdfGenerazione.objects.filter(manuale=manuale).order_by('-generato_at')[:50]
        return Response(ManualePdfGenerazioneSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='diagnostica')
    def diagnostica(self, request):
        return Response(compute_wiki_pdf_diagnostica())

    @action(detail=False, methods=['get'], url_path='export-zip')
    def export_zip(self, request):
        try:
            zip_path = build_manuali_zip_bundle()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(open(zip_path, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{BUNDLE_ZIP_NAME}"'
        return response

    @action(detail=False, methods=['post'], url_path='genera-tutti')
    def genera_tutti(self, request):
        try:
            job = create_batch_job(triggered_by_email=_triggered_by_email_from_request(request))
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        enqueue_batch_job(job, request.get_host(), _render_wiki_widgets_for_pdf)
        return Response(
            ManualePdfBatchJobSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=['get'], url_path=r'jobs/(?P<job_id>[0-9]+)')
    def job_status(self, request, job_id=None):
        job = get_object_or_404(ManualePdfBatchJob, pk=job_id)
        return Response(ManualePdfBatchJobSerializer(job).data)

    @action(detail=True, methods=['get'], url_path='anteprima')
    def anteprima(self, request, slug=None):
        """Anteprima HTML del manuale (stesso markup del PDF)."""
        manuale = self.get_object()
        try:
            html = build_manuale_html_for_request(
                manuale,
                request,
                render_content_fn=_render_wiki_widgets_for_pdf,
                force_public=True,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class PublicManualePdfViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ManualePdf.objects.filter(attivo=True).order_by('ordine', 'titolo')
    serializer_class = PublicManualePdfSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    pagination_class = None


class PaginaRegolamentoSmallViewSet(viewsets.ModelViewSet):
    queryset = PaginaRegolamento.objects.all()
    serializer_class = PaginaRegolamentoSmallSerializer
    permission_classes = [permissions.IsAuthenticated]
    

# ViewSet per il Menu (solo titoli e struttura) - PUBBLICO
class PublicPaginaRegolamentoMenu(viewsets.ReadOnlyModelViewSet):
    queryset = PaginaRegolamento.objects.filter(public=True).order_by('ordine', 'titolo')
    serializer_class = PaginaRegolamentoSmallSerializer
    permission_classes = [permissions.AllowAny] # Aperto a tutti
    pagination_class = None # Il menu lo vogliamo tutto in una volta

# ViewSet per il Contenuto Pagina - PUBBLICO
class PublicPaginaRegolamentoDetail(viewsets.ReadOnlyModelViewSet):
    queryset = PaginaRegolamento.objects.filter(public=True)
    serializer_class = PaginaRegolamentoSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug' # Importante: cerchiamo per slug, non per ID
    
class PublicTabellaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone le Tabelle (es. Liste Abilità) per il regolamento pubblico.
    """
    queryset = Tabella.objects.all()
    serializer_class = TabellaSerializer
    permission_classes = [permissions.AllowAny] # <--- FONDAMENTALE: Accesso pubblico!

class PublicAuraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone le Aure per il regolamento pubblico.
    """
    queryset = ModelloAura.objects.all()
    serializer_class = ModelloAuraSerializer
    permission_classes = [permissions.AllowAny]
    
class PublicTierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone i Tier (es. Livello 1, Livello 2...) con le relative abilità.
    """
    _abilita_prefetch = Prefetch('abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
    queryset = Tier.objects.all().prefetch_related(_abilita_prefetch)
    serializer_class = WikiTierSerializer
    permission_classes = [permissions.AllowAny] # Accesso pubblic

class PublicEventiViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone gli eventi pubblici per la homepage.
    Mostra solo gli eventi futuri o recenti (ultimi 30 giorni).
    """
    serializer_class = EventoPubblicoSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        from django.utils import timezone
        from datetime import timedelta
        
        # Data di oggi e data limite per eventi passati (30 giorni fa)
        oggi = timezone.now()
        trenta_giorni_fa = oggi - timedelta(days=30)
        
        # Restituisce eventi che:
        # - Sono nel futuro (data_inizio >= oggi), O
        # - Sono finiti da meno di 30 giorni (data_fine >= 30 giorni fa)
        return Evento.objects.filter(
            data_fine__gte=trenta_giorni_fa
        ).order_by('data_inizio')

class PublicConfigurazioneSitoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone la configurazione del sito (info associazione per widget Chi Siamo).
    Singleton - restituisce sempre il record con pk=1.
    """
    serializer_class = ConfigurazioneSitoSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Assicura che il record esista
        ConfigurazioneSito.get_config()
        return ConfigurazioneSito.objects.all()


def _is_campaign_head_master_plus(request, user_override=None):
    user = user_override if user_override is not None else request.user
    if _is_global_admin(user):
        return True
    role = _campaign_role_for_request(request, user_override=user)
    return role == CAMPAGNA_ROLE_HEAD_MASTER


class StaffDashboardLayoutView(APIView):
    """
    Layout globale menu Dashboard Staff.
    GET: qualsiasi staff campagna; PATCH: Head Master o superuser.
    """

    permission_classes = [IsAuthenticated]

    def _deny_not_staff(self, request):
        if not _is_campaign_staff_plus(request):
            return Response({"detail": "Accesso riservato allo staff."}, status=403)
        return None

    def get(self, request):
        denied = self._deny_not_staff(request)
        if denied is not None:
            return denied
        from .staff_dashboard_layout import effective_staff_dashboard_layout
        config = ConfigurazioneSito.get_config()
        return Response({
            "staff_dashboard_layout": effective_staff_dashboard_layout(config.staff_dashboard_layout),
        })

    def patch(self, request):
        denied = self._deny_not_staff(request)
        if denied is not None:
            return denied
        if not _is_campaign_head_master_plus(request):
            return Response(
                {"detail": "Solo Head Master o admin globale possono modificare il layout."},
                status=403,
            )
        from .serializers import StaffDashboardLayoutSerializer
        serializer = StaffDashboardLayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = ConfigurazioneSito.get_config()
        config.staff_dashboard_layout = serializer.validated_data["staff_dashboard_layout"]
        config.save(update_fields=["staff_dashboard_layout", "ultima_modifica"])
        return Response(serializer.validated_data)


class AdminMaintenanceConfigView(APIView):
    """
    Console maintenance mode riservata ai soli superuser Django.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def _ensure_superuser(self, request):
        if not bool(request.user and request.user.is_superuser):
            return Response({"detail": "Accesso riservato agli admin generali Django."}, status=403)
        return None

    def get(self, request):
        denied = self._ensure_superuser(request)
        if denied is not None:
            return denied
        config = ConfigurazioneSito.get_config()
        data = ConfigurazioneSitoSerializer(config).data
        return Response(data)

    def patch(self, request):
        denied = self._ensure_superuser(request)
        if denied is not None:
            return denied
        config = ConfigurazioneSito.get_config()
        serializer = ConfigurazioneSitoSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PublicLinkSocialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone i link social attivi per il widget Social.
    """
    serializer_class = LinkSocialSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Restituisce solo i link attivi, ordinati per 'ordine'
        return LinkSocial.objects.filter(attivo=True).order_by('ordine', 'tipo')


class PublicWikiGlossarioViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Glossario dichiarazioni (termini nel testo wiki → link a definizioni in fondo pagina).
    Solo lista: nessun dettaglio per id DB.
    """

    queryset = Dichiarazione.objects.all().order_by('tipo', 'nome')
    serializer_class = PublicDichiarazioneGlossarioSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response['Cache-Control'] = 'public, max-age=86400'
        return response


class PublicWikiImmagineViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone le immagini wiki per l'uso nei widget.
    Accesso pubblico in lettura.
    """
    queryset = WikiImmagine.objects.all()
    serializer_class = WikiImmagineSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_context(self):
        """Aggiunge il request al contesto per generare URL assoluti"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class StaffWikiImmagineViewSet(viewsets.ModelViewSet):
    """
    ViewSet per la gestione CRUD delle immagini wiki (solo staff).
    Permette di creare, modificare ed eliminare immagini.
    """
    queryset = WikiImmagine.objects.all()
    serializer_class = WikiImmagineSerializer
    permission_classes = [IsMasterOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Supporta upload file con FormData
    
    def get_serializer_context(self):
        """Aggiunge il request al contesto per generare URL assoluti"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        """Imposta automaticamente il creatore quando viene creata un'immagine"""
        serializer.save(creatore=self.request.user)
    

class PublicWikiTierWidgetViewSet(viewsets.ReadOnlyModelViewSet):
    """Espone i widget Tier per l'uso nelle pagine wiki (lettura)."""
    _abilita_prefetch = Prefetch('tier__abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
    _caratt_prefetch = Prefetch('tier__caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
    queryset = WikiTierWidget.objects.all().select_related('tier').prefetch_related(_abilita_prefetch, _caratt_prefetch)
    serializer_class = WikiTierWidgetSerializer
    permission_classes = [permissions.AllowAny]


class StaffWikiTierWidgetViewSet(viewsets.ModelViewSet):
    """CRUD widget Tier (solo staff)."""
    queryset = WikiTierWidget.objects.all().select_related('tier')
    serializer_class = WikiTierWidgetSerializer
    permission_classes = [IsMasterOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(creatore=self.request.user)


class PublicWikiTierCollectionWidgetViewSet(viewsets.ReadOnlyModelViewSet):
    """Espone i widget collezione tier per l'uso nelle pagine wiki (lettura)."""
    queryset = WikiTierCollectionWidget.objects.all().prefetch_related('widgets__tier')
    serializer_class = WikiTierCollectionWidgetSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class StaffWikiTierCollectionWidgetViewSet(viewsets.ModelViewSet):
    """CRUD widget collezione tier (solo staff)."""
    queryset = WikiTierCollectionWidget.objects.all().prefetch_related('widgets__tier')
    serializer_class = WikiTierCollectionWidgetSerializer
    permission_classes = [IsMasterOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(creatore=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class PublicWikiMattoniWidgetViewSet(viewsets.ReadOnlyModelViewSet):
    """Espone i widget Mattoni per l'uso nelle pagine wiki (lettura)."""
    queryset = WikiMattoniWidget.objects.all().prefetch_related('aure', 'caratteristiche')
    serializer_class = WikiMattoniWidgetSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class StaffWikiMattoniWidgetViewSet(viewsets.ModelViewSet):
    """CRUD widget Mattoni (solo staff)."""
    queryset = WikiMattoniWidget.objects.all().prefetch_related('aure', 'caratteristiche')
    serializer_class = WikiMattoniWidgetSerializer
    permission_classes = [IsMasterOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(creatore=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class PublicWikiButtonWidgetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone i widget pulsanti per l'uso nelle pagine wiki.
    Accesso pubblico in lettura.
    """
    queryset = WikiButtonWidget.objects.all().prefetch_related('buttons')
    serializer_class = WikiButtonWidgetSerializer
    permission_classes = [permissions.AllowAny]


class StaffWikiButtonWidgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet per la gestione CRUD dei widget pulsanti (solo staff).
    Permette di creare, modificare ed eliminare widget pulsanti.
    """
    queryset = WikiButtonWidget.objects.all().prefetch_related('buttons')
    serializer_class = WikiButtonWidgetSerializer
    permission_classes = [IsMasterOrReadOnly]
    
    def perform_create(self, serializer):
        """Imposta il creatore al momento della creazione"""
        serializer.save(creatore=self.request.user)
    
    def perform_update(self, serializer):
        """Mantiene il creatore originale durante l'aggiornamento"""
        # Il creatore non viene modificato, viene mantenuto quello originale
        serializer.save()
    
    
def _get_active_campaign_for_request(request):
    slug = (request.headers.get("X-Campagna") or request.query_params.get("campagna") or "kor35").strip().lower()
    campagna = Campagna.objects.filter(slug=slug, attiva=True).first()
    if campagna:
        return campagna
    return Campagna.objects.filter(attiva=True, is_default=True).first() or Campagna.objects.filter(slug="kor35").first()


def _campaign_role_for_request(request, user_override=None):
    user = user_override if user_override is not None else request.user
    if not (user and user.is_authenticated):
        return None
    campagna = _get_active_campaign_for_request(request)
    if not campagna:
        return None
    return (
        CampagnaUtente.objects.filter(user=user, campagna=campagna, attivo=True)
        .values_list("ruolo", flat=True)
        .first()
    )


def _is_global_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def _is_campaign_staff_plus(request, user_override=None):
    user = user_override if user_override is not None else request.user
    if _is_global_admin(user):
        return True
    role = _campaign_role_for_request(request, user_override=user)
    return role in (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def _is_campaign_master_plus(request, user_override=None):
    user = user_override if user_override is not None else request.user
    if _is_global_admin(user):
        return True
    role = _campaign_role_for_request(request, user_override=user)
    return role in (CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def _can_view_unpublished_non_staff_wiki(request, user_override=None):
    user = user_override if user_override is not None else request.user
    if _is_global_admin(user):
        return True
    role = _campaign_role_for_request(request, user_override=user)
    return role in (CAMPAGNA_ROLE_REDACTOR, CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def _public_wiki_effective_user(request):
    """
    Hardening endpoint pubblici wiki:
    considera privilegi staff solo con token API esplicito.
    Le sessioni cookie implicite (es. admin Django aperto) non elevano i permessi.
    """
    auth_header = (request.headers.get("Authorization") or "").strip()
    has_token_header = auth_header.lower().startswith("token ")
    if has_token_header and request.user and request.user.is_authenticated:
        return request.user
    return AnonymousUser()

def _resolve_by_pk_or_sync_id(qs, raw_key):
    """
    Accetta token wiki in formato legacy (id numerico) o stabile (sync_id UUID).
    """
    key = str(raw_key).strip()
    if not key:
        return None
    if key.isdigit():
        return qs.filter(pk=int(key)).first()
    return qs.filter(sync_id=key).first()


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_tier_display(request, key):
    """
    Restituisce i dati di un Tier per {{WIDGET_TIER:id}}.
    Ordine: 1) WikiTierWidget (id widget), 2) Tier (id tier), 3) plugin CMS.
    """
    tier = None
    extra = {}
    # 1) WikiTierWidget (widget configurabile)
    _abilita_prefetch = Prefetch('tier__abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
    _caratt_prefetch = Prefetch('tier__caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
    widget = _resolve_by_pk_or_sync_id(
        WikiTierWidget.objects.select_related('tier').prefetch_related(_abilita_prefetch, _caratt_prefetch),
        key,
    )
    if widget:
        tier = widget.tier
        extra = {
            'abilities_collapsible': widget.abilities_collapsible,
            'abilities_collapsed_by_default': widget.abilities_collapsed_by_default,
            'abilities_solo_list': getattr(widget, 'abilities_solo_list', False),
            'show_runtime_filters': getattr(widget, 'show_runtime_filters', False),
            'show_description': widget.show_description,
            'color_style': widget.color_style or 'default',
            'gradient_colors': getattr(widget, 'gradient_colors', []) or [],
        }
    if not tier:
        _pf = Prefetch('abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
        _pf_car = Prefetch('caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
        tier = _resolve_by_pk_or_sync_id(
            Tier.objects.prefetch_related(_pf, _pf_car),
            key,
        )
        if tier:
            extra = {
                'abilities_collapsible': True,
                'abilities_collapsed_by_default': False,
                'abilities_solo_list': False,
                'show_runtime_filters': False,
                'show_description': True,
                'color_style': 'default',
            }
    if not tier:
        # Plugin in personaggi
        plugin = _resolve_by_pk_or_sync_id(
            TierPluginModel.objects.select_related('tier'),
            key,
        )
        if plugin:
            _pf = Prefetch('abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
            _pf_car = Prefetch('caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
            tier = Tier.objects.filter(pk=plugin.tier_id).prefetch_related(_pf, _pf_car).first()
            if tier:
                extra = {
                    'abilities_collapsible': True,
                    'abilities_collapsed_by_default': False,
                    'abilities_solo_list': False,
                    'show_runtime_filters': False,
                    'show_description': True,
                    'color_style': 'default',
                }
    if not tier:
        # Plugin in cms_kor (stesso nome modello, altra app)
        try:
            from cms_kor.models import TierPluginModel as CmsKorTierPluginModel
            plugin = _resolve_by_pk_or_sync_id(
                CmsKorTierPluginModel.objects.select_related('tier'),
                key,
            )
            if plugin:
                _pf = Prefetch('abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
                _pf_car = Prefetch('caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
                tier = Tier.objects.filter(pk=plugin.tier_id).prefetch_related(_pf, _pf_car).first()
                if tier:
                    extra = {
                        'abilities_collapsible': True,
                        'abilities_collapsed_by_default': False,
                        'abilities_solo_list': False,
                        'show_runtime_filters': False,
                        'show_description': True,
                        'color_style': 'default',
                    }
        except Exception:
            pass
    if not tier:
        # Fallback: qualsiasi CMSPlugin con questo pk che abbia un FK tier (get_plugin_instance)
        try:
            from cms.models.pluginmodel import CMSPlugin
            cms_plugin = _resolve_by_pk_or_sync_id(
                CMSPlugin.objects.all(),
                key,
            )
            if cms_plugin:
                instance, _ = cms_plugin.get_plugin_instance()
                _pf = Prefetch('abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3'))
                _pf_car = Prefetch('caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
                if instance and getattr(instance, 'tier_id', None):
                    tier = Tier.objects.filter(pk=instance.tier_id).prefetch_related(_pf, _pf_car).first()
                elif instance and getattr(instance, 'tier', None):
                    tier = Tier.objects.filter(pk=instance.tier.pk).prefetch_related(_pf, _pf_car).first()
                if tier:
                    extra = {
                        'abilities_collapsible': True,
                        'abilities_collapsed_by_default': False,
                        'abilities_solo_list': False,
                        'show_runtime_filters': False,
                        'show_description': True,
                        'color_style': 'default',
                    }
        except Exception:
            pass
    if not tier:
        raise Http404("No Tier matches the given query.")
    data = WikiTierSerializer(tier).data
    data["sync_id"] = str(getattr(tier, "sync_id", "") or "")
    data.update(extra)
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_tier_collection_display(request, key):
    """
    Restituisce una collezione di widget tier pronta per il rendering in wiki.
    Supporta filtri/sort persistenti da configurazione widget.
    """
    widget = _resolve_by_pk_or_sync_id(
        WikiTierCollectionWidget.objects.prefetch_related('widgets__tier', 'widgets__tier__caratteristiche_visibili', 'caratteristiche'),
        key,
    )
    if not widget:
        raise Http404("No WikiTierCollectionWidget matches the given query.")

    if widget.source_mode == WikiTierCollectionWidget.SOURCE_SELECTED:
        qs = widget.widgets.all().select_related('tier').prefetch_related('tier__caratteristiche_visibili')
    else:
        qs = WikiTierWidget.objects.all().select_related('tier').prefetch_related('tier__caratteristiche_visibili')

    tier_type_filter = (widget.tier_type_filter or WikiTierCollectionWidget.TIER_TYPE_ALL).strip().lower()
    if tier_type_filter and tier_type_filter != WikiTierCollectionWidget.TIER_TYPE_ALL:
        qs = qs.filter(tier__tipo=tier_type_filter.upper())

    car_ids = list(widget.caratteristiche.values_list('id', flat=True))
    car_mode = widget.caratteristiche_filter_mode or WikiTierCollectionWidget.CAR_FILTER_ANY
    if car_ids:
        if car_mode == WikiTierCollectionWidget.CAR_FILTER_ALL:
            for car_id in car_ids:
                qs = qs.filter(tier__caratteristiche_visibili__id=car_id)
        else:
            qs = qs.filter(tier__caratteristiche_visibili__id__in=car_ids)
        qs = qs.distinct()

    sort_by = widget.sort_by or WikiTierCollectionWidget.SORT_TIER_NAME
    sort_dir = widget.sort_dir or WikiTierCollectionWidget.SORT_ASC
    is_desc = sort_dir == WikiTierCollectionWidget.SORT_DESC
    if sort_by == WikiTierCollectionWidget.SORT_WIDGET_CREATED:
        order_expr = '-data_creazione' if is_desc else 'data_creazione'
    else:
        order_expr = '-tier__nome' if is_desc else 'tier__nome'
    qs = qs.order_by(order_expr, 'id')

    items = [
        {
            'id': w.id,
            'sync_id': str(w.sync_id) if getattr(w, 'sync_id', None) else None,
            'tier_id': w.tier_id,
            'tier_nome': w.tier.nome if w.tier_id else '',
            'tier_tipo': getattr(w.tier, 'tipo', ''),
            'tier_caratteristiche': list(
                w.tier.caratteristiche_visibili.all()
                .order_by('ordine', 'nome')
                .values('id', 'nome', 'sigla', 'colore', 'ordine')
            ),
            'token': str(w.sync_id) if getattr(w, 'sync_id', None) else str(w.id),
        }
        for w in qs
    ]
    available_char_ids = {c['id'] for item in items for c in item.get('tier_caratteristiche', [])}
    caratteristiche_available = list(
        Punteggio.objects.filter(tipo='CA', id__in=available_char_ids)
        .order_by('ordine', 'nome')
        .values('id', 'nome', 'sigla', 'colore', 'ordine')
    )
    payload = {
        'id': widget.id,
        'sync_id': str(widget.sync_id) if getattr(widget, 'sync_id', None) else None,
        'title': widget.title or '',
        'source_mode': widget.source_mode,
        'tier_type_filter': widget.tier_type_filter,
        'sort_by': widget.sort_by,
        'sort_dir': widget.sort_dir,
        'caratteristiche_filter_mode': widget.caratteristiche_filter_mode,
        'show_runtime_filters': bool(widget.show_runtime_filters),
        'show_search_control': bool(widget.show_search_control),
        'show_tier_type_control': bool(widget.show_tier_type_control),
        'show_characteristics_control': bool(widget.show_characteristics_control),
        'show_sort_controls': bool(widget.show_sort_controls),
        'badge_mode': widget.badge_mode or 'compact',
        'can_manage_runtime_controls': bool(_is_campaign_wiki_editor_plus(request)),
        'caratteristiche': list(
            widget.caratteristiche.all()
            .order_by('ordine', 'nome')
            .values('id', 'nome', 'sigla', 'colore', 'ordine')
        ),
        'caratteristiche_available': caratteristiche_available,
        'items': items,
    }
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_mattoni_display(request, key):
    """
    Restituisce i dati di un widget Mattoni per {{WIDGET_MATTONI:id}}.
    Applica i filtri configurati e ordina di default per Aura -> Ordine -> Nome.
    """
    widget = _resolve_by_pk_or_sync_id(
        WikiMattoniWidget.objects.prefetch_related('aure', 'caratteristiche'),
        key,
    )
    if not widget:
        raise Http404("No WikiMattoniWidget matches the given query.")

    mattoni_qs = Mattone.objects.select_related('aura', 'caratteristica_associata')

    filter_type = widget.filter_type or WikiMattoniWidget.FILTER_ALL
    if filter_type == WikiMattoniWidget.FILTER_AURA:
        aura_ids = list(widget.aure.values_list('id', flat=True))
        if aura_ids:
            mattoni_qs = mattoni_qs.filter(aura_id__in=aura_ids)
    elif filter_type == WikiMattoniWidget.FILTER_CARATTERISTICA:
        car_ids = list(widget.caratteristiche.values_list('id', flat=True))
        if car_ids:
            mattoni_qs = mattoni_qs.filter(caratteristica_associata_id__in=car_ids)

    mattoni_qs = mattoni_qs.order_by('aura__ordine', 'ordine', 'nome')

    return Response({
        'id': widget.id,
        'sync_id': str(widget.sync_id) if getattr(widget, 'sync_id', None) else None,
        'title': widget.title,
        'filter_type': filter_type,
        'aure': PunteggioWikiSerializer(widget.aure.all(), many=True).data,
        'caratteristiche': PunteggioWikiSerializer(widget.caratteristiche.all(), many=True).data,
        'mattoni': MattoneWikiSerializer(mattoni_qs, many=True).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_image_display(request, key):
    """
    Dettaglio immagine wiki con token stabile: accetta id numerico o sync_id.
    """
    obj = _resolve_by_pk_or_sync_id(WikiImmagine.objects.all(), key)
    if not obj:
        raise Http404("No WikiImmagine matches the given query.")
    serializer = WikiImmagineSerializer(obj, context={"request": request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_buttons_display(request, key):
    """
    Dettaglio widget pulsanti con token stabile: accetta id numerico o sync_id.
    """
    obj = _resolve_by_pk_or_sync_id(
        WikiButtonWidget.objects.prefetch_related("buttons"),
        key,
    )
    if not obj:
        raise Http404("No WikiButtonWidget matches the given query.")
    serializer = WikiButtonWidgetSerializer(obj)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_era_display(request, key):
    """
    Restituisce i dati di un'Era per {{WIDGET_ERA:id}}.
    Mostra anche le abilità assegnate automaticamente (is_default=True).
    """
    era = _resolve_by_pk_or_sync_id(
        Era.objects.prefetch_related(
            Prefetch(
                'ere_abilita',
                queryset=(
                    EraAbilita.objects
                    .filter(is_default=True)
                    .select_related('abilita')
                    .order_by('ordine', 'abilita__nome')
                ),
            )
        ),
        key,
    )
    if not era:
        raise Http404("No Era matches the given query.")

    abilita_auto = [
        {
            'id': row.abilita_id,
            'nome': row.abilita.nome,
            'descrizione': row.abilita.descrizione or '',
        }
        for row in era.ere_abilita.all()
        if row.abilita_id
    ]

    return Response({
        'id': era.id,
        'sync_id': str(era.sync_id) if getattr(era, 'sync_id', None) else None,
        'nome': era.nome,
        'descrizione_breve': era.descrizione_breve or '',
        'difetto_interpretativo_titolo': era.difetto_interpretativo_titolo or '',
        'difetto_interpretativo_testo': era.difetto_interpretativo_testo or '',
        'abilita_automatiche': abilita_auto,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def public_wiki_punteggi(request):
    """
    Lista pubblica (ridotta) di Punteggi filtrati per tipo.
    Query param: ?tipo=AU|CA
    """
    tipo = (request.GET.get('tipo') or '').strip().upper()
    qs = Punteggio.objects.all()
    if tipo:
        qs = qs.filter(tipo=tipo)
    qs = qs.order_by('ordine', 'nome')
    return Response(PunteggioWikiSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny]) # Aperto a tutti, filtriamo dentro
def get_wiki_menu(request):
    # Base: prendi tutto
    queryset = PaginaRegolamento.objects.all().order_by('parent', 'ordine', 'titolo')
    effective_user = _public_wiki_effective_user(request)

    if _is_campaign_master_plus(request, user_override=effective_user):
        # Master/Head Master/Admin: visione completa inclusa staff-only.
        pass
    elif _can_view_unpublished_non_staff_wiki(request, user_override=effective_user):
        # Redactor/Staffer: vedono anche bozze, ma non staff-only.
        queryset = queryset.filter(visibile_solo_staff=False)
    else:
        # Player/non autenticati: solo pubblico non staff-only.
        queryset = queryset.filter(public=True, visibile_solo_staff=False)

    serializer = PaginaRegolamentoSmallSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_page(request, slug):
    queryset = PaginaRegolamento.objects.all()
    effective_user = _public_wiki_effective_user(request)

    if _is_campaign_master_plus(request, user_override=effective_user):
        pass
    elif _can_view_unpublished_non_staff_wiki(request, user_override=effective_user):
        queryset = queryset.filter(visibile_solo_staff=False)
    else:
        queryset = queryset.filter(public=True, visibile_solo_staff=False)

    page = get_object_or_404(queryset, slug=slug)
    serializer = PaginaRegolamentoSerializer(page)
    return Response(serializer.data)


def _get_manuale_or_404(slug: str) -> ManualePdf:
    manuale = ManualePdf.objects.filter(slug=slug).first()
    if not manuale:
        raise Http404("Manuale non trovato.")
    return manuale


@api_view(['GET'])
@permission_classes([AllowAny])
def download_wiki_manual_pdf(request):
    """
    Genera on-demand il PDF del manuale «completo» (retrocompatibilità).
    """
    manuale = _get_manuale_or_404(request.GET.get('manuale') or 'completo')
    try:
        pdf_bytes = generate_manuale_pdf(
            manuale,
            request,
            render_content_fn=_render_wiki_widgets_for_pdf,
            force_public=not _is_campaign_master_plus(request),
        )
    except ValueError:
        raise Http404("Nessuna pagina wiki disponibile per questo manuale.")
    except ImportError:
        return HttpResponse(
            "Servizio PDF non disponibile: dipendenze di rendering mancanti nel container.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="kor35-manuale-{manuale.slug}.pdf"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_wiki_manual_snapshot(request):
    """
    Rigenera tutti i manuali attivi (retrocompatibilità endpoint legacy).
    """
    if not _is_campaign_wiki_editor_plus(request):
        return Response({"detail": "Permesso negato."}, status=status.HTTP_403_FORBIDDEN)

    results = []
    errors = []
    email = _triggered_by_email_from_request(request)
    for manuale in ManualePdf.objects.filter(attivo=True).order_by('ordine', 'titolo'):
        try:
            esegui_generazione_manuale(
                manuale,
                request,
                _render_wiki_widgets_for_pdf,
                triggered_by_email=email,
            )
            results.append({"slug": manuale.slug, "ok": True})
        except ValueError as exc:
            errors.append({"slug": manuale.slug, "detail": str(exc)})
        except ImportError:
            return Response(
                {"detail": "Servizio PDF non disponibile: dipendenze di rendering mancanti nel container."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Errore generazione manuale %s", manuale.slug)
            errors.append({"slug": manuale.slug, "detail": "Errore generazione."})

    if not results and errors:
        return Response({"detail": "Nessun manuale generato.", "errors": errors}, status=status.HTTP_404_NOT_FOUND)

    return Response(
        {
            "ok": True,
            "generated": results,
            "errors": errors,
            "download_url": "/api/plot/api/wiki/manuale/latest.pdf",
        }
    )


def _file_response_latest_manuale_pdf(slug: str):
    manuale = _get_manuale_or_404(slug)
    output_path = wiki_manual_latest_path(manuale)
    if not output_path.exists() and slug == 'completo':
        output_path = wiki_manual_legacy_latest_path()
    if not output_path.exists():
        raise Http404("Nessun manuale PDF generato al momento.")
    response = FileResponse(open(output_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="kor35-manuale-{slug}-latest.pdf"'
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def download_latest_wiki_manual_pdf(request):
    """Scarica l'ultimo PDF del manuale «completo» (retrocompatibilità)."""
    return _file_response_latest_manuale_pdf('completo')


@api_view(['GET'])
@permission_classes([AllowAny])
def download_latest_manuale_pdf(request, slug):
    return _file_response_latest_manuale_pdf(slug)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_public_wiki_manuali(request):
    qs = ManualePdf.objects.filter(attivo=True).order_by('ordine', 'titolo')
    serializer = PublicManualePdfSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


def _pdf_widget_modalita():
    return get_current_pdf_stile().get("widget_modalita") or "completo"


def _render_wiki_widgets_for_pdf(content, request):
    def _replace(match):
        widget_type = (match.group(1) or "").strip().upper()
        widget_key = (match.group(2) or "").strip()
        return _widget_token_to_pdf_html(widget_type, widget_key, request)

    rendered = WIDGET_TOKEN_RE.sub(_replace, content or "")
    rendered = _absolutize_img_src_for_pdf(rendered, request)
    if get_current_pdf_stile().get("hide_images"):
        rendered = re.sub(r"<img\b[^>]*\s*/?>", "", rendered, flags=re.IGNORECASE)
    return rendered


def _widget_token_to_pdf_html(widget_type, widget_key, request):
    try:
        if widget_type == "TIER":
            return _pdf_render_tier(widget_key)
        if widget_type in ("TIER_COLLECTION", "COLLECTION", "COLLEZIONE", "COLLEZIONI"):
            return _pdf_render_tier_collection(widget_key)
        if widget_type == "MATTONI":
            return _pdf_render_mattoni(widget_key)
        if widget_type in ("BUTTONS", "PULSANTI"):
            return ""
        if widget_type in ("IMAGE", "IMMAGINE"):
            if get_current_pdf_stile().get("hide_images"):
                return ""
            return _pdf_render_image(widget_key, request)
        if widget_type == "ERA":
            return _pdf_render_era(widget_key)
    except Exception as exc:
        logger.warning("Errore rendering widget PDF %s:%s -> %s", widget_type, widget_key, exc)
        return (
            f'<div class="pdf-widget pdf-widget-error">'
            f'<strong>Widget {escape(widget_type)}</strong>: errore di rendering.'
            f"</div>"
        )

    return (
        f'<div class="pdf-widget pdf-widget-missing">'
        f'<strong>Widget {escape(widget_type)}</strong> non supportato nel PDF.'
        f"</div>"
    )


def _pdf_render_tier(widget_key):
    _abilita_prefetch = Prefetch(
        'abilita',
        queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3')
    )
    _caratt_prefetch = Prefetch('caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA'))
    tier = _resolve_by_pk_or_sync_id(Tier.objects.prefetch_related(_abilita_prefetch, _caratt_prefetch), widget_key)
    if not tier:
        widget = _resolve_by_pk_or_sync_id(
            WikiTierWidget.objects.select_related('tier').prefetch_related(
                Prefetch('tier__abilita', queryset=Abilita.objects.select_related('caratteristica', 'caratteristica_2', 'caratteristica_3')),
                Prefetch('tier__caratteristiche_visibili', queryset=Punteggio.objects.filter(tipo='CA')),
            ),
            widget_key,
        )
        tier = widget.tier if widget else None
    if not tier:
        return f'<div class="pdf-widget pdf-widget-error">Tier {escape(widget_key)} non trovato.</div>'

    data = WikiTierSerializer(tier).data
    modalita = _pdf_widget_modalita()
    titolo_tier = escape(data.get("nome") or "")

    if modalita == "solo_testo":
        items = "".join(
            f"<li>{escape(a.get('nome') or '')}</li>" for a in (data.get("abilita") or [])
        ) or "<li>Nessuna abilità.</li>"
        return (
            f'<section class="pdf-widget pdf-widget-tier pdf-widget-compact">'
            f'<h4 class="pdf-widget-title">Tier: {titolo_tier}</h4>'
            f"<ul class=\"pdf-widget-list\">{items}</ul>"
            f"</section>"
        )

    caratteristiche = ", ".join(
        [escape(c.get("sigla") or c.get("nome") or "") for c in (data.get("caratteristiche_visibili") or []) if (c.get("sigla") or c.get("nome"))]
    )
    abilita_rows = []
    for abilita in (data.get("abilita") or []):
        nome = escape(abilita.get("nome") or "")
        costo = escape(abilita.get("costo") or "")
        if modalita == "compatto":
            costo_part = f" <span class=\"muted\">({costo})</span>" if costo else ""
            abilita_rows.append(f"<tr><td><strong>{nome}</strong>{costo_part}</td></tr>")
        else:
            desc = abilita.get("descrizione") or ""
            costo_html = f'<br><span class="muted">{costo}</span>' if costo else ""
            abilita_rows.append(
                f"<tr><td><strong>{nome}</strong>{costo_html}</td>"
                f"<td>{desc}</td></tr>"
            )
    if modalita == "compatto":
        abilita_html = "".join(abilita_rows) or "<tr><td>Nessuna abilità.</td></tr>"
        table = (
            f'<table class="pdf-widget-table pdf-widget-table-compact">'
            f"<thead><tr><th>Abilità</th></tr></thead><tbody>{abilita_html}</tbody></table>"
        )
        descrizione_html = ""
    else:
        abilita_html = "".join(abilita_rows) or "<tr><td colspan='2'>Nessuna abilità.</td></tr>"
        table = (
            f'<table class="pdf-widget-table"><thead><tr><th>Abilità</th><th>Descrizione</th></tr></thead>'
            f"<tbody>{abilita_html}</tbody></table>"
        )
        descrizione = data.get("descrizione") or ""
        descrizione_html = f'<div class="pdf-widget-rich">{descrizione}</div>' if descrizione else ""

    caratteristiche_html = f'<p class="muted">Caratteristiche: {caratteristiche}</p>' if caratteristiche and modalita != "compatto" else ""
    if modalita == "compatto" and caratteristiche:
        caratteristiche_html = f'<p class="muted">{caratteristiche}</p>'

    return (
        f'<section class="pdf-widget pdf-widget-tier">'
        f'<div class="pdf-widget-head">'
        f'<h4 class="pdf-widget-title">Tier: {titolo_tier}</h4>'
        f"{caratteristiche_html}"
        f"</div>"
        f"{descrizione_html}"
        f"{table}"
        f"</section>"
    )


def _pdf_render_tier_collection(widget_key):
    widget = _resolve_by_pk_or_sync_id(
        WikiTierCollectionWidget.objects.prefetch_related('widgets__tier'),
        widget_key,
    )
    if not widget:
        return f'<div class="pdf-widget pdf-widget-error">Collezione Tier {escape(widget_key)} non trovata.</div>'

    if widget.source_mode == WikiTierCollectionWidget.SOURCE_SELECTED:
        qs = widget.widgets.all().select_related('tier')
    else:
        qs = WikiTierWidget.objects.all().select_related('tier')
    widget_ids = [str(w.sync_id) if getattr(w, "sync_id", None) else str(w.id) for w in qs if getattr(w, "tier", None)]
    if not widget_ids:
        return f'<div class="pdf-widget pdf-widget-error">Collezione Tier {escape(widget_key)} senza elementi.</div>'

    rendered_items = "".join([_pdf_render_tier(wid) for wid in widget_ids])
    return (
        f'<section class="pdf-widget pdf-widget-tier-collection">'
        f'<div class="pdf-widget-head">'
        f'<h4 class="pdf-widget-title">{escape(widget.title or "Collezione Tier")}</h4>'
        f"</div>"
        f'<div class="pdf-tier-collection-grid">{rendered_items}</div>'
        f"</section>"
    )


def _pdf_render_mattoni(widget_key):
    widget = _resolve_by_pk_or_sync_id(
        WikiMattoniWidget.objects.prefetch_related('aure', 'caratteristiche'),
        widget_key,
    )
    if not widget:
        return f'<div class="pdf-widget pdf-widget-error">Widget Mattoni {escape(widget_key)} non trovato.</div>'

    mattoni_qs = Mattone.objects.select_related('aura', 'caratteristica_associata')
    filter_type = widget.filter_type or WikiMattoniWidget.FILTER_ALL
    if filter_type == WikiMattoniWidget.FILTER_AURA:
        aura_ids = list(widget.aure.values_list('id', flat=True))
        if aura_ids:
            mattoni_qs = mattoni_qs.filter(aura_id__in=aura_ids)
    elif filter_type == WikiMattoniWidget.FILTER_CARATTERISTICA:
        car_ids = list(widget.caratteristiche.values_list('id', flat=True))
        if car_ids:
            mattoni_qs = mattoni_qs.filter(caratteristica_associata_id__in=car_ids)
    data = MattoneWikiSerializer(mattoni_qs.order_by('aura__ordine', 'ordine', 'nome'), many=True).data

    modalita = _pdf_widget_modalita()
    rows = []
    for m in data:
        if modalita == "solo_testo":
            rows.append(f"<li>{escape(m.get('nome') or '')}</li>")
        elif modalita == "compatto":
            rows.append(
                "<tr>"
                f"<td><strong>{escape(m.get('nome') or '')}</strong></td>"
                f"<td>{escape((m.get('aura') or {}).get('nome') or '-')}</td>"
                "</tr>"
            )
        else:
            rows.append(
                "<tr>"
                f"<td><strong>{escape(m.get('nome') or '')}</strong></td>"
                f"<td>{escape((m.get('aura') or {}).get('nome') or '-')}</td>"
                f"<td>{escape((m.get('caratteristica_associata') or {}).get('nome') or '-')}</td>"
                f"<td>{m.get('descrizione_mattone') or ''}</td>"
                "</tr>"
            )
    if modalita == "solo_testo":
        body = "".join(rows) or "<li>Nessun mattone.</li>"
        inner = f'<ul class="pdf-widget-list">{body}</ul>'
    elif modalita == "compatto":
        body = "".join(rows) or "<tr><td colspan='2'>Nessun mattone.</td></tr>"
        inner = (
            f'<table class="pdf-widget-table"><thead><tr><th>Nome</th><th>Aura</th></tr></thead>'
            f"<tbody>{body}</tbody></table>"
        )
    else:
        body = "".join(rows) or "<tr><td colspan='4'>Nessun mattone.</td></tr>"
        inner = (
            f'<table class="pdf-widget-table"><thead><tr><th>Nome</th><th>Aura</th>'
            f"<th>Caratteristica</th><th>Descrizione</th></tr></thead><tbody>{body}</tbody></table>"
        )
    return (
        f'<section class="pdf-widget pdf-widget-mattoni">'
        f'<div class="pdf-widget-head">'
        f'<h4 class="pdf-widget-title">{escape(widget.title or "Mattoni")}</h4>'
        f"</div>"
        f"{inner}"
        f"</section>"
    )


def _pdf_render_image(widget_key, request):
    obj = _resolve_by_pk_or_sync_id(WikiImmagine.objects.all(), widget_key)
    if not obj:
        return f'<div class="pdf-widget pdf-widget-error">Immagine widget {escape(widget_key)} non trovata.</div>'
    serializer = WikiImmagineSerializer(obj, context={"request": request})
    data = serializer.data
    image_url = obj.immagine.url if getattr(obj, "immagine", None) else (data.get("immagine_url") or data.get("immagine"))
    if image_url:
        image_url = _normalize_img_src_for_pdf(image_url, request)
    image_html = f'<img src="{escape(image_url)}" alt="{escape(data.get("titolo") or "")}" />' if image_url else ""
    descrizione_html = f'<div class="muted">{escape(data.get("descrizione") or "")}</div>' if data.get("descrizione") else ""
    caption_html = f'<figcaption>{escape(data.get("titolo") or "")}</figcaption>' if data.get("titolo") else ""
    if not image_html:
        return f'<div class="pdf-widget pdf-widget-error">Immagine widget {escape(widget_key)} non disponibile.</div>'
    return (
        f'<figure class="pdf-widget pdf-widget-image">'
        f"{image_html}"
        f"{caption_html}"
        f"{descrizione_html}"
        f"</figure>"
    )


def _absolutize_img_src_for_pdf(html, request):
    if not html:
        return html
    return re.sub(
        r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])',
        lambda m: f'{m.group(1)}{escape(_normalize_img_src_for_pdf(m.group(2), request))}{m.group(3)}',
        html,
        flags=re.IGNORECASE,
    )


def _normalize_img_src_for_pdf(src, request):
    value = str(src or "").strip()
    if not value:
        return value
    if value.startswith(("data:", "file://", "http://", "https://")):
        return value

    # Usa il file locale per /media quando disponibile: evita fetch HTTP in WeasyPrint.
    if value.startswith("/media/"):
        local_uri = _media_rel_to_file_uri(value[len("/media/"):])
        return local_uri or request.build_absolute_uri(value)
    if value.startswith("media/"):
        local_uri = _media_rel_to_file_uri(value[len("media/"):])
        return local_uri or request.build_absolute_uri(f"/{value}")

    if value.startswith("/"):
        return request.build_absolute_uri(value)
    return request.build_absolute_uri(f"/{value.lstrip('/')}")


def _media_rel_to_file_uri(rel_path):
    rel_clean = str(rel_path or "").split("?", 1)[0].split("#", 1)[0].lstrip("/")
    if not rel_clean:
        return None
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / rel_clean).resolve()
    try:
        candidate.relative_to(media_root)
    except Exception:
        return None
    if not candidate.exists():
        return None
    return candidate.as_uri()


def _pdf_render_era(widget_key):
    era = _resolve_by_pk_or_sync_id(
        Era.objects.prefetch_related(
            Prefetch(
                'ere_abilita',
                queryset=(
                    EraAbilita.objects.filter(is_default=True).select_related('abilita').order_by('ordine', 'abilita__nome')
                ),
            )
        ),
        widget_key,
    )
    if not era:
        return f'<div class="pdf-widget pdf-widget-error">Era {escape(widget_key)} non trovata.</div>'
    abilita = [row.abilita.nome for row in era.ere_abilita.all() if row.abilita_id]
    abilita_html = "".join([f"<li>{escape(nome)}</li>" for nome in abilita]) or "<li>Nessuna abilità automatica.</li>"
    descrizione_html = f'<div class="pdf-widget-rich">{era.descrizione_breve}</div>' if era.descrizione_breve else ""
    return (
        f'<section class="pdf-widget pdf-widget-era">'
        f'<div class="pdf-widget-head">'
        f'<h4 class="pdf-widget-title">Era: {escape(era.nome or "")}</h4>'
        f"{descrizione_html}"
        f"</div>"
        f"<p><strong>Abilità automatiche</strong></p><ul>{abilita_html}</ul>"
        f"</section>"
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def serve_wiki_image(request, slug):
    """
    Restituisce l'immagine della pagina wiki ridimensionata.
    Query params:
    - w: larghezza desiderata (es. 1024)
    - q: qualità (default 80)
    """
    page = get_object_or_404(PaginaRegolamento, slug=slug)
    
    if not page.immagine:
        raise Http404("Nessuna immagine associata")

    # Parametri richiesti
    try:
        width = int(request.GET.get('w', 0))
    except ValueError:
        width = 0
        
    original_path = page.immagine.path
    
    # Se non è richiesta una larghezza specifica o è troppo grande, ritorna l'originale
    if width <= 0 or width > 2500:
        return FileResponse(open(original_path, 'rb'), content_type='image/jpeg')

    # Logica di Caching: nomefile_W.ext
    base, ext = os.path.splitext(original_path)
    cache_filename = f"{base}_{width}{ext}"
    
    # 1. Se esiste il file cachato, restituiscilo
    if os.path.exists(cache_filename):
        return FileResponse(open(cache_filename, 'rb'), content_type='image/jpeg')

    # 2. Se non esiste, generalo
    try:
        img = Image.open(original_path)
        
        # Calcola altezza mantenendo aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(width * aspect_ratio)
        
        # Ridimensiona
        img = img.resize((width, new_height), Image.Resampling.LANCZOS)
        
        # Salva copia ottimizzata
        img.save(cache_filename, quality=85, optimize=True)
        
        # Riapri per servire il file (per evitare lock)
        return FileResponse(open(cache_filename, 'rb'), content_type='image/jpeg')
        
    except Exception as e:
        print(f"Errore resize immagine: {e}")
        # Fallback sull'originale in caso di errore
        return FileResponse(open(original_path, 'rb'), content_type='image/jpeg')