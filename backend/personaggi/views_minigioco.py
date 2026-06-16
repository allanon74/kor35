"""API minigioco QR lato giocatore."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi import qr_minigioco
from personaggi.models import Personaggio


class MinigiocoQrCompleteView(APIView):
    """POST — verifica soluzione e sblocca il QR."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        raw_pid = request.data.get("personaggio_id")
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            return Response(
                {"error": "personaggio_id obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        personaggio = Personaggio.objects.filter(pk=pid, proprietario=request.user).first()
        if not personaggio:
            return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)

        client_state = request.data.get("stato") or request.data.get("stato_gioco") or {}
        ok, msg, payload = qr_minigioco.completa_sessione(session_id, personaggio, client_state)
        if not ok:
            return Response(
                {"error": msg, **(payload or {})},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload or {"messaggio": msg}, status=status.HTTP_200_OK)


class MinigiocoQrExpireView(APIView):
    """POST — timer scaduto lato client."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        raw_pid = request.data.get("personaggio_id")
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            return Response(
                {"error": "personaggio_id obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        personaggio = Personaggio.objects.filter(pk=pid, proprietario=request.user).first()
        if not personaggio:
            return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)

        payload = qr_minigioco.expire_sessione(session_id, personaggio, request=request)
        if payload.get("error") and payload.get("tipo_modello") == "minigioco_errore":
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_200_OK)
