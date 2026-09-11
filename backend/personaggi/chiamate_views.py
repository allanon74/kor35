"""API REST per avvio / accettazione / chiusura chiamate vocali e ICE config."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi.campagna_moduli import (
    MODULO_CHIAMATE,
    ModuloStaffGateMixin,
    campagna_da_request,
    user_puo_accedere_modulo,
)
from personaggi.chiamate_vocali import (
    accetta_chiamata,
    avvia_chiamata,
    chiamate_vocali_abilitate,
    chiudi_chiamata,
    ice_servers,
    rifiuta_chiamata,
    scadi_chiamate_vecchie,
    serializza_chiamata,
    storico_chiamate_personaggio,
    user_ha_chiamata_attiva,
    user_is_campaign_staff,
)
from personaggi.models import ChiamataVocale, Personaggio


def _ensure_enabled():
    if not chiamate_vocali_abilitate():
        return Response(
            {"detail": "Chiamate vocali disabilitate su questo nodo."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return None


def _gate_modulo_utente(request):
    campagna = campagna_da_request(request)
    if campagna and not user_puo_accedere_modulo(request.user, campagna, MODULO_CHIAMATE):
        from personaggi.campagna_moduli import get_modulo_accesso, modulo_label, MODULO_ACCESSO_TEST

        modo = get_modulo_accesso(campagna, MODULO_CHIAMATE)
        if modo == MODULO_ACCESSO_TEST:
            detail = "Chiamate vocali: in testing — accesso solo per staff/master."
        else:
            detail = f"{modulo_label(MODULO_CHIAMATE)}: modulo non attivo in questa campagna."
        return Response({"detail": detail}, status=status.HTTP_403_FORBIDDEN)
    return None


class ChiamataIceServersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        gated = _gate_modulo_utente(request)
        if gated:
            return gated
        return Response({"iceServers": ice_servers(request)})


class ChiamataVocaleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        scadi_chiamate_vecchie()
        call = user_ha_chiamata_attiva(request.user)
        if not call:
            return Response({"chiamata": None})
        return Response({"chiamata": serializza_chiamata(call, request.user)})

    def post(self, request):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        data = request.data or {}
        verso_staff = bool(data.get("verso_staff"))
        chiamante_id = data.get("chiamante_id") or data.get("chiamante")
        if not chiamante_id:
            return Response({"detail": "chiamante_id obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        chiamante = Personaggio.objects.filter(
            pk=chiamante_id, proprietario=request.user
        ).select_related("campagna", "proprietario").first()
        if not chiamante:
            return Response({"detail": "Personaggio chiamante non valido."}, status=status.HTTP_400_BAD_REQUEST)
        chiamato = None
        if not verso_staff:
            chiamato_id = data.get("chiamato_id") or data.get("chiamato")
            if not chiamato_id:
                return Response({"detail": "chiamato_id obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
            chiamato = Personaggio.objects.filter(pk=chiamato_id).select_related("proprietario").first()
            if not chiamato:
                return Response({"detail": "Destinatario non trovato."}, status=status.HTTP_404_NOT_FOUND)
        try:
            call = avvia_chiamata(chiamante=chiamante, chiamato=chiamato, verso_staff=verso_staff)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializza_chiamata(call, request.user), status=status.HTTP_201_CREATED)


class ChiamataVocaleStoricoView(APIView):
    """Registro chiamate (inviate / ricevute / perse) per un personaggio del giocatore."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        gated = _gate_modulo_utente(request)
        if gated:
            return gated
        pg_id = request.query_params.get("personaggio_id") or request.query_params.get("personaggio")
        if not pg_id:
            return Response({"detail": "personaggio_id obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        personaggio = (
            Personaggio.objects.filter(pk=pg_id, proprietario=request.user)
            .select_related("campagna")
            .first()
        )
        if not personaggio:
            return Response({"detail": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        try:
            limit = int(request.query_params.get("limit") or 50)
        except (TypeError, ValueError):
            limit = 50
        return Response({"results": storico_chiamate_personaggio(personaggio, limit=limit)})


class ChiamataVocaleCodaStaffView(ModuloStaffGateMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_key = MODULO_CHIAMATE

    def get(self, request):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        scadi_chiamate_vecchie()
        qs = (
            ChiamataVocale.objects.filter(
                verso_staff=True,
                stato=ChiamataVocale.STATO_RINGING,
            )
            .select_related("chiamante", "chiamato", "campagna")
            .order_by("created_at")
        )
        items = [
            serializza_chiamata(c, request.user)
            for c in qs
            if user_is_campaign_staff(request.user, c.campagna)
        ]
        return Response({"results": items})


class _ChiamataAzioneMixin:
    permission_classes = [IsAuthenticated]

    def _get_call(self, pk):
        return (
            ChiamataVocale.objects.select_related(
                "chiamante", "chiamato", "campagna", "accettata_da"
            )
            .filter(pk=pk)
            .first()
        )


class ChiamataVocaleAccettaView(_ChiamataAzioneMixin, APIView):
    def post(self, request, pk):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        call = self._get_call(pk)
        if not call:
            return Response({"detail": "Chiamata non trovata."}, status=status.HTTP_404_NOT_FOUND)
        try:
            call = accetta_chiamata(call, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializza_chiamata(call, request.user))


class ChiamataVocaleRifiutaView(_ChiamataAzioneMixin, APIView):
    def post(self, request, pk):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        call = self._get_call(pk)
        if not call:
            return Response({"detail": "Chiamata non trovata."}, status=status.HTTP_404_NOT_FOUND)
        try:
            call = rifiuta_chiamata(call, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializza_chiamata(call, request.user))


class ChiamataVocaleChiudiView(_ChiamataAzioneMixin, APIView):
    def post(self, request, pk):
        blocked = _ensure_enabled()
        if blocked:
            return blocked
        call = self._get_call(pk)
        if not call:
            return Response({"detail": "Chiamata non trovata."}, status=status.HTTP_404_NOT_FOUND)
        try:
            call = chiudi_chiamata(call, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializza_chiamata(call, request.user))
