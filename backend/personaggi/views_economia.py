"""
API economia duale: summary, trasferimento deposito→corrente, log movimenti.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.permissions import IsStaffOrMaster
from personaggi.campagna_moduli import MODULO_CONTO_DEPOSITO, modulo_gate_response
from personaggi.economia_crediti import (
    economia_summary,
    get_economia_config,
    trasferisci_deposito_a_corrente,
)
from personaggi.models import CreditoMovimento, Personaggio, PuntiCaratteristicaMovimento
from personaggi.scommesse_evento import personaggio_in_evento_attivo
from personaggi.serializers import CreditoMovimentoSerializer


def _get_pg(request):
    char_id = request.query_params.get("char_id") or request.data.get("char_id")
    if not char_id:
        return None, Response({"error": "char_id richiesto."}, status=400)
    pg = Personaggio.objects.filter(pk=char_id, proprietario=request.user).first()
    if not pg:
        return None, Response({"error": "Personaggio non trovato."}, status=404)
    return pg, None


class EconomiaSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pg, err = _get_pg(request)
        if err:
            return err
        evento = personaggio_in_evento_attivo(pg)
        return Response(economia_summary(pg, evento=evento, user=request.user))


class EconomiaTrasferisciDepositoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pg, err = _get_pg(request)
        if err:
            return err
        gate = modulo_gate_response(pg, MODULO_CONTO_DEPOSITO, user=request.user)
        if gate:
            return gate
        evento = personaggio_in_evento_attivo(pg)
        if not evento:
            return Response(
                {"error": "Trasferimento consentito solo durante un evento attivo a cui partecipi."},
                status=400,
            )
        try:
            importo = Decimal(str(request.data.get("importo", "0")))
        except (InvalidOperation, TypeError, ValueError):
            return Response({"error": "Importo non valido."}, status=400)
        try:
            trasferito = trasferisci_deposito_a_corrente(
                pg, importo, evento, force=False, user=request.user
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        return Response({
            "status": "success",
            "importo": str(trasferito),
            "economia": economia_summary(pg, evento=evento, user=request.user),
        })


class EconomiaMovimentiView(APIView):
    """Log lazy: movimenti crediti e/o PC."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        pg, err = _get_pg(request)
        if err:
            return err
        tipo = (request.query_params.get("tipo") or "crediti").strip().lower()
        conto = (request.query_params.get("conto") or "").strip().upper() or None
        try:
            limit = min(100, max(1, int(request.query_params.get("limit") or 40)))
        except (TypeError, ValueError):
            limit = 40
        try:
            offset = max(0, int(request.query_params.get("offset") or 0))
        except (TypeError, ValueError):
            offset = 0

        if tipo == "pc":
            qs = PuntiCaratteristicaMovimento.objects.filter(personaggio=pg).order_by("-data")
            total = qs.count()
            rows = list(qs[offset : offset + limit])
            data = [
                {
                    "importo": r.importo,
                    "descrizione": r.descrizione,
                    "data": r.data,
                }
                for r in rows
            ]
            return Response({"tipo": "pc", "total": total, "offset": offset, "results": data})

        qs = CreditoMovimento.objects.filter(personaggio=pg).order_by("-data")
        if conto in ("CORRENTE", "DEPOSITO"):
            qs = qs.filter(conto=conto)
        total = qs.count()
        rows = qs[offset : offset + limit]
        return Response({
            "tipo": "crediti",
            "conto": conto,
            "total": total,
            "offset": offset,
            "results": CreditoMovimentoSerializer(rows, many=True).data,
        })


class StaffEconomiaCampagnaConfigView(APIView):
    """GET/PATCH config economia per campagna (staff tool economia-crediti)."""

    permission_classes = [IsStaffOrMaster]

    def _campagna(self, request):
        from personaggi.models import Campagna

        camp_id = request.query_params.get("campagna_id") or request.data.get("campagna_id")
        if not camp_id:
            return None, Response({"error": "campagna_id richiesto."}, status=400)
        campagna = Campagna.objects.filter(pk=camp_id).first()
        if not campagna:
            return None, Response({"error": "Campagna non trovata."}, status=404)
        return campagna, None

    def get(self, request):
        campagna, err = self._campagna(request)
        if err:
            return err
        return Response({
            "campagna_id": str(campagna.id),
            "config": get_economia_config(campagna),
            "config_raw": campagna.economia_config or {},
        })

    def patch(self, request):
        from personaggi.economia_crediti import apply_economia_config

        campagna, err = self._campagna(request)
        if err:
            return err
        payload = request.data.get("economia_config")
        if payload is None:
            payload = {
                k: request.data[k]
                for k in (
                    "frazione_trasferimento_stipendio",
                    "fattore_valore_deposito",
                    "categorie_spesa_deposito",
                )
                if k in request.data
            }
        try:
            cfg = apply_economia_config(campagna, payload, merge=True)
        except ValidationError as e:
            return Response({"error": e.message_dict if hasattr(e, "message_dict") else str(e)}, status=400)
        return Response({"campagna_id": str(campagna.id), "config": cfg})


class StaffEconomiaPersonaggioView(APIView):
    """GET saldi + POST trasferimento forzato staff."""

    permission_classes = [IsStaffOrMaster]

    def get(self, request, pk):
        pg = Personaggio.all_objects.filter(pk=pk).first()
        if not pg:
            return Response({"error": "Personaggio non trovato."}, status=404)
        evento = personaggio_in_evento_attivo(pg)
        return Response({
            **economia_summary(pg, evento=evento, user=request.user),
            "punti_caratteristica": pg.punti_caratteristica,
            "personaggio_id": pg.id,
            "personaggio_nome": pg.nome,
            "movimenti_recenti": CreditoMovimentoSerializer(
                CreditoMovimento.objects.filter(personaggio=pg).order_by("-data")[:40],
                many=True,
            ).data,
        })

    def post(self, request, pk):
        from gestione_plot.models import Evento

        pg = Personaggio.all_objects.filter(pk=pk).first()
        if not pg:
            return Response({"error": "Personaggio non trovato."}, status=404)
        azione = (request.data.get("azione") or "trasferisci").strip().lower()
        if azione != "trasferisci":
            return Response({"error": "Azione non supportata."}, status=400)
        try:
            importo = Decimal(str(request.data.get("importo", "0")))
        except (InvalidOperation, TypeError, ValueError):
            return Response({"error": "Importo non valido."}, status=400)
        evento_id = request.data.get("evento_id")
        evento = None
        if evento_id:
            evento = Evento.objects.filter(pk=evento_id).first()
        if not evento:
            evento = personaggio_in_evento_attivo(pg)
        if not evento:
            return Response({"error": "Evento richiesto per il trasferimento."}, status=400)
        try:
            trasferito = trasferisci_deposito_a_corrente(
                pg, importo, evento, force=True, user=request.user,
                descrizione=request.data.get("motivo") or "Trasferimento staff deposito→corrente",
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        return Response({
            "status": "success",
            "importo": str(trasferito),
            "economia": economia_summary(pg, evento=evento, user=request.user),
        })
