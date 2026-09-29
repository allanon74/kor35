"""API giocatore: inventario serie e trasferimento pezzi."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi import qr_random_pool
from personaggi.models import Personaggio, SerieAssegnazione


def _resolve_own_personaggio(request, raw_pid):
    qs = Personaggio.objects.filter(proprietario=request.user)
    if raw_pid not in (None, ""):
        try:
            return qs.filter(pk=int(raw_pid)).first()
        except (TypeError, ValueError):
            return None
    return qs.first()


class SerieInventarioView(APIView):
    """GET — pezzi serie del personaggio, raggruppati (solo eventi non chiusi)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        pg = _resolve_own_personaggio(request, request.query_params.get("personaggio_id"))
        if not pg:
            return Response(
                {"error": "Personaggio non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = qr_random_pool.inventario_serie_per_personaggio(pg, request=request)
        return Response({"serie": data, "personaggio_id": pg.pk})


class SerieAssegnazioneTrasferisciView(APIView):
    """
    POST — trasferisce un pezzo dell'inventario serie a un altro personaggio.

    Body: { personaggio_id, destinatario_personaggio_id }
    Alternativa consigliata ai messaggi/transazioni: aggiorna ownership
    sull'assegnazione (fonte di verità dell'inventario serie).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, assegnazione_id):
        mittente = _resolve_own_personaggio(request, request.data.get("personaggio_id"))
        if not mittente:
            return Response(
                {"error": "Personaggio mittente non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw_dest = request.data.get("destinatario_personaggio_id")
        try:
            dest_id = int(raw_dest)
        except (TypeError, ValueError):
            return Response(
                {"error": "destinatario_personaggio_id obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        destinatario = Personaggio.objects.filter(pk=dest_id).first()
        if not destinatario:
            return Response(
                {"error": "Personaggio destinatario non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            ass = SerieAssegnazione.objects.select_related(
                "serie", "immagine", "personaggio", "oggetto"
            ).get(pk=assegnazione_id)
        except (SerieAssegnazione.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Pezzo serie non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload, err = qr_random_pool.trasferisci_assegnazione_serie(
            assegnazione=ass,
            destinatario=destinatario,
            mittente=mittente,
        )
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "status": "success",
                "messaggio": (
                    f"Trasferito «{payload.get('etichetta')}» a {destinatario.nome}."
                ),
                "pezzo": payload,
            }
        )
