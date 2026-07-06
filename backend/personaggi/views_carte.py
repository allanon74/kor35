"""
API giocatore e staff per carte collezionabili.
"""
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.permissions import IsStaffOrMaster
from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    CartaCollezionabile,
    CartaPosseduta,
    ComboReliquiario,
    ConfigurazioneCarteCollezionabili,
    EspansioneCarte,
    KeywordCarta,
    OffertaScambioCarte,
)
from personaggi.carte_collezionabili_service import (
    apri_bustina,
    build_collezione_payload,
    equip_reliquio,
    get_config_carte,
    lista_bustine,
    lista_espansioni_giocatore,
    personaggio_puo_accedere_carte,
    elimina_mazzo_duello,
    salva_mazzo_duello,
    stato_carte_per_personaggio,
)
from personaggi.carte_duello_service import (
    accetta_duello,
    accetta_duello_per_codice,
    annulla_duello,
    crea_invito_duello,
    esegui_azione_duello,
    get_duello_per_giocatore,
    lista_avversari_duello,
    lista_duelli_personaggio,
)
from personaggi.carte_mercato_service import (
    accetta_offerta_scambio,
    annulla_offerta_scambio,
    build_mercato_payload,
    crea_offerta_scambio,
    lista_scambi_staff,
)
from personaggi.carte_lobby_service import (
    apri_scontro_lobby,
    azione_prematch,
    unisciti_scontro_lobby,
)
from personaggi.models import FEATURE_CARTE_COLLEZIONABILI, Personaggio
from personaggi.serializers_carte import (
    BustinaCarteSerializer,
    CartaCollezionabileSerializer,
    ComboReliquiarioSerializer,
    ConfigurazioneCarteCollezionabiliSerializer,
    EspansioneCarteSerializer,
    KeywordCartaSerializer,
)
from personaggi.views import _can_operate_in_campaign
from personaggi.views_staff import _campaign_feature_filter, _get_active_campaign, _get_default_campaign


def _get_pg(request, char_id):
    pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
    if not _can_operate_in_campaign(request.user, pg.campagna, needs_master=False):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("Non autorizzato per la campagna del personaggio.")
    return pg


