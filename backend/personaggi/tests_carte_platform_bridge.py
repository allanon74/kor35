"""Test predisposizione Card Studio / Card Arena (schema + sync registry)."""
import uuid
from io import BytesIO
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from kor35.sync_tombstone import get_sync_model_registry
from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    EspansioneCarte,
)
from personaggi.carte_platform_models import (
    EXCHANGE_JOB_EXPORT_PLAYABLE,
    CarteArenaRuleset,
    CarteGiocoDefinizione,
    CartePlatformExchangeJob,
    CarteStudioTemplate,
)
from personaggi.carte_platform_specs import build_playable_spec_from_carta
from personaggi.mse_style_import import import_mse_style_package
from personaggi.models import Campagna


class CartePlatformRegistryTests(TestCase):
    def test_registry_includes_platform_models(self):
        registry = get_sync_model_registry(("personaggi",))
        for label in (
            "personaggi.cartegiocodefinizione",
            "personaggi.cartestudiotemplate",
            "personaggi.cartearenaruleset",
            "personaggi.carteplatformgiocatore",
            "personaggi.carteplatformexchangejob",
            "personaggi.cartemsepackageimport",
        ):
            self.assertIn(label, registry)


class CartePlatformModelTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="platform-test", nome="Platform Test")

    def test_bootstrap_gioco_template_ruleset(self):
        gioco = CarteGiocoDefinizione.objects.create(
            campagna=self.campagna,
            slug="sette-elegie",
            nome="Sette Elegie",
            modello_base="kor35",
            studio_abilitato=True,
            arena_abilitata=True,
        )
        template = CarteStudioTemplate.objects.create(
            gioco_definizione=gioco,
            campagna=self.campagna,
            slug="default",
            nome="Default",
            is_default_for_new_cards=True,
            layout_spec={"version": "1", "width_mm": 63, "height_mm": 88},
        )
        ruleset = CarteArenaRuleset.objects.create(
            gioco_definizione=gioco,
            campagna=self.campagna,
            zones_spec={"version": "1", "zones": ["hand", "field"]},
        )
        espansione = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Espansione test",
            slug="esp-test",
            gioco_definizione=gioco,
            default_studio_template=template,
            studio_set_spec={"version": "1"},
        )
        carta = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=espansione,
            codice="PLT-001",
            nome="Carta platform",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            studio_template=template,
            costo_gioco=2,
            attacco=3,
            salute=4,
        )
        spec = build_playable_spec_from_carta(carta)
        self.assertEqual(spec["version"], "1")
        self.assertEqual(spec["gameplay"]["codice"], "PLT-001")
        self.assertEqual(spec["gameplay"]["costo_gioco"], 2)
        self.assertEqual(spec["espansione_slug"], "esp-test")

        carta.arena_playable_spec = spec
        carta.save(update_fields=["arena_playable_spec", "updated_at"])
        carta.refresh_from_db()
        self.assertEqual(carta.arena_playable_spec["gameplay"]["nome"], "Carta platform")
        self.assertEqual(ruleset.gioco_definizione_id, gioco.id)
        self.assertEqual(espansione.default_studio_template_id, template.id)

    def test_import_mse_style_extracts_assets_manifest(self):
        gioco = CarteGiocoDefinizione.objects.create(
            campagna=self.campagna,
            slug="mse-import",
            nome="MSE Import",
        )
        template = CarteStudioTemplate.objects.create(
            gioco_definizione=gioco,
            campagna=self.campagna,
            slug="imported",
            nome="Imported",
        )
        buff = BytesIO()
        with zipfile.ZipFile(buff, "w") as zf:
            zf.writestr(
                "style",
                "short name: Demo Style\nfull name: Demo Full\ngame: mtg\ncard width: 375\ncard height: 523\ncard dpi: 300\n",
            )
            zf.writestr("images/frame.png", b"\x89PNG\r\n\x1a\nfakepng")
            zf.writestr("scripts/helpers.mse-include", "do stuff")
        upload = SimpleUploadedFile("demo.mse-style", buff.getvalue(), content_type="application/zip")
        imported = import_mse_style_package(template=template, upload_file=upload)
        template.save()

        self.assertTrue(imported.extracted_root.startswith("card_studio/mse_styles_extracted/"))
        self.assertGreaterEqual(len(imported.assets_manifest), 3)
        self.assertEqual(imported.parsed_meta.get("game"), "mtg")
        self.assertEqual(template.layout_spec.get("card_width_px"), 375.0)
        self.assertEqual(template.layout_spec.get("card_height_px"), 523.0)
        self.assertEqual(template.layout_spec.get("dpi"), 300.0)
        img_assets = [a for a in template.mse_assets_manifest if a.get("asset_type") == "image"]
        self.assertTrue(img_assets)


class CartePlatformExchangeJobTests(TestCase):
    def test_create_export_playable_job(self):
        campagna = Campagna.objects.create(slug="job-test", nome="Job Test")
        gioco = CarteGiocoDefinizione.objects.create(
            campagna=campagna,
            slug="job-game",
            nome="Job Game",
            modello_base="mtg",
        )
        job = CartePlatformExchangeJob.objects.create(
            campagna=campagna,
            gioco_definizione=gioco,
            tipo=EXCHANGE_JOB_EXPORT_PLAYABLE,
            payload={"scope": "campagna"},
        )
        self.assertEqual(job.stato, "pending")
        self.assertTrue(job.sync_id)

    def test_apply_gioco_definizione_sync_row(self):
        from kor35.edge_sync import EdgeSyncView

        camp = Campagna.objects.create(slug="sync-gioco", nome="Sync Gioco")
        remote_updated = timezone.now()
        row = {
            "sync_id": str(uuid.uuid4()),
            "campagna": str(camp.sync_id),
            "slug": "sync-slug",
            "nome": "Gioco sync",
            "platform_version": "1.0.0",
            "studio_abilitato": True,
            "arena_abilitata": False,
            "mse_game_name": "",
            "meta": {},
            "updated_at": remote_updated.isoformat(),
        }
        view = EdgeSyncView()
        result = view._try_apply_one(CarteGiocoDefinizione, row)
        self.assertEqual(result, "applied")
        gioco = CarteGiocoDefinizione.objects.get(sync_id=row["sync_id"])
        self.assertEqual(gioco.campagna_id, camp.id)
        self.assertTrue(gioco.studio_abilitato)

    def test_create_card_uses_expansion_default_template(self):
        from personaggi.serializers_carte import CartaCollezionabileSerializer

        camp = Campagna.objects.create(slug="tmpl-card", nome="Template Card")
        gioco = CarteGiocoDefinizione.objects.create(
            campagna=camp,
            slug="tmpl-game",
            nome="Template Game",
        )
        tmpl = CarteStudioTemplate.objects.create(
            gioco_definizione=gioco,
            campagna=camp,
            slug="alt",
            nome="Alternativo",
            is_default_for_new_cards=True,
        )
        esp = EspansioneCarte.objects.create(
            campagna=camp,
            nome="ESP",
            slug="esp",
            gioco_definizione=gioco,
            default_studio_template=tmpl,
        )
        serializer = CartaCollezionabileSerializer(
            data={
                "campagna": str(camp.id),
                "espansione": str(esp.id),
                "codice": "TMP-001",
                "nome": "Carta TMP",
                "tipo": CARTA_TIPO_PERSONAGGIO,
                "energia": CARTA_ENERGIA_MARZIALE,
                "rarita": CARTA_RARITA_COMUNE,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        carta = serializer.save(campagna=camp)
        self.assertEqual(carta.studio_template_id, tmpl.id)
