from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.permissions import IsStaffOrMaster
from personaggi.models import Personaggio, get_default_campagna_id
from personaggi.scommesse_config import config_to_public_dict, get_config_scommesse
from personaggi.scommesse_evento import personaggio_in_evento_attivo
from personaggi.scommesse_logic import ALLIBRATORE_SIGLA, calendario_ancora_visibile
from personaggi.scommesse_classifica import calcola_classifica_sport, calcola_classifiche_attive
from personaggi.scommesse_models import (
    CalendarioScommesse,
    CodiceScommessa,
    ConfigurazioneScommesse,
    ProgrammazioneTorneoScommesse,
    PuntataScommessa,
    SportScommesse,
    SquadraScommesse,
)
from personaggi.scommesse_scheduling import (
    genera_calendario_per_evento,
    sincronizza_programmazione,
    sincronizza_tutte_programmazioni,
)
from personaggi.scommesse_service import (
    liquidare_calendari_scaduti,
    piazza_puntata,
    riscuoti_vincita,
    ritira_da_riserva,
    storico_risultati_squadra,
)
from personaggi.serializers_scommesse import (
    CalendarioScommesseDetailSerializer,
    CalendarioScommesseListSerializer,
    CalendarioScommesseWriteSerializer,
    CodiceScommessaSerializer,
    ConfigurazioneScommesseSerializer,
    PiazzamentoPuntataSerializer,
    ProgrammazioneTorneoScommesseSerializer,
    PuntataScommessaSerializer,
    SportScommesseSerializer,
    SquadraScommesseSerializer,
)


def _get_active_personaggio(request, *, required=True):
    """
    Risolve il personaggio attivo dall'utente loggato.
    Allineato a PersonaggioDetailView: proprietario o master/staff della campagna del PG.
    """
    from personaggi.views import _can_operate_in_campaign

    raw_id = request.query_params.get("personaggio_id") or request.data.get("personaggio_id")
    if raw_id in (None, ""):
        return None
    try:
        pg_id = int(raw_id)
    except (TypeError, ValueError):
        return None

    personaggio = (
        Personaggio.objects.filter(pk=pg_id)
        .select_related("campagna", "proprietario")
        .first()
    )
    if not personaggio:
        return None

    user = request.user
    if personaggio.proprietario_id == user.id:
        return personaggio
    if user.is_superuser or _can_operate_in_campaign(user, personaggio.campagna, needs_master=True):
        return personaggio
    return None


def _personaggio_or_error(request, *, required=True):
    personaggio = _get_active_personaggio(request)
    if personaggio:
        return personaggio, None
    if not required:
        return None, None
    raw_id = request.query_params.get("personaggio_id") or request.data.get("personaggio_id")
    if raw_id in (None, ""):
        return None, Response({"error": "Parametro personaggio_id richiesto."}, status=400)
    return None, Response({"error": "Personaggio non trovato o non autorizzato."}, status=400)


class ScommessePuntatePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class SportScommesseStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = SportScommesseSerializer
    queryset = SportScommesse.objects.all().order_by("nome")


class SquadraScommesseStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = SquadraScommesseSerializer

    def get_queryset(self):
        qs = SquadraScommesse.objects.select_related("sport").order_by("sport__nome", "nome")
        sport_id = self.request.query_params.get("sport")
        if sport_id:
            qs = qs.filter(sport_id=sport_id)
        return qs


class CalendarioScommesseStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    queryset = CalendarioScommesse.objects.select_related("sport", "evento").prefetch_related(
        "incontri__squadra_casa", "incontri__squadra_trasferta"
    ).order_by("-data_risoluzione")

    def get_serializer_class(self):
        if self.action in ("retrieve", "list"):
            return CalendarioScommesseDetailSerializer
        return CalendarioScommesseWriteSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["staff_view"] = True
        return ctx

    @action(detail=True, methods=["post"], url_path="rigenera-incontri")
    def rigenera_incontri(self, request, pk=None):
        calendario = self.get_object()
        if calendario.puntate.exists():
            return Response(
                {"error": "Impossibile rigenerare: esistono puntate su questo calendario."},
                status=400,
            )
        try:
            calendario.genera_incontri()
        except DjangoValidationError as exc:
            return Response({"error": str(exc.message if hasattr(exc, "message") else exc)}, status=400)
        calendario.refresh_from_db()
        ser = CalendarioScommesseDetailSerializer(calendario, context=self.get_serializer_context())
        return Response(ser.data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            calendario = ser.save()
            try:
                calendario.genera_incontri()
            except DjangoValidationError as exc:
                calendario.delete()
                msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
                return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        out = CalendarioScommesseDetailSerializer(calendario, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProgrammazioneTorneoScommesseStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = ProgrammazioneTorneoScommesseSerializer
    queryset = ProgrammazioneTorneoScommesse.objects.select_related(
        "sport", "ultimo_evento"
    ).order_by("sport__nome")

    def get_queryset(self):
        qs = super().get_queryset()
        sport_id = self.request.query_params.get("sport")
        if sport_id:
            qs = qs.filter(sport_id=sport_id)
        return qs

    def create(self, request, *args, **kwargs):
        sport_id = request.data.get("sport")
        if sport_id and ProgrammazioneTorneoScommesse.objects.filter(sport_id=sport_id).exists():
            return Response(
                {"error": "Esiste già una programmazione per questo sport."},
                status=400,
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="sincronizza")
    def sincronizza(self, request, pk=None):
        prog = self.get_object()
        max_crea = int(request.data.get("max_crea", 1))
        try:
            creati = sincronizza_programmazione(prog, max_crea=max(1, min(max_crea, 10)))
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"error": msg}, status=400)
        calendari = CalendarioScommesseDetailSerializer(
            CalendarioScommesse.objects.filter(
                id__in=[c.id for c in creati]
            ).select_related("sport", "evento").prefetch_related(
                "incontri__squadra_casa", "incontri__squadra_trasferta"
            ),
            many=True,
            context={"staff_view": True},
        ).data
        prog.refresh_from_db()
        return Response({
            "creati": len(creati),
            "calendari": calendari,
            "programmazione": ProgrammazioneTorneoScommesseSerializer(prog).data,
        })

    @action(detail=True, methods=["post"], url_path="genera-per-evento")
    def genera_per_evento(self, request, pk=None):
        from gestione_plot.models import Evento

        prog = self.get_object()
        evento_id = request.data.get("evento_id")
        if not evento_id:
            return Response({"error": "evento_id richiesto."}, status=400)
        try:
            evento = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            return Response({"error": "Evento non trovato."}, status=404)
        try:
            cal = genera_calendario_per_evento(prog, evento)
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"error": msg}, status=400)
        prog.refresh_from_db()
        ser = CalendarioScommesseDetailSerializer(cal, context={"staff_view": True})
        return Response({
            "calendario": ser.data,
            "programmazione": ProgrammazioneTorneoScommesseSerializer(prog).data,
        }, status=201)

    @action(detail=False, methods=["post"], url_path="sincronizza-tutte")
    def sincronizza_tutte(self, request):
        max_crea = int(request.data.get("max_crea_per_sport", 1))
        report = sincronizza_tutte_programmazioni(max_crea_per_sport=max(1, min(max_crea, 5)))
        return Response(report)


class ScommesseCalendariPlayerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        liquidare_calendari_scaduti()
        now = timezone.now()
        qs = CalendarioScommesse.objects.filter(attivo=True).select_related("sport", "evento")
        visibili = []
        for cal in qs:
            if not calendario_ancora_visibile(cal):
                continue
            visibili.append(cal.id)
        calendari = CalendarioScommesse.objects.filter(id__in=visibili).select_related("sport").order_by("-data_risoluzione")
        personaggio, _ = _personaggio_or_error(request, required=False)
        cfg = get_config_scommesse()
        return Response({
            "config": config_to_public_dict(cfg, personaggio=personaggio),
            "calendari": CalendarioScommesseListSerializer(calendari, many=True).data,
        })


class ScommesseCalendarioDetailPlayerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, calendario_id):
        liquidare_calendari_scaduti()
        try:
            cal = CalendarioScommesse.objects.select_related("sport", "evento").prefetch_related(
                "incontri__squadra_casa", "incontri__squadra_trasferta"
            ).get(pk=calendario_id)
        except CalendarioScommesse.DoesNotExist:
            return Response({"error": "Calendario non trovato."}, status=404)
        if not calendario_ancora_visibile(cal):
            return Response({"error": "Calendario non disponibile."}, status=404)
        ser = CalendarioScommesseDetailSerializer(cal)
        return Response(ser.data)


class ScommessePuntataCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        personaggio, err = _personaggio_or_error(request)
        if err:
            return err
        ser = PiazzamentoPuntataSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            puntata = piazza_puntata(
                personaggio,
                data["calendario_id"],
                data["selezioni"],
                data["importo"],
                codice_str=data.get("codice") or None,
                usa_riserva=bool(data.get("usa_riserva")),
            )
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"error": msg}, status=400)
        return Response(
            PuntataScommessaSerializer(
                PuntataScommessa.objects.prefetch_related("selezioni__incontro").get(pk=puntata.pk)
            ).data,
            status=201,
        )


class ScommesseMiePuntateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        liquidare_calendari_scaduti()
        personaggio, err = _personaggio_or_error(request, required=False)
        if err:
            return err
        if not personaggio:
            paginator = ScommessePuntatePagination()
            return paginator.get_paginated_response([])
        qs = PuntataScommessa.objects.filter(
            personaggio=personaggio,
        ).select_related("calendario__sport", "codice").prefetch_related(
            "selezioni__incontro__squadra_casa", "selezioni__incontro__squadra_trasferta"
        ).order_by("-created_at")
        paginator = ScommessePuntatePagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        ser = PuntataScommessaSerializer(page, many=True, context={"personaggio": personaggio})
        return paginator.get_paginated_response(ser.data)


class ScommesseRiscuotiVincitaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, puntata_id):
        liquidare_calendari_scaduti()
        personaggio, err = _personaggio_or_error(request)
        if err:
            return err
        try:
            puntata = riscuoti_vincita(personaggio, puntata_id)
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"error": msg}, status=400)
        puntata = PuntataScommessa.objects.filter(pk=puntata.pk).select_related(
            "calendario__sport", "codice"
        ).prefetch_related(
            "selezioni__incontro__squadra_casa", "selezioni__incontro__squadra_trasferta"
        ).first()
        return Response(PuntataScommessaSerializer(puntata, context={"personaggio": personaggio}).data)


class ScommesseRitiraRiservaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, puntata_id):
        liquidare_calendari_scaduti()
        personaggio, err = _personaggio_or_error(request)
        if err:
            return err
        try:
            puntata = ritira_da_riserva(personaggio, puntata_id)
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"error": msg}, status=400)
        puntata = PuntataScommessa.objects.filter(pk=puntata.pk).select_related(
            "calendario__sport", "codice"
        ).prefetch_related(
            "selezioni__incontro__squadra_casa", "selezioni__incontro__squadra_trasferta"
        ).first()
        return Response(PuntataScommessaSerializer(puntata, context={"personaggio": personaggio}).data)


class ScommesseGeneraCodiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        personaggio, err = _personaggio_or_error(request)
        if err:
            return err
        if personaggio.get_valore_statistica(ALLIBRATORE_SIGLA) <= 0:
            return Response(
                {"error": "Serve la statistica Allibratore (ALL > 0) per generare codici."},
                status=403,
            )
        from personaggi.transazioni_evento import GIOCO_LIVE_BLOCCO_MSG, gioco_live_consentito

        if not gioco_live_consentito(user=request.user, campagna=personaggio.campagna):
            return Response(
                {"error": GIOCO_LIVE_BLOCCO_MSG},
                status=403,
            )
        try:
            codice = CodiceScommessa.crea_per_allibratore(personaggio)
        except DjangoValidationError as exc:
            msg = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response({"error": msg}, status=400)
        return Response(CodiceScommessaSerializer(codice).data, status=201)


class ScommesseMieiCodiciView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        personaggio, err = _personaggio_or_error(request, required=False)
        if err:
            return err
        if not personaggio:
            return Response({"valore_all": 0, "can_generare": False, "codici": []})
        valore_all = personaggio.get_valore_statistica(ALLIBRATORE_SIGLA)
        from personaggi.transazioni_evento import gioco_live_consentito

        azioni_ok = gioco_live_consentito(user=request.user, campagna=personaggio.campagna)
        codici = CodiceScommessa.objects.filter(allibratore=personaggio).order_by("-created_at")[:30]
        return Response({
            "valore_all": valore_all,
            "can_generare": valore_all > 0 and azioni_ok,
            "in_evento_attivo": azioni_ok,
            "codici": CodiceScommessaSerializer(codici, many=True).data,
        })


class ScommesseConfigPlayerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cfg = get_config_scommesse()
        return Response(config_to_public_dict(cfg))


class ScommesseConfigStaffView(APIView):
    permission_classes = [IsStaffOrMaster]

    def _get_config(self, request):
        campagna_id = request.query_params.get("campagna") or request.data.get("campagna") or get_default_campagna_id()
        obj, _ = ConfigurazioneScommesse.objects.get_or_create(campagna_id=campagna_id)
        return obj

    def get(self, request):
        obj = self._get_config(request)
        return Response(ConfigurazioneScommesseSerializer(obj).data)

    def patch(self, request):
        obj = self._get_config(request)
        ser = ConfigurazioneScommesseSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class ScommesseSquadraStoricoView(APIView):
    """Storico ultimi risultati pubblicati di una squadra."""
    permission_classes = [IsAuthenticated]

    def get(self, request, squadra_id):
        liquidare_calendari_scaduti()
        data = storico_risultati_squadra(squadra_id)
        if not data:
            return Response({"error": "Squadra non trovata."}, status=404)
        return Response(data)


class ScommesseClassifichePlayerView(APIView):
    """Elenco classifiche per tutti gli sport con giornate liquidate."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        liquidare_calendari_scaduti()
        return Response({"classifiche": calcola_classifiche_attive()})


class ScommesseClassificaSportPlayerView(APIView):
    """Classifica dettagliata di un singolo sport/torneo."""
    permission_classes = [IsAuthenticated]

    def get(self, request, sport_id):
        liquidare_calendari_scaduti()
        data = calcola_classifica_sport(sport_id)
        if not data:
            return Response({"error": "Sport non trovato."}, status=404)
        return Response(data)
