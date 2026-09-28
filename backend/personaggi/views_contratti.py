"""API giocatore e staff per i contratti."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from personaggi.campagna_moduli import (
    MODULO_CONTRATTI,
    campagna_da_request,
    modulo_visibile_in_staff,
)
from personaggi.contratti_effetti import EFFETTI_REGISTRY
from personaggi.contratti_models import STATI_OCCUPANO_SLOT, Contratto, ContrattoAdempimento, ModelloContratto
from personaggi.contratti_service import (
    attiva_contratto,
    annulla_proposta,
    associa_post,
    crea_preset,
    crea_proposta,
    firma_contratto,
    marca_scaduti,
    qr_png_base64,
    registra_servizio,
    rifiuta_contratto,
    salda_debito,
    riepilogo_ruoli,
    salva_modello,
    segnala_ferita,
    serializza_contratto,
    serializza_modello,
    slot_liberi,
    slot_totali,
    slot_usati,
    tab_visibile,
    user_is_staff_campagna,
    conferma_adempimento,
)
from personaggi.models import Carriera, Personaggio


def _pg(request):
    raw = request.query_params.get("personaggio_id") or request.data.get("personaggio_id")
    try:
        pid = int(raw)
    except (TypeError, ValueError):
        return None
    return Personaggio.objects.filter(pk=pid, proprietario=request.user).select_related("campagna").first()


def _errore(exc: ValidationError):
    if hasattr(exc, "messages"):
        testo = " ".join(str(m) for m in exc.messages)
    else:
        testo = str(exc)
    return Response({"error": testo}, status=status.HTTP_400_BAD_REQUEST)


class ContrattiAccessoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pg = _pg(request)
        if not pg:
            return Response({"visibile": False})
        return Response(
            {
                "visibile": tab_visibile(pg, request.user),
                "slot_totali": slot_totali(pg),
                "slot_usati": slot_usati(pg),
                "slot_liberi": slot_liberi(pg),
            }
        )


class ContrattiSchedaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pg = _pg(request)
        if not pg:
            return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        marca_scaduti()
        from personaggi.models import get_active_korp_membership

        membership = get_active_korp_membership(pg)
        modelli = []
        if membership and getattr(membership.carriera, "sottoscrive_contratti", False):
            modelli = [
                serializza_modello(m)
                for m in ModelloContratto.objects.filter(
                    korp=membership.carriera, attivo=True, campagna=pg.campagna
                ).prefetch_related("parametri", "effetti", "voci__effetti")
            ]
        contratti = (
            Contratto.objects.filter(proponente=pg)
            | Contratto.objects.filter(cliente=pg)
        ).distinct().select_related("proponente", "cliente").prefetch_related("adempimenti").order_by("-created_at")
        return Response(
            {
                "visibile": tab_visibile(pg, request.user),
                "slot_totali": slot_totali(pg),
                "slot_usati": slot_usati(pg),
                "slot_liberi": slot_liberi(pg),
                "puo_proporre": slot_liberi(pg) > 0,
                "riepilogo": riepilogo_ruoli(pg),
                "modelli": modelli,
                "contratti": [serializza_contratto(c, pg.pk) for c in contratti[:80]],
            }
        )


class ContrattoPropostaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pg = _pg(request)
        if not pg:
            return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        modello = get_object_or_404(ModelloContratto, pk=request.data.get("modello_id"))
        evento = None
        if request.data.get("evento_id"):
            from gestione_plot.models import Evento

            evento = get_object_or_404(Evento, pk=request.data.get("evento_id"))
        try:
            contratto = crea_proposta(
                pg,
                modello,
                request.data.get("parametri") or {},
                request.data.get("voci_ids") or [],
                evento=evento,
            )
        except ValidationError as exc:
            return _errore(exc)
        dati = serializza_contratto(contratto, pg.pk)
        if contratto.qr_code_id:
            dati["qr_png"] = qr_png_base64(contratto.qr_code_id)
        return Response(dati, status=status.HTTP_201_CREATED)


class ContrattoAzioneView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, contratto_id, azione):
        pg = _pg(request)
        if not pg:
            return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        contratto = get_object_or_404(
            Contratto.objects.select_related("proponente", "cliente", "modello__korp"),
            pk=contratto_id,
        )
        try:
            if azione == "firma":
                firma_contratto(contratto, pg)
            elif azione == "rifiuta":
                rifiuta_contratto(contratto, pg)
            elif azione == "annulla":
                annulla_proposta(contratto, pg)
            elif azione == "attiva":
                attiva_contratto(contratto, pg, staff=False)
            elif azione == "ferita":
                segnala_ferita(contratto, pg)
            elif azione == "servizio":
                evento = None
                if request.data.get("evento_id"):
                    from gestione_plot.models import Evento

                    evento = get_object_or_404(Evento, pk=request.data.get("evento_id"))
                registra_servizio(contratto, pg, request.data.get("quantita"), evento=evento, note=request.data.get("note") or "")
            elif azione == "associa-post":
                from social.models import SocialPost

                post = get_object_or_404(SocialPost, pk=request.data.get("post_id"))
                associa_post(contratto, pg, post)
            elif azione == "conferma":
                ademp = get_object_or_404(ContrattoAdempimento, pk=request.data.get("adempimento_id"), contratto=contratto)
                conferma_adempimento(ademp, attore=pg, staff=False)
            else:
                return Response({"error": "Azione sconosciuta."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return _errore(exc)
        contratto.refresh_from_db()
        return Response(serializza_contratto(contratto, pg.pk))


class ContrattoQrImmagineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, contratto_id):
        pg = _pg(request)
        contratto = get_object_or_404(Contratto, pk=contratto_id)
        if not pg or pg.pk not in (contratto.proponente_id, contratto.cliente_id):
            return Response({"error": "Non autorizzato."}, status=status.HTTP_403_FORBIDDEN)
        if not contratto.qr_code_id:
            return Response({"error": "QR assente."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"qr_code_id": contratto.qr_code_id, "qr_png": qr_png_base64(contratto.qr_code_id)})


class ContrattiStaffListaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        campagna = campagna_da_request(request)
        if not user_is_staff_campagna(request.user, campagna):
            return Response({"error": "Solo staff."}, status=status.HTTP_403_FORBIDDEN)
        if not modulo_visibile_in_staff(campagna, MODULO_CONTRATTI):
            return Response({"error": "Modulo contratti spento."}, status=status.HTTP_403_FORBIDDEN)
        modelli = ModelloContratto.objects.filter(campagna=campagna).select_related("korp").prefetch_related(
            "parametri", "effetti", "voci__effetti"
        )
        return Response(
            {
                "effetti": EFFETTI_REGISTRY,
                "korp": [
                    {
                        "id": c.pk,
                        "nome": c.nome,
                        "sottoscrive_contratti": c.sottoscrive_contratti,
                        "slot_contratto_base": c.slot_contratto_base,
                    }
                    for c in Carriera.objects.filter(tipo_carriera__codice="korp").order_by("nome")
                ],
                "modelli": [serializza_modello(m) for m in modelli],
            }
        )

    def post(self, request):
        campagna = campagna_da_request(request)
        if not user_is_staff_campagna(request.user, campagna):
            return Response({"error": "Solo staff."}, status=status.HTTP_403_FORBIDDEN)
        korp = get_object_or_404(Carriera, pk=request.data.get("korp"))
        try:
            if request.data.get("preset"):
                modello = crea_preset(campagna, korp, request.data.get("preset"))
            else:
                modello = ModelloContratto(campagna=campagna, korp=korp, nome=request.data.get("nome") or "Nuovo contratto")
                modello = salva_modello(modello, request.data)
        except ValidationError as exc:
            return _errore(exc)
        return Response(serializza_modello(modello), status=status.HTTP_201_CREATED)


class ContrattiStaffDettaglioView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, modello_id):
        campagna = campagna_da_request(request)
        modello = get_object_or_404(ModelloContratto, pk=modello_id, campagna=campagna)
        if not user_is_staff_campagna(request.user, campagna):
            return Response({"error": "Solo staff."}, status=status.HTTP_403_FORBIDDEN)
        try:
            salva_modello(modello, request.data)
        except ValidationError as exc:
            return _errore(exc)
        return Response(serializza_modello(modello))

    def delete(self, request, modello_id):
        campagna = campagna_da_request(request)
        modello = get_object_or_404(ModelloContratto, pk=modello_id, campagna=campagna)
        if not user_is_staff_campagna(request.user, campagna):
            return Response({"error": "Solo staff."}, status=status.HTTP_403_FORBIDDEN)
        if modello.contratti.filter(stato__in=STATI_OCCUPANO_SLOT).exists():
            modello.attivo = False
            modello.save(update_fields=["attivo", "updated_at"])
            return Response({"disattivato": True})
        modello.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContrattiStaffRuntimeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        campagna = campagna_da_request(request)
        if not user_is_staff_campagna(request.user, campagna):
            return Response({"error": "Solo staff."}, status=status.HTTP_403_FORBIDDEN)
        marca_scaduti()
        qs = Contratto.objects.filter(campagna=campagna).select_related("proponente", "cliente").prefetch_related("adempimenti")[:100]
        return Response([serializza_contratto(c) for c in qs])

    def post(self, request):
        campagna = campagna_da_request(request)
        if not user_is_staff_campagna(request.user, campagna):
            return Response({"error": "Solo staff."}, status=status.HTTP_403_FORBIDDEN)
        azione = request.data.get("azione") or "conferma"
        try:
            if azione == "attiva":
                contratto = get_object_or_404(Contratto, pk=request.data.get("contratto_id"), campagna=campagna)
                attiva_contratto(contratto, contratto.proponente, staff=True)
                contratto.refresh_from_db()
                return Response(serializza_contratto(contratto))
            ademp = get_object_or_404(
                ContrattoAdempimento, pk=request.data.get("adempimento_id"), contratto__campagna=campagna
            )
            if azione == "salda":
                salda_debito(ademp)
            else:
                conferma_adempimento(ademp, attore=None, staff=True)
        except ValidationError as exc:
            return _errore(exc)
        ademp.refresh_from_db()
        return Response(serializza_contratto(ademp.contratto))
