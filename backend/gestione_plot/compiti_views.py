"""API calendario compiti staff / master / aiuto-staff."""
from __future__ import annotations

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.models import User

from personaggi.models import (
    CAMPAGNA_ROLE_HELPER,
    CAMPAGNA_ROLES_COMPITO,
    CampagnaUtente,
)

from .compiti_automatici import (
    CAMPAGNA_ROLES_COMPITO_AUTOMATICO,
    COMPITO_AUTOMATICO_META,
    conteggi_proposte_in_valutazione,
    ensure_default_compiti_automatici,
    list_automatic_compiti_payloads,
    serialize_config_row,
    sync_assegnatari_automatico,
)
from .models import (
    CalendarioFeedToken,
    StaffCompito,
    StaffCompitoAssegnazione,
    StaffCompitoAutomatico,
)
from .serializers import StaffCompitoSerializer
from .views import (
    _get_active_campaign_for_request,
    _is_campaign_master_plus,
    _is_campaign_staff_plus,
    _campaign_role_for_request,
)


def _is_campaign_helper(request) -> bool:
    return _campaign_role_for_request(request) == CAMPAGNA_ROLE_HELPER


def _can_see_compiti(request) -> bool:
    if _is_campaign_master_plus(request) or _is_campaign_staff_plus(request):
        return True
    return _is_campaign_helper(request)


def _user_ids_assegnabili(campagna):
    if not campagna:
        return User.objects.none()
    ids = CampagnaUtente.objects.filter(
        campagna=campagna,
        attivo=True,
        ruolo__in=CAMPAGNA_ROLES_COMPITO,
    ).values_list("user_id", flat=True)
    return User.objects.filter(pk__in=ids)


def _sync_assegnatari(compito: StaffCompito, user_ids: list[int], *, campagna) -> None:
    allowed = set(_user_ids_assegnabili(campagna).values_list("pk", flat=True))
    wanted = {int(uid) for uid in user_ids if int(uid) in allowed}
    existing = {row.user_id: row for row in compito.assegnazioni.all()}
    for uid, row in list(existing.items()):
        if uid not in wanted:
            row.delete()
    for uid in wanted:
        if uid not in existing:
            StaffCompitoAssegnazione.objects.create(compito=compito, user_id=uid)


def _reset_push_flags(compito: StaffCompito) -> None:
    for row in compito.assegnazioni.all():
        if row.push_preavviso_inviata or row.push_scadenza_inviata:
            row.push_preavviso_inviata = False
            row.push_scadenza_inviata = False
            row.save(update_fields=["push_preavviso_inviata", "push_scadenza_inviata", "updated_at"])


