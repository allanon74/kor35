"""
API staff Card Studio / Card Arena (predisposizione piattaforma).
"""
import zipfile

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from gestione_plot.permissions import IsStaffOrMaster
from personaggi.carte_platform_models import (
    EXCHANGE_JOB_EXPORT_PLAYABLE,
    EXCHANGE_JOB_PENDING,
    CarteArenaRuleset,
    CarteGiocoDefinizione,
    CarteMsePackageImport,
    CartePlatformExchangeJob,
    CartePlatformGiocatore,
    CarteStudioTemplate,
    MODELLO_BASE_KOR35,
)
from personaggi.mse_kor35_game_spec import merge_kor35_game_meta
from personaggi.carte_platform_specs import build_playable_spec_from_carta
from personaggi.mse_style_import import import_mse_style_package
from personaggi.carte_collezionabili_models import CartaCollezionabile
from personaggi.models import FEATURE_CARTE_COLLEZIONABILI
from personaggi.serializers_carte_platform import (
    CarteArenaRulesetSerializer,
    CarteGiocoDefinizioneSerializer,
    CarteMsePackageImportSerializer,
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
    qs = CarteGiocoDefinizione.objects.filter(campagna=campagna).order_by("nome")
    if qs.count() == 1:
        return qs.first()
    return None


class CarteGiocoDefinizioneStaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrMaster]
    serializer_class = CarteGiocoDefinizioneSerializer

    def get_queryset(self):
        qs = CarteGiocoDefinizione.objects.all().select_related("campagna")
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)

    def perform_create(self, serializer):
        campagna = _require_campagna(self.request)
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
                is_default_for_new_cards=True,
                layout_spec={"version": "1", "width_mm": 63, "height_mm": 88, "dpi": 300},
                campi_schema={"version": "1", "mapping": {}},
            )
            created.append("studio_template")
        if gioco.modello_base == MODELLO_BASE_KOR35:
            merged_meta = merge_kor35_game_meta(gioco.meta)
            if merged_meta != (gioco.meta or {}):
                gioco.meta = merged_meta
                gioco.save(update_fields=["meta", "updated_at"])
                created.append("kor35_mse_game_spec")
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
                {
                    "gioco_definizione": (
                        "Specifica gioco_definizione: la campagna non ha un unico gioco predefinito."
                    )
                }
            )
        serializer.save(campagna=campagna, gioco_definizione=gioco)

    @action(
        detail=False,
        methods=["post"],
        url_path="import-mse-style",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_mse_style(self, request):
        """
        Import package `.mse-style/.zip`, estrai asset grafici/non grafici
        e crea/aggiorna un template studio.
        """
        campagna = _require_campagna(request)
        up = request.FILES.get("file")
        if not up:
            raise DRFValidationError({"file": "File .mse-style/.zip obbligatorio."})
        if not (up.name.endswith(".zip") or up.name.endswith(".mse-style")):
            raise DRFValidationError({"file": "Estensione non valida: usare .zip o .mse-style."})

        gioco_id = request.data.get("gioco_definizione")
        if gioco_id:
            gioco = CarteGiocoDefinizione.objects.filter(id=gioco_id, campagna=campagna).first()
            if not gioco:
                raise DRFValidationError({"gioco_definizione": "Gioco non trovato nella campagna attiva."})
        else:
            gioco = _get_gioco_for_campagna(campagna)
            if not gioco:
                raise DRFValidationError(
                    {
                        "gioco_definizione": (
                            "Specifica gioco_definizione: la campagna non ha un unico gioco predefinito."
                        )
                    }
                )

        slug = (request.data.get("slug") or "").strip().lower().replace(" ", "-")
        nome = (request.data.get("nome") or "").strip()
        if not slug:
            base = up.name.rsplit(".", 1)[0].lower().replace(" ", "-")
            slug = f"mse-{base}"[:80]
        if not nome:
            nome = up.name.rsplit(".", 1)[0][:120]
        base_slug = slug
        idx = 2
        while CarteStudioTemplate.objects.filter(
            campagna=campagna, gioco_definizione=gioco, slug=slug
        ).exists():
            suffix = f"-{idx}"
            slug = f"{base_slug[: max(1, 80 - len(suffix))]}{suffix}"
            idx += 1
        is_default = str(request.data.get("is_default_for_new_cards", "")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        template = CarteStudioTemplate(
            campagna=campagna,
            gioco_definizione=gioco,
            slug=slug,
            nome=nome,
            is_default_for_new_cards=is_default,
            attivo=True,
        )

        try:
            imported = import_mse_style_package(template=template, upload_file=up)
        except zipfile.BadZipFile as exc:
            raise DRFValidationError({"file": "Archivio non valido o corrotto."}) from exc

        if imported.parsed_meta.get("full_name") and not request.data.get("nome"):
            template.nome = imported.parsed_meta["full_name"][:120]

        if imported.parsed_meta.get("game"):
            campi_schema = dict(template.campi_schema or {})
            campi_schema.setdefault("version", "1")
            campi_schema.setdefault("mse_game", imported.parsed_meta["game"])
            template.campi_schema = campi_schema

        template.save()
        if template.is_default_for_new_cards:
            (
                CarteStudioTemplate.objects.filter(gioco_definizione=gioco)
                .exclude(pk=template.pk)
                .update(is_default_for_new_cards=False)
            )

        return Response(
            {
                "template": CarteStudioTemplateSerializer(template, context={"request": request}).data,
                "import_summary": {
                    "assets_total": len(imported.assets_manifest),
                    "images_total": len(
                        [a for a in imported.assets_manifest if a.get("asset_type") == "image"]
                    ),
                    "text_total": len(
                        [a for a in imported.assets_manifest if a.get("asset_type") == "text"]
                    ),
                    "binary_total": len(
                        [a for a in imported.assets_manifest if a.get("asset_type") == "binary"]
                    ),
                    "extracted_root": imported.extracted_root,
                    "parsed_meta": imported.parsed_meta,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CarteMsePackageImportStaffViewSet(viewsets.ReadOnlyModelViewSet):
    """Registry package MSE importati (per package choice nel Card Studio)."""

    permission_classes = [IsStaffOrMaster]
    serializer_class = CarteMsePackageImportSerializer

    def get_queryset(self):
        qs = CarteMsePackageImport.objects.filter(imported=True).select_related(
            "campagna", "gioco_definizione"
        )
        return _campaign_feature_filter(self.request, qs, FEATURE_CARTE_COLLEZIONABILI)


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
                {
                    "gioco_definizione": (
                        "Specifica gioco_definizione: la campagna non ha un unico gioco predefinito."
                    )
                }
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
                {
                    "gioco_definizione": (
                        "Specifica gioco_definizione: la campagna non ha un unico gioco predefinito."
                    )
                }
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
                {
                    "gioco_definizione": (
                        "Specifica gioco_definizione: la campagna non ha un unico gioco predefinito."
                    )
                }
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
