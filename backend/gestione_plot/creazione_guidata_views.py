import json

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from personaggi.views import _get_active_campaign

from .creazione_guidata_serializers import (
    CreazioneGuidataFlussoListSerializer,
    CreazioneGuidataFlussoSerializer,
    CreazioneGuidataPassoPlayerSerializer,
    CreazioneGuidataPassoSerializer,
    CreazioneGuidataSceltaSerializer,
)
from personaggi.models import Personaggio

from .creazione_guidata_helpers import _parse_effetti_param, enrich_passo_player_data
from .creazione_guidata_publish import (
    crea_sandbox_test_da_produzione,
    get_sandbox_for_produzione,
    pubblica_sandbox_su_produzione,
    sandbox_ha_modifiche_non_pubblicate,
)
from .models import ConfigurazioneSito, CreazioneGuidataFlusso, CreazioneGuidataPasso, CreazioneGuidataScelta
from .views import IsWikiEditorOrMasterForStaffOnly, _is_campaign_staff_plus, _is_global_admin


def _user_can_use_wizard_test(request):
    """Staff Django, superuser o ruoli campagna Staffer/Master/Head Master."""
    user = request.user
    if not user or not user.is_authenticated:
        return False
    if _is_global_admin(user) or getattr(user, 'is_staff', False):
        return True
    return _is_campaign_staff_plus(request, user_override=user)


def _parse_modalita_test_param(request):
    raw = request.query_params.get('modalita_test')
    if raw is None:
        return None
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')


def _flusso_queryset_for_campagna(campagna):
    qs = CreazioneGuidataFlusso.objects.filter(attivo=True).select_related(
        'passo_iniziale', 'campagna'
    )
    if campagna:
        specific = qs.filter(campagna=campagna).order_by('-updated_at')
        if specific.exists():
            return specific
    return qs.filter(campagna__isnull=True).order_by('-updated_at')


def _flusso_produzione_attivo(campagna):
    return _flusso_queryset_for_campagna(campagna).filter(modalita_test=False).first()


def _resolve_active_flusso(request):
    prefer_test = _parse_modalita_test_param(request)
    can_test = _user_can_use_wizard_test(request)
    if prefer_test is True and not can_test:
        return None

    campagna = _get_active_campaign(request)
    prod = _flusso_produzione_attivo(campagna)

    if prefer_test is True:
        if prod:
            sandbox = get_sandbox_for_produzione(prod)
            if sandbox and sandbox.attivo:
                return sandbox
        qs = _flusso_queryset_for_campagna(campagna).filter(modalita_test=True)
        return qs.first()

    if prefer_test is False:
        return prod

    return prod


def _personaggio_for_wizard(request):
    pid = request.query_params.get('personaggio_id')
    if not pid:
        return None
    try:
        return Personaggio.objects.get(pk=pid, proprietario=request.user)
    except Personaggio.DoesNotExist:
        return None