class CarteStatoGiocatoreView(APIView):
    """Flag leggero per UI (tab Carte, reliquiario, duelli)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        return Response(stato_carte_per_personaggio(pg))


class CarteCollezionabiliGiocatoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        payload = build_collezione_payload(pg)
        if not payload.get("puo_accedere"):
            return Response(payload)
        cfg = get_config_carte(pg.campagna, create=False)
        payload["bustine"] = lista_bustine(pg.campagna)
        payload["espansioni"] = lista_espansioni_giocatore(pg.campagna)
        payload["config"] = {
            "max_bustine_giorno": cfg.max_bustine_giorno if cfg else 10,
            "pity_soglia": cfg.pity_soglia if cfg else 20,
        }
        payload["wiki_regolamento_slug"] = "carte-collezionabili-regolamento"
        return Response(payload)


class CarteApriBustinaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        bustina_id = request.data.get("bustina_id")
        if not char_id or not bustina_id:
            return Response({"error": "char_id e bustina_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(apri_bustina(pg, bustina_id))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except BustinaCarte.DoesNotExist:
            return Response({"error": "Bustina non trovata."}, status=404)


class CarteReliquiarioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        slot_index = request.data.get("slot_index")
        carta_posseduta_id = request.data.get("carta_posseduta_id")
        if char_id is None or slot_index is None:
            return Response({"error": "char_id e slot_index richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            slot_index = int(slot_index)
            payload = equip_reliquio(pg, slot_index, carta_posseduta_id or None)
            return Response(payload)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except (ValueError, TypeError):
            return Response({"error": "slot_index non valido."}, status=400)


class CarteMercatoView(APIView):
    """Mercato scambio carte tra personaggi della stessa campagna."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        return Response(build_mercato_payload(pg))

    def post(self, request):
        char_id = request.data.get("char_id")
        carta_offerta_id = request.data.get("carta_offerta_id")
        if not char_id or not carta_offerta_id:
            return Response({"error": "char_id e carta_offerta_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(
                crea_offerta_scambio(
                    pg,
                    carta_offerta_id=carta_offerta_id,
                    richiesta_carta_id=request.data.get("richiesta_carta_id"),
                    richiesta_crediti=request.data.get("richiesta_crediti"),
                    messaggio=request.data.get("messaggio") or "",
                )
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except CartaPosseduta.DoesNotExist:
            return Response({"error": "Carta offerta non trovata."}, status=404)
        except CartaCollezionabile.DoesNotExist:
            return Response({"error": "Carta richiesta non trovata."}, status=404)


class CarteMercatoAccettaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        offerta_id = request.data.get("offerta_id")
        if not char_id or not offerta_id:
            return Response({"error": "char_id e offerta_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(
                accetta_offerta_scambio(
                    pg,
                    offerta_id,
                    carta_contropartita_id=request.data.get("carta_contropartita_id"),
                )
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except OffertaScambioCarte.DoesNotExist:
            return Response({"error": "Offerta non trovata."}, status=404)


class CarteMercatoAnnullaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        offerta_id = request.data.get("offerta_id")
        if not char_id or not offerta_id:
            return Response({"error": "char_id e offerta_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(annulla_offerta_scambio(pg, offerta_id))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except OffertaScambioCarte.DoesNotExist:
            return Response({"error": "Offerta non trovata."}, status=404)


class StaffCarteScambiView(APIView):
    """Riepilogo scambi carte per campagna attiva (staff)."""

    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        campagna = _get_active_campaign(request) or _get_default_campaign()
        if not campagna:
            return Response({"error": "Campagna attiva non trovata."}, status=400)
        stato = (request.query_params.get("stato") or "").strip() or None
        try:
            limit = int(request.query_params.get("limit") or 100)
        except (TypeError, ValueError):
            limit = 100
        return Response(lista_scambi_staff(campagna, stato=stato, limit=limit))


class CarteMazzoDuelloView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        payload = build_collezione_payload(pg)
        return Response({"mazzi": payload.get("mazzi") or [], "puo_accedere": payload.get("puo_accedere", False)})

    def post(self, request):
        char_id = request.data.get("char_id")
        carte_ids = request.data.get("carte_ids") or request.data.get("mazzo_ids") or []
        nome = request.data.get("nome") or "Mazzo principale"
        mazzo_id = request.data.get("mazzo_id")
        is_default = bool(request.data.get("is_default", False))
        leader_carta_posseduta_id = (
            request.data.get("leader_id") or request.data.get("leader_carta_posseduta_id")
        )
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(
                salva_mazzo_duello(
                    pg,
                    carte_ids,
                    mazzo_id=mazzo_id,
                    nome=nome,
                    is_default=is_default,
                    leader_carta_posseduta_id=leader_carta_posseduta_id,
                )
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)

    def delete(self, request):
        char_id = request.data.get("char_id")
        mazzo_id = request.data.get("mazzo_id")
        if not char_id or not mazzo_id:
            return Response({"error": "char_id e mazzo_id richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(elimina_mazzo_duello(pg, mazzo_id))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteDuelloListaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        stato = stato_carte_per_personaggio(pg)
        if not stato.get("puo_accedere"):
            return Response({**stato, "duelli": []})
        return Response({**stato, "duelli": lista_duelli_personaggio(pg)})


class CarteDuelloDettaglioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, duello_id):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(get_duello_per_giocatore(duello_id, pg))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteDuelloInvitaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        mazzo_ids = request.data.get("mazzo_ids") or []
        leader_id = request.data.get("leader_id")
        sfidato_id = request.data.get("sfidato_id")
        qrcode_id = request.data.get("qrcode_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(
                crea_invito_duello(
                    pg,
                    mazzo_ids,
                    leader_id=leader_id,
                    sfidato_id=sfidato_id,
                    qrcode_id=qrcode_id,
                )
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteDuelloAvversariView(APIView):
    """Lista avversari per sfida a distanza (solo modalità TEST)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response({"avversari": lista_avversari_duello(pg)})
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteDuelloAccettaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, duello_id=None):
        char_id = request.data.get("char_id")
        mazzo_ids = request.data.get("mazzo_ids") or []
        leader_id = request.data.get("leader_id")
        codice = request.data.get("codice_invito")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            if codice and not duello_id:
                return Response(
                    accetta_duello_per_codice(pg, codice, mazzo_ids, leader_id=leader_id)
                )
            if not duello_id:
                return Response({"error": "duello_id o codice_invito richiesto."}, status=400)
            return Response(accetta_duello(duello_id, pg, mazzo_ids, leader_id=leader_id))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteDuelloAzioneView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, duello_id):
        char_id = request.data.get("char_id")
        azione = request.data.get("azione")
        payload = request.data.get("payload") or {}
        if not char_id or not azione:
            return Response({"error": "char_id e azione richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(esegui_azione_duello(duello_id, pg, azione, payload))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteDuelloAnnullaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, duello_id):
        char_id = request.data.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(annulla_duello(duello_id, pg))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteScontroApriView(APIView):
    """OPEN: crea lobby con QR sessione."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(apri_scontro_lobby(pg))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteScontroUniscitiView(APIView):
    """OPEN: unisciti via QR o duello_id."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        char_id = request.data.get("char_id")
        qrcode_id = request.data.get("qrcode_id")
        duello_id = request.data.get("duello_id")
        if not char_id:
            return Response({"error": "char_id richiesto."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(
                unisciti_scontro_lobby(pg, qrcode_id=qrcode_id, duello_id=duello_id)
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class CarteScontroPrematchView(APIView):
    """Negoziazione mazzo, posta, modalità prima della partita."""

    permission_classes = [IsAuthenticated]

    def post(self, request, duello_id):
        char_id = request.data.get("char_id")
        azione = request.data.get("azione")
        payload = request.data.get("payload") or {}
        if not char_id or not azione:
            return Response({"error": "char_id e azione richiesti."}, status=400)
        pg = _get_pg(request, char_id)
        try:
            return Response(azione_prematch(duello_id, pg, azione, payload))
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)


class EspansioneCarteStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = EspansioneCarteSerializer

    def get_queryset(self):
        from django.db.models import Count

        qs = (
            EspansioneCarte.objects.all()
            .select_related("campagna")
            .annotate(bustine_count=Count("bustine"), carte_count=Count("carte"))
            .order_by("ordine", "nome")
        )
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _get_active_campaign(self.request) or _get_default_campaign()
        if not campagna:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
        serializer.save(campagna=campagna)


class CartaCollezionabileStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CartaCollezionabileSerializer

    def get_queryset(self):
        qs = (
            CartaCollezionabile.objects.all()
            .select_related("campagna", "espansione")
            .prefetch_related(
                "reliquiario_statistiche__statistica",
                "reliquiario_statistiche__limit_a_aure",
                "reliquiario_statistiche__limit_a_elementi",
            )
        )
        qs = _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)
        espansione_id = self.request.query_params.get("espansione_id")
        if espansione_id:
            qs = qs.filter(espansione_id=espansione_id)
        return qs

    def perform_create(self, serializer):
        campagna = _get_active_campaign(self.request) or _get_default_campaign()
        if not campagna:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
        serializer.save(campagna=campagna)


class BustinaCarteStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = BustinaCarteSerializer

    def get_queryset(self):
        qs = BustinaCarte.objects.all().select_related("campagna", "qr_code", "espansione")
        qs = _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)
        espansione_id = self.request.query_params.get("espansione_id")
        if espansione_id:
            qs = qs.filter(espansione_id=espansione_id)
        return qs

    def perform_create(self, serializer):
        campagna = _get_active_campaign(self.request) or _get_default_campaign()
        if not campagna:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
        serializer.save(campagna=campagna)


class ConfigurazioneCarteStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = ConfigurazioneCarteCollezionabiliSerializer

    def get_queryset(self):
        qs = ConfigurazioneCarteCollezionabili.objects.all().select_related("campagna")
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _get_active_campaign(self.request) or _get_default_campaign()
        if not campagna:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
        serializer.save(campagna=campagna)

    @action(detail=False, methods=["get"], url_path="corrente")
    def corrente(self, request):
        campagna = _get_active_campaign(request) or _get_default_campaign()
        if not campagna:
            return Response({"error": "Campagna non trovata."}, status=404)
        cfg = get_config_carte(campagna, create=True)
        return Response(ConfigurazioneCarteCollezionabiliSerializer(cfg, context={"request": request}).data)


class KeywordCartaStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = KeywordCartaSerializer

    def get_queryset(self):
        qs = KeywordCarta.objects.all().select_related("campagna").order_by("-priorita", "nome")
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _get_active_campaign(self.request) or _get_default_campaign()
        if not campagna:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
        serializer.save(campagna=campagna)


class ComboReliquiarioStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = ComboReliquiarioSerializer

    def get_queryset(self):
        qs = (
            ComboReliquiario.objects.all()
            .select_related("campagna")
            .prefetch_related(
                "statistiche__statistica",
                "statistiche__limit_a_aure",
                "statistiche__limit_a_elementi",
            )
            .order_by("ordine", "nome")
        )
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _get_active_campaign(self.request) or _get_default_campaign()
        if not campagna:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
        serializer.save(campagna=campagna)


class StaffCarteEffectSchemaView(APIView):
    """JSON Schema EffectScript v1 + template Mutazione per compositore staff."""

    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        from personaggi.carte_effect_script import (
            EFFECT_SCRIPT_VERSION,
            colpo_influenza_effect_script_template,
            danno_eroe_effect_script_template,
            get_effect_script_schema,
            guscio_effect_script_template,
            guarigione_completa_effect_script_template,
            guarigione_effect_script_template,
            mutazione_effect_script_template,
            pesca_effect_script_template,
            rigenerazione_energia_effect_script_template,
            sinergia_energia_effect_script_template,
            sinergia_pesca_effect_script_template,
        )

        return Response({
            "version": EFFECT_SCRIPT_VERSION,
            "schema": get_effect_script_schema(),
            "templates": {
                "mutazione": mutazione_effect_script_template(),
                "colpo_influenza": colpo_influenza_effect_script_template(),
                "pesca": pesca_effect_script_template(),
                "rigenerazione_energia": rigenerazione_energia_effect_script_template(),
                "danno_eroe": danno_eroe_effect_script_template(),
                "guscio": guscio_effect_script_template(),
                "guarigione": guarigione_effect_script_template(),
                "guarigione_completa": guarigione_completa_effect_script_template(),
                "sinergia_pesca": sinergia_pesca_effect_script_template(),
                "sinergia_energia": sinergia_energia_effect_script_template(),
            },
        })

    def post(self, request):
        """Valida uno script rispetto a schema + placeholder keyword."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        from personaggi.carte_effect_script import validate_effect_script_for_keyword

        script = request.data.get("script")
        nome = (request.data.get("nome") or "").strip()
        codice = (request.data.get("codice") or "").strip()
        if script is None or script == "":
            return Response({"valid": True, "script": {}, "detail": "Script vuoto."})
        try:
            validated = validate_effect_script_for_keyword(script, nome=nome, codice=codice)
            return Response({"valid": True, "script": validated, "detail": "Script valido."})
        except DjangoValidationError as exc:
            errors = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return Response(
                {"valid": False, "errors": errors, "detail": " ".join(errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StaffWikiCarteRegolamentoView(APIView):
    """
    Sincronizza bozza regolamento carte da docs/wiki/carte/.
    GET: metadati manifest; POST: esegue sync (default force=true).
    """

    permission_classes = [IsStaffOrMaster]

    def get(self, request):
        from gestione_plot.wiki_carte_regolamento import get_wiki_carte_regolamento_info

        return Response(get_wiki_carte_regolamento_info())

    def post(self, request):
        from gestione_plot.wiki_carte_regolamento import sync_wiki_carte_regolamento

        force_raw = request.data.get("force", True)
        if isinstance(force_raw, str):
            force = force_raw.strip().lower() in ("1", "true", "yes", "on")
        else:
            force = bool(force_raw)

        try:
            results = sync_wiki_carte_regolamento(force=force)
        except FileNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        created = sum(1 for r in results if r["action"] == "created")
        updated = sum(1 for r in results if r["action"] == "updated")
        skipped = sum(1 for r in results if r["action"] == "skipped")
        return Response(
            {
                "ok": True,
                "force": force,
                "summary": {"created": created, "updated": updated, "skipped": skipped},
                "results": results,
            }
        )
