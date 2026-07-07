"""Test predisposizione Card Studio / Card Arena (schema + sync registry)."""
import uuid

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
            studio_abilitato=True,
            arena_abilitata=True,
        )
        template = CarteStudioTemplate.objects.create(
            gioco_definizione=gioco,
            campagna=self.campagna,
            slug="default",
            nome="Default",
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


class CartePlatformExchangeJobTests(TestCase):
    def test_create_export_playable_job(self):
        campagna = Campagna.objects.create(slug="job-test", nome="Job Test")
        gioco = CarteGiocoDefinizione.objects.create(
            campagna=campagna,
            slug="job-game",
            nome="Job Game",
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
