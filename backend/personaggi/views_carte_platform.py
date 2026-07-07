"""
API staff Card Studio / Card Arena (predisposizione piattaforma).
"""
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from gestione_plot.permissions import IsStaffOrMaster
from personaggi.carte_platform_models import (
    EXCHANGE_JOB_EXPORT_PLAYABLE,
    EXCHANGE_JOB_PENDING,
    CarteArenaRuleset,
    CarteGiocoDefinizione,
    CartePlatformExchangeJob,
    CartePlatformGiocatore,
    CarteStudioTemplate,
)
from personaggi.carte_platform_specs import build_playable_spec_from_carta
from personaggi.carte_collezionabili_models import CartaCollezionabile
from personaggi.models import FEATURE_CARTE_COLLEZIONABILI
from personaggi.serializers_carte_platform import (
    CarteArenaRulesetSerializer,
    CarteGiocoDefinizioneSerializer,
    CartePlatformExchangeJobSerializer,
    CartePlatformGiocatoreSerializer,
    CarteStudioTemplateSerializer,
)
from personaggi.views_staff import _campaign_feature_filter, _get_active_campaign, _get_default_campaign


def _require_campagna(request):
    campagna = _get_active_campaign(request) or _get_default_campaign()
    if not campagna:
        raise DRFValidationError({"campagna": "Campagna attiva non trovata."})
    return campagna


def _get_gioco_for_campagna(campagna):
    return CarteGiocoDefinizione.objects.filter(campagna=campagna).first()


class CarteGiocoDefinizioneStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CarteGiocoDefinizioneSerializer

    def get_queryset(self):
        qs = CarteGiocoDefinizione.objects.all().select_related("campagna")
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _require_campagna(self.request)
        if CarteGiocoDefinizione.objects.filter(campagna=campagna).exists():
            raise DRFValidationError(
                {"campagna": "Esiste già una definizione gioco per questa campagna."}
            )
        serializer.save(campagna=campagna)

    @action(detail=True, methods=["post"], url_path="bootstrap")
    def bootstrap(self, request, pk=None):
        """Crea ruleset Arena e template Studio di default se mancanti."""
        gioco = self.get_object()
        campagna = gioco.campagna
        created = []
        if not hasattr(gioco, "arena_ruleset"):
            CarteArenaRuleset.objects.create(
                gioco_definizione=gioco,
                campagna=campagna,
                zones_spec={
                    "version": "1",
                    "zones": ["deck", "hand", "field", "reliquary", "graveyard", "exile"],
                },
                win_conditions={"version": "1", "type": "leader_hp_zero"},
                formato_mazzo={"version": "1", "max_cards": 15, "max_duplicates": 2, "leader_required": True},
            )
            created.append("arena_ruleset")
        if not gioco.studio_templates.filter(slug="default").exists():
            CarteStudioTemplate.objects.create(
                gioco_definizione=gioco,
                campagna=campagna,
                slug="default",
                nome="Template standard",
                layout_spec={"version": "1", "width_mm": 63, "height_mm": 88, "dpi": 300},
                campi_schema={"version": "1", "mapping": {}},
            )
            created.append("studio_template")
        return Response({"created": created, "gioco_id": str(gioco.id)})


class CarteStudioTemplateStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CarteStudioTemplateSerializer

    def get_queryset(self):
        qs = CarteStudioTemplate.objects.all().select_related("campagna", "gioco_definizione")
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _require_campagna(self.request)
        gioco = serializer.validated_data.get("gioco_definizione") or _get_gioco_for_campagna(campagna)
        if not gioco:
            raise DRFValidationError(
                {"gioco_definizione": "Crea prima una definizione gioco per la campagna."}
            )
        serializer.save(campagna=campagna, gioco_definizione=gioco)


class CarteArenaRulesetStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CarteArenaRulesetSerializer

    def get_queryset(self):
        qs = CarteArenaRuleset.objects.all().select_related("campagna", "gioco_definizione")
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _require_campagna(self.request)
        gioco = serializer.validated_data.get("gioco_definizione") or _get_gioco_for_campagna(campagna)
        if not gioco:
            raise DRFValidationError(
                {"gioco_definizione": "Crea prima una definizione gioco per la campagna."}
            )
        if hasattr(gioco, "arena_ruleset"):
            raise DRFValidationError(
                {"gioco_definizione": "Ruleset Arena già presente per questa definizione."}
            )
        serializer.save(campagna=campagna, gioco_definizione=gioco)


class CartePlatformGiocatoreStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CartePlatformGiocatoreSerializer

    def get_queryset(self):
        qs = CartePlatformGiocatore.objects.all().select_related(
            "campagna", "gioco_definizione", "personaggio", "user"
        )
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _require_campagna(self.request)
        gioco = serializer.validated_data.get("gioco_definizione") or _get_gioco_for_campagna(campagna)
        if not gioco:
            raise DRFValidationError(
                {"gioco_definizione": "Crea prima una definizione gioco per la campagna."}
            )
        serializer.save(campagna=campagna, gioco_definizione=gioco)


class CartePlatformExchangeJobStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CartePlatformExchangeJobSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = CartePlatformExchangeJob.objects.all().select_related(
            "campagna", "gioco_definizione", "richiesto_da"
        )
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _require_campagna(self.request)
        gioco = serializer.validated_data.get("gioco_definizione") or _get_gioco_for_campagna(campagna)
        if not gioco:
            raise DRFValidationError(
                {"gioco_definizione": "Crea prima una definizione gioco per la campagna."}
            )
        serializer.save(
            campagna=campagna,
            gioco_definizione=gioco,
            richiesto_da=self.request.user,
            stato=EXCHANGE_JOB_PENDING,
        )

    @action(detail=True, methods=["post"], url_path="esegui-export-playable")
    def esegui_export_playable(self, request, pk=None):
        """Job sincrono MVP: rigenera arena_playable_spec su tutte le carte campagna."""
        job = self.get_object()
        if job.tipo != EXCHANGE_JOB_EXPORT_PLAYABLE:
            return Response({"error": "Job non di tipo export_playable."}, status=400)
        job.stato = "running"
        job.save(update_fields=["stato", "updated_at"])
        carte = CartaCollezionabile.objects.filter(campagna=job.campagna, attiva=True)
        count = 0
        try:
            for carta in carte.iterator():
                spec = build_playable_spec_from_carta(carta)
                carta.arena_playable_spec = spec
                carta.save(update_fields=["arena_playable_spec", "updated_at"])
                count += 1
            job.stato = "done"
            job.risultato = {"carte_aggiornate": count}
            job.completato_at = timezone.now()
            job.save(update_fields=["stato", "risultato", "completato_at", "updated_at"])
            return Response(CartePlatformExchangeJobSerializer(job).data)
        except Exception as exc:
            job.stato = "failed"
            job.errore = str(exc)
            job.completato_at = timezone.now()
            job.save(update_fields=["stato", "errore", "completato_at", "updated_at"])
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