class IsCalendarioCompitiPermission(permissions.BasePermission):
    """Lettura per master/staffer/helper; scrittura solo master+."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        action = getattr(view, "action", None)
        if action == "candidati":
            return _is_campaign_master_plus(request)
        if action == "automatici":
            if request.method in permissions.SAFE_METHODS:
                return _is_campaign_master_plus(request) or _is_campaign_staff_plus(request)
            return _is_campaign_master_plus(request)
        if action in ("completa", "feed_token", "rigenera_feed_token", "miei"):
            return _can_see_compiti(request)
        if request.method in permissions.SAFE_METHODS:
            return _can_see_compiti(request)
        return _is_campaign_master_plus(request)


class StaffCompitoViewSet(viewsets.ModelViewSet):
    serializer_class = StaffCompitoSerializer
    permission_classes = [IsCalendarioCompitiPermission]
    pagination_class = None

    def _wants_miei(self) -> bool:
        if self.action == "miei":
            return True
        return str(self.request.query_params.get("miei") or "") in ("1", "true", "yes")

    def get_queryset(self):
        campagna = _get_active_campaign_for_request(self.request)
        qs = (
            StaffCompito.objects.filter(campagna=campagna)
            .select_related("creato_da")
            .prefetch_related("assegnazioni__user")
        )
        if self._wants_miei():
            qs = qs.filter(assegnazioni__user=self.request.user, attivo=True).distinct()
        elif not _is_campaign_master_plus(self.request):
            qs = qs.filter(assegnazioni__user=self.request.user).distinct()
        return qs.order_by("scadenza", "titolo")

    def _with_automatici(self, manual_data: list) -> list:
        campagna = _get_active_campaign_for_request(self.request)
        only_mine = self._wants_miei() or not _is_campaign_master_plus(self.request)
        automatici = list_automatic_compiti_payloads(
            campagna=campagna,
            request_user=self.request.user,
            only_assigned_to_user=only_mine,
        )
        return list(automatici) + list(manual_data)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)
        return Response(self._with_automatici(serializer.data))

    def perform_create(self, serializer):
        campagna = _get_active_campaign_for_request(self.request)
        assegnatari = serializer.validated_data.pop("assegnatari", [])
        with transaction.atomic():
            compito = serializer.save(campagna=campagna, creato_da=self.request.user)
            _sync_assegnatari(compito, assegnatari, campagna=campagna)

    def perform_update(self, serializer):
        campagna = _get_active_campaign_for_request(self.request)
        assegnatari = serializer.validated_data.pop("assegnatari", None)
        prev_scadenza = serializer.instance.scadenza
        prev_preavviso = serializer.instance.preavviso_minuti
        with transaction.atomic():
            compito = serializer.save()
            if assegnatari is not None:
                _sync_assegnatari(compito, assegnatari, campagna=campagna)
            if compito.scadenza != prev_scadenza or compito.preavviso_minuti != prev_preavviso:
                _reset_push_flags(compito)

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=["get"], url_path="miei")
    def miei(self, request):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(self._with_automatici(serializer.data))

    @action(detail=False, methods=["get"], url_path="candidati")
    def candidati(self, request):
        if not _is_campaign_master_plus(request):
            return Response({"detail": "Solo master."}, status=status.HTTP_403_FORBIDDEN)
        campagna = _get_active_campaign_for_request(request)
        memberships = CampagnaUtente.objects.filter(
            campagna=campagna,
            attivo=True,
            ruolo__in=CAMPAGNA_ROLES_COMPITO,
        ).select_related("user")
        rows = [
            {
                "id": m.user_id,
                "username": m.user.username,
                "first_name": m.user.first_name,
                "last_name": m.user.last_name,
                "ruolo": m.ruolo,
            }
            for m in memberships.order_by("ruolo", "user__username")
        ]
        return Response(rows)

    @action(detail=False, methods=["get", "put", "patch"], url_path="automatici")
    def automatici(self, request):
        """Config compiti automatici (GET lista; PUT/PATCH aggiorna assegnatari per codice)."""
        campagna = _get_active_campaign_for_request(request)
        if not campagna:
            return Response({"detail": "Campagna non trovata."}, status=status.HTTP_400_BAD_REQUEST)

        if request.method in ("PUT", "PATCH"):
            if not _is_campaign_master_plus(request):
                return Response({"detail": "Solo master."}, status=status.HTTP_403_FORBIDDEN)
            items = request.data.get("items")
            if items is None and request.data.get("codice"):
                items = [request.data]
            if not isinstance(items, list):
                return Response(
                    {"detail": "Invia {items: [{codice, assegnatari, attivo?}]}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ensure_default_compiti_automatici(campagna)
            with transaction.atomic():
                for raw in items:
                    codice = str((raw or {}).get("codice") or "").strip()
                    if not codice:
                        continue
                    config = StaffCompitoAutomatico.objects.filter(
                        campagna=campagna, codice=codice
                    ).first()
                    if not config:
                        continue
                    if "attivo" in (raw or {}):
                        config.attivo = bool(raw.get("attivo"))
                        config.save(update_fields=["attivo", "updated_at"])
                    if "assegnatari" in (raw or {}):
                        ids = raw.get("assegnatari") or []
                        if not isinstance(ids, list):
                            continue
                        sync_assegnatari_automatico(config, ids, campagna=campagna)

        ensure_default_compiti_automatici(campagna)
        conteggi = conteggi_proposte_in_valutazione(campagna)
        configs = (
            StaffCompitoAutomatico.objects.filter(campagna=campagna)
            .prefetch_related("assegnazioni__user")
            .order_by("codice")
        )
        by_codice = {c.codice: c for c in configs}
        ordered = [
            by_codice[c]
            for c in sorted(
                COMPITO_AUTOMATICO_META.keys(),
                key=lambda x: COMPITO_AUTOMATICO_META[x]["ordine"],
            )
            if c in by_codice
        ]
        candidati = []
        if _is_campaign_master_plus(request):
            memberships = CampagnaUtente.objects.filter(
                campagna=campagna,
                attivo=True,
                ruolo__in=CAMPAGNA_ROLES_COMPITO_AUTOMATICO,
            ).select_related("user")
            candidati = [
                {
                    "id": m.user_id,
                    "username": m.user.username,
                    "first_name": m.user.first_name,
                    "last_name": m.user.last_name,
                    "ruolo": m.ruolo,
                }
                for m in memberships.order_by("ruolo", "user__username")
            ]
        return Response(
            {
                "items": [
                    serialize_config_row(c, conteggio=conteggi.get(c.codice, 0)) for c in ordered
                ],
                "candidati": candidati,
            }
        )

    @action(detail=True, methods=["post"], url_path="completa")
    def completa(self, request, pk=None):
        compito = self.get_object()
        row = compito.assegnazioni.filter(user=request.user).first()
        if not row:
            return Response({"detail": "Compito non assegnato a te."}, status=status.HTTP_403_FORBIDDEN)
        undo = bool(request.data.get("undo"))
        if undo:
            row.completato_at = None
        elif row.completato_at is None:
            row.completato_at = timezone.now()
        row.save(update_fields=["completato_at", "updated_at"])
        compito = self.get_queryset().get(pk=compito.pk)
        serializer = self.get_serializer(compito)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="feed-token")
    def feed_token(self, request):
        from .compiti_ics import calendario_feed_payload

        return Response(calendario_feed_payload(request.user))

    @action(detail=False, methods=["post"], url_path="feed-token/rigenera")
    def rigenera_feed_token(self, request):
        from .compiti_ics import calendario_feed_payload

        token_row, _ = CalendarioFeedToken.objects.get_or_create(user=request.user)
        token_row.rigenera()
        return Response(calendario_feed_payload(request.user))


class CalendarioCompitiIcsView(APIView):
    """Feed iCal pubblico-con-segreto (i client calendario non inviano JWT)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        from .compiti_ics import (
            assegnazioni_queryset_for_ics,
            build_calendario_ics,
            eventi_queryset_for_ics,
            user_ics_includes_compiti,
        )

        raw = str(request.query_params.get("token") or "").strip()
        if not raw:
            return Response({"detail": "Token mancante."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token_row = CalendarioFeedToken.objects.select_related("user").get(token=raw)
        except (CalendarioFeedToken.DoesNotExist, ValueError):
            return Response({"detail": "Token non valido."}, status=status.HTTP_404_NOT_FOUND)

        include_compiti = user_ics_includes_compiti(token_row.user)
        assegnazioni = assegnazioni_queryset_for_ics(token_row.user) if include_compiti else []
        name = "KOR35 — eventi e compiti" if include_compiti else "KOR35 — eventi"
        body = build_calendario_ics(
            eventi=list(eventi_queryset_for_ics()),
            assegnazioni=assegnazioni,
            calendar_name=name,
            include_compiti=include_compiti,
        )
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'inline; filename="kor35-calendario.ics"'
        return response