class CreazioneGuidataFlussoViewSet(viewsets.ModelViewSet):
    queryset = CreazioneGuidataFlusso.objects.all().prefetch_related('passi__scelte')
    permission_classes = [IsWikiEditorOrMasterForStaffOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return CreazioneGuidataFlussoListSerializer
        return CreazioneGuidataFlussoSerializer

    @action(detail=True, methods=['post'], url_path='crea-sandbox')
    def crea_sandbox(self, request, pk=None):
        flusso = self.get_object()
        try:
            sandbox = crea_sandbox_test_da_produzione(flusso)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CreazioneGuidataFlussoSerializer(sandbox, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='pubblica-su-produzione')
    def pubblica_su_produzione(self, request, pk=None):
        flusso_test = self.get_object()
        try:
            prod = pubblica_sandbox_su_produzione(flusso_test)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CreazioneGuidataFlussoSerializer(prod, context={'request': request})
        return Response({
            'messaggio': 'Modifiche pubblicate sul flusso di produzione.',
            'flusso_produzione': serializer.data,
        })


class CreazioneGuidataPassoViewSet(viewsets.ModelViewSet):
    queryset = CreazioneGuidataPasso.objects.all().prefetch_related('scelte')
    serializer_class = CreazioneGuidataPassoSerializer
    permission_classes = [IsWikiEditorOrMasterForStaffOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        flusso_id = self.request.query_params.get('flusso')
        if flusso_id:
            qs = qs.filter(flusso_id=flusso_id)
        return qs


class CreazioneGuidataSceltaViewSet(viewsets.ModelViewSet):
    queryset = CreazioneGuidataScelta.objects.all().select_related(
        'passo', 'passo_destinazione'
    )
    serializer_class = CreazioneGuidataSceltaSerializer
    permission_classes = [IsWikiEditorOrMasterForStaffOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        passo_id = self.request.query_params.get('passo')
        if passo_id:
            qs = qs.filter(passo_id=passo_id)
        return qs


def _creazione_guidata_aperta_giocatori():
    return bool(ConfigurazioneSito.get_config().creazione_guidata_aperta_giocatori)


@api_view(['GET', 'PATCH'])
@permission_classes([IsWikiEditorOrMasterForStaffOnly])
def creazione_guidata_impostazioni(request):
    """Interruttore globale: pulsante wizard visibile ai giocatori."""
    config = ConfigurazioneSito.get_config()
    if request.method == 'GET':
        return Response({
            'aperta_giocatori': config.creazione_guidata_aperta_giocatori,
        })
    val = request.data.get('aperta_giocatori')
    if val is not None:
        config.creazione_guidata_aperta_giocatori = str(val).strip().lower() in (
            '1', 'true', 'yes', 'on',
        )
        config.save(update_fields=['creazione_guidata_aperta_giocatori', 'ultima_modifica'])
    return Response({'aperta_giocatori': config.creazione_guidata_aperta_giocatori})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def creazione_guidata_stato(request):
    """Indica se esiste un percorso guidato accessibile (produzione o test per staff)."""
    campagna = _get_active_campaign(request)
    can_test = _user_can_use_wizard_test(request)
    prod = _flusso_produzione_attivo(campagna)
    sandbox = get_sandbox_for_produzione(prod) if prod and can_test else None
    test_disponibile = bool(sandbox and sandbox.attivo) if can_test else False
    flusso = _resolve_active_flusso(request)
    aperta_giocatori = _creazione_guidata_aperta_giocatori()
    disponibile_giocatori = bool(prod and aperta_giocatori)
    return Response({
        'disponibile': bool(disponibile_giocatori or test_disponibile),
        'disponibile_produzione': bool(prod),
        'disponibile_test': test_disponibile,
        'aperta_giocatori': aperta_giocatori,
        'disponibile_giocatori': disponibile_giocatori,
        'puo_usare_test': can_test,
        'flusso_produzione_id': str(prod.id) if prod else None,
        'flusso_sandbox_id': str(sandbox.id) if sandbox else None,
        'sandbox_modifiche_pending': (
            sandbox_ha_modifiche_non_pubblicate(prod) if prod and sandbox else False
        ),
        'flusso_attivo_slug': flusso.slug if flusso else None,
        'flusso_attivo_test': bool(flusso and flusso.modalita_test),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def creazione_guidata_avvio(request):
    flusso = _resolve_active_flusso(request)
    if not flusso or not flusso.passo_iniziale_id:
        return Response(
            {'detail': 'Nessun percorso di creazione guidata attivo.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    passo = (
        CreazioneGuidataPasso.objects.filter(pk=flusso.passo_iniziale_id)
        .prefetch_related('scelte__passo_destinazione')
        .first()
    )
    personaggio = _personaggio_for_wizard(request)
    effetti = _parse_effetti_param(request.query_params.get('effetti'))
    passo_data = enrich_passo_player_data(passo, personaggio, effetti, request=request)
    return Response({
        'flusso': {
            'id': flusso.id,
            'slug': flusso.slug,
            'titolo': flusso.titolo,
            'modalita_test': flusso.modalita_test,
        },
        'passo': passo_data,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def creazione_guidata_passo(request, slug):
    flusso = _resolve_active_flusso(request)
    if not flusso:
        return Response({'detail': 'Nessun flusso attivo.'}, status=status.HTTP_404_NOT_FOUND)
    passo = (
        CreazioneGuidataPasso.objects.filter(flusso=flusso, slug=slug)
        .prefetch_related('scelte__passo_destinazione')
        .first()
    )
    if not passo:
        return Response({'detail': 'Passo non trovato.'}, status=status.HTTP_404_NOT_FOUND)
    personaggio = _personaggio_for_wizard(request)
    effetti = _parse_effetti_param(request.query_params.get('effetti'))
    return Response(enrich_passo_player_data(passo, personaggio, effetti, request=request))
