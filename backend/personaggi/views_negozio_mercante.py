"""
API giocatore e staff per negozi mercante.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi.models import FEATURE_NEGOZI_MERCANTE
from personaggi.views_staff import _campaign_feature_filter, _get_active_campaign
from personaggi.negozio_mercante_models import NegozioMercante, NegozioMercanteVoce
from personaggi.negozio_mercante_readiness import valuta_prontezza_negozio
from personaggi.negozio_mercante_models import NegozioMercanteMovimento
from personaggi.negozio_mercante_service import (
    acquista_stock,
    acquista_voce,
    build_listino,
    negozi_corporativi_per_personaggio,
    preview_vendita_oggetto,
    vendi_oggetto_a_negozio,
)
from personaggi.models import Personaggio, QrCode
from gestione_plot.permissions import IsStaffOrMaster
from personaggi.serializers_negozio_mercante import NegozioMercanteSerializer, NegozioMercanteVoceSerializer
from personaggi.views import _can_operate_in_campaign


def _get_pg(request, char_id):
    pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
    if not _can_operate_in_campaign(request.user, pg.campagna, needs_master=False):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("Non autorizzato per la campagna del personaggio.")
    return pg


class NegozioMercanteGiocatoreViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="corporativi")
    def corporativi(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        negozi = negozi_corporativi_per_personaggio(pg)
        data = [
            {
                "id": str(n.id),
                "nome": n.nome,
                "descrizione": n.descrizione,
            }
            for n in negozi
        ]
        return Response(data)

    @action(detail=True, methods=["get"], url_path="listino")
    def listino(self, request, pk=None):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        negozio = get_object_or_404(NegozioMercante, pk=pk, attivo=True)
        return Response(build_listino(negozio, pg))

    @action(detail=True, methods=["post"], url_path="acquista")
    def acquista(self, request, pk=None):
        char_id = request.data.get("char_id")
        voce_id = request.data.get("voce_id")
        stock_id = request.data.get("stock_id")
        slot_corpo = request.data.get("slot_corpo")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        negozio = get_object_or_404(NegozioMercante, pk=pk, attivo=True)
        try:
            if stock_id:
                result = acquista_stock(negozio, pg, stock_id, slot_corpo=slot_corpo)
            elif voce_id:
                result = acquista_voce(negozio, pg, voce_id, slot_corpo=slot_corpo)
            else:
                return Response({"error": "voce_id o stock_id richiesto."}, status=400)
            return Response(result)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=["post"], url_path="vendi")
    def vendi(self, request, pk=None):
        char_id = request.data.get("char_id")
        oggetto_id = request.data.get("oggetto_id")
        if not char_id or not oggetto_id:
            return Response({"error": "char_id e oggetto_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        negozio = get_object_or_404(NegozioMercante, pk=pk, attivo=True)
        try:
            return Response(vendi_oggetto_a_negozio(negozio, pg, oggetto_id))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=["get"], url_path="preview-vendita")
    def preview_vendita(self, request, pk=None):
        char_id = request.query_params.get("char_id")
        oggetto_id = request.query_params.get("oggetto_id")
        if not char_id or not oggetto_id:
            return Response({"error": "char_id e oggetto_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        negozio = get_object_or_404(NegozioMercante, pk=pk, attivo=True)
        try:
            return Response(preview_vendita_oggetto(negozio, pg, oggetto_id))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class NegozioMercanteStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = NegozioMercanteSerializer

    def get_queryset(self):
        qs = NegozioMercante.objects.all().select_related("qr_code", "inventario", "campagna")
        return _campaign_feature_filter(self.request, qs, FEATURE_NEGOZI_MERCANTE)

    def perform_create(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))

    @action(detail=True, methods=["post"], url_path="associa-qr")
    def associa_qr(self, request, pk=None):
        negozio = self.get_object()
        qr_id = request.data.get("qr_id")
        force = bool(request.data.get("force", False))

        if qr_id in (None, ""):
            from personaggi.negozio_mercante_avista import scollega_qr_da_negozio

            scollega_qr_da_negozio(negozio)
            return Response({"status": "success", "message": "QR scollegato.", "qr_id": None})

        try:
            qr = QrCode.objects.select_related("vista").get(pk=qr_id)
        except QrCode.DoesNotExist:
            return Response({"error": "QR Code non trovato."}, status=status.HTTP_404_NOT_FOUND)

        from personaggi.negozio_mercante_avista import associa_qr_a_negozio

        ok, conflict = associa_qr_a_negozio(negozio, qr, force=force)
        if not ok:
            return Response(conflict, status=status.HTTP_409_CONFLICT)

        return Response(
            {
                "status": "success",
                "message": "QR associato al negozio.",
                "qr_id": qr.id,
                "negozio_id": str(negozio.id),
            }
        )

    @action(detail=True, methods=["get"], url_path="readiness")
    def readiness(self, request, pk=None):
        negozio = self.get_object()
        return Response(valuta_prontezza_negozio(negozio))

    @action(detail=True, methods=["get"], url_path="movimenti")
    def movimenti(self, request, pk=None):
        negozio = self.get_object()
        qs = (
            NegozioMercanteMovimento.objects.filter(negozio=negozio)
            .select_related("personaggio")
            .order_by("-created_at")[:80]
        )
        rows = [
            {
                "id": str(m.id),
                "tipo": m.tipo,
                "importo": int(m.importo),
                "saldo_dopo": int(m.saldo_dopo),
                "nota": m.nota,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "personaggio": m.personaggio.nome if m.personaggio_id else None,
            }
            for m in qs
        ]
        return Response(rows)


class NegozioMercanteVoceStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = NegozioMercanteVoceSerializer

    def get_queryset(self):
        qs = NegozioMercanteVoce.objects.select_related(
            "negozio",
            "oggetto_base",
            "oggetto",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
        )
        negozio_id = self.request.query_params.get("negozio")
        if negozio_id:
            qs = qs.filter(negozio_id=negozio_id)
        return qs


class NegozioMercanteQrListinoView(APIView):
    """Listino da scan QR (senza conoscere UUID negozio in anticipo)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, qrcode_id):
        from personaggi.models import QrCode

        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        qr = get_object_or_404(QrCode, pk=qrcode_id)
        negozio = get_object_or_404(NegozioMercante, qr_code=qr, attivo=True)
        payload = build_listino(negozio, pg)
        payload["qrcode_id"] = qr.id
        return Response(payload)
