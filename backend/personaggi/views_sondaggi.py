"""API sondaggio: scheda giocatore e importazione staff da Google Form."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.permissions import IsStaffOrMaster, _get_active_campaign_for_request
from personaggi.models import Personaggio
from personaggi.sondaggi_google import ErroreModuloGoogle
from personaggi.sondaggi_models import RispostaSondaggio, Sondaggio
from personaggi.sondaggi_service import (
    applica_premi_da_richiesta,
    eroga_premi_mancanti,
    importa_modulo,
    inoltra_sospese,
    registra_risposta,
    serializza_per_giocatore,
    serializza_staff,
)


def _messaggio(exc: Exception) -> str:
    messaggi = getattr(exc, "messages", None)
    if messaggi:
        return " ".join(str(voce) for voce in messaggi)
    return str(exc)


def _campagna_staff(request):
    campagna = _get_active_campaign_for_request(request)
    if not campagna:
        return None, Response({"error": "Nessuna campagna attiva."}, status=400)
    return campagna, None


def _personaggio_proprietario(request):
    raw = request.query_params.get("personaggio_id") or (request.data or {}).get("personaggio_id")
    if not raw:
        return None, Response({"error": "personaggio_id richiesto."}, status=400)
    personaggio = Personaggio.objects.filter(pk=raw, proprietario=request.user).first()
    if not personaggio:
        return None, Response({"error": "Personaggio non trovato."}, status=404)
    return personaggio, None


def _sondaggio_campagna(campagna, sondaggio_id):
    sondaggio = Sondaggio.objects.filter(pk=sondaggio_id, campagna=campagna).first()
    if not sondaggio:
        return None, Response({"error": "Sondaggio non trovato."}, status=404)
    return sondaggio, None


class SondaggiGiocatoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        personaggio, errore = _personaggio_proprietario(request)
        if errore:
            return errore
        aperti = list(
            Sondaggio.objects.filter(campagna=personaggio.campagna, attivo=True).order_by("-created_at")
        )
        if request.query_params.get("breve") == "1":
            risposte = {
                riga.sondaggio_id: riga
                for riga in RispostaSondaggio.objects.filter(
                    personaggio=personaggio,
                    sondaggio__in=aperti,
                )
            }
            da_compilare = sum(1 for sondaggio in aperti if sondaggio.id not in risposte)
            return Response({
                "visibile": bool(aperti),
                "da_compilare": da_compilare,
            })
        mie = {
            riga.sondaggio_id: riga
            for riga in RispostaSondaggio.objects.filter(personaggio=personaggio, sondaggio__in=aperti)
        }
        return Response({
            "sondaggi": [serializza_per_giocatore(sondaggio, mie.get(sondaggio.id)) for sondaggio in aperti],
        })


class SondaggioRispostaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sondaggio_id):
        personaggio, errore = _personaggio_proprietario(request)
        if errore:
            return errore
        sondaggio = Sondaggio.objects.filter(pk=sondaggio_id, campagna=personaggio.campagna).first()
        if not sondaggio:
            return Response({"error": "Sondaggio non trovato."}, status=404)
        try:
            risposta, creata = registra_risposta(
                sondaggio,
                personaggio,
                request.user,
                request.data.get("risposte"),
            )
        except ValidationError as exc:
            return Response({"error": _messaggio(exc)}, status=400)
        return Response(
            serializza_per_giocatore(sondaggio, risposta),
            status=201 if creata else 200,
        )


class SondaggiStaffView(APIView):
    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        righe = Sondaggio.objects.filter(campagna=campagna).order_by("-created_at")
        return Response({"sondaggi": [serializza_staff(riga) for riga in righe]})

    def post(self, request):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        attivo = request.data.get("attivo", True)
        if not isinstance(attivo, bool):
            return Response({"error": "attivo deve essere vero o falso."}, status=400)
        try:
            sondaggio, creato = importa_modulo(campagna, request.data.get("url") or "", attivo=attivo)
        except ErroreModuloGoogle as exc:
            return Response({"error": str(exc)}, status=400)
        return Response(serializza_staff(sondaggio), status=201 if creato else 200)


class SondaggioStaffDettaglioView(APIView):
    permission_classes = [IsStaffOrMaster]

    def get(self, request, sondaggio_id):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        sondaggio, errore = _sondaggio_campagna(campagna, sondaggio_id)
        if errore:
            return errore
        return Response(serializza_staff(sondaggio, con_risposte=True))

    def patch(self, request, sondaggio_id):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        sondaggio, errore = _sondaggio_campagna(campagna, sondaggio_id)
        if errore:
            return errore
        if "titolo" in request.data:
            titolo = str(request.data.get("titolo") or "").strip()
            if not titolo:
                return Response({"error": "Il titolo non può essere vuoto."}, status=400)
            sondaggio.titolo = titolo[:200]
        if "descrizione" in request.data:
            sondaggio.descrizione = str(request.data.get("descrizione") or "")[:8000]
        for campo in ("attivo", "consenti_modifica", "inoltra_email"):
            if campo in request.data:
                valore = request.data.get(campo)
                if not isinstance(valore, bool):
                    return Response({"error": f"{campo} deve essere vero o falso."}, status=400)
                setattr(sondaggio, campo, valore)
        try:
            applica_premi_da_richiesta(sondaggio, request.data)
        except ValidationError as exc:
            return Response({"error": _messaggio(exc)}, status=400)
        sondaggio.save()
        return Response(serializza_staff(sondaggio, con_risposte=True))

    def delete(self, request, sondaggio_id):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        sondaggio, errore = _sondaggio_campagna(campagna, sondaggio_id)
        if errore:
            return errore
        sondaggio.delete()
        return Response(status=204)


class SondaggioStaffAggiornaView(APIView):
    permission_classes = [IsStaffOrMaster]

    def post(self, request, sondaggio_id):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        sondaggio, errore = _sondaggio_campagna(campagna, sondaggio_id)
        if errore:
            return errore
        try:
            aggiornato, _ = importa_modulo(campagna, sondaggio.google_form_url, attivo=None)
        except ErroreModuloGoogle as exc:
            return Response({"error": str(exc)}, status=400)
        return Response(serializza_staff(aggiornato, con_risposte=True))


class SondaggioStaffInoltraView(APIView):
    permission_classes = [IsStaffOrMaster]

    def post(self, request, sondaggio_id):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        sondaggio, errore = _sondaggio_campagna(campagna, sondaggio_id)
        if errore:
            return errore
        esito = inoltra_sospese(sondaggio)
        payload = serializza_staff(sondaggio, con_risposte=True)
        payload["inoltro"] = esito
        return Response(payload)


class SondaggioStaffPremiView(APIView):
    permission_classes = [IsStaffOrMaster]

    def post(self, request, sondaggio_id):
        campagna, errore = _campagna_staff(request)
        if errore:
            return errore
        sondaggio, errore = _sondaggio_campagna(campagna, sondaggio_id)
        if errore:
            return errore
        erogati = eroga_premi_mancanti(sondaggio)
        payload = serializza_staff(sondaggio, con_risposte=True)
        payload["premi_appena_erogati"] = erogati
        return Response(payload)
