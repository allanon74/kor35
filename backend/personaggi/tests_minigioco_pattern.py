"""Test pattern minigioco: estrazione pesata, legacy, sezione default, sync registry, tool layout."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from gestione_plot.staff_dashboard_layout import (
    KNOWN_STAFF_TOOL_IDS,
    default_staff_dashboard_layout,
    validate_staff_dashboard_layout,
)
from kor35.sync_tombstone import get_sync_model_registry
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    MinigiocoPattern,
    MinigiocoPatternEntry,
    MinigiocoQrConfig,
    MinigiocoSezioneDefault,
)
from personaggi.qr_minigioco import scegli_tipo_e_difficolta


User = get_user_model()


class _Cfg:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MinigiocoPatternExtractionTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.filter(is_default=True).first()
        if not self.campagna:
            self.campagna = Campagna.objects.create(
                slug="test-pattern",
                nome="Test Pattern",
                is_default=True,
            )
        self.pattern = MinigiocoPattern.objects.create(
            nome="Solo simon pesato",
            attivo=True,
            campagna=self.campagna,
        )
        MinigiocoPatternEntry.objects.create(
            pattern=self.pattern,
            tipo=MinigiocoQrConfig.TIPO_SIMON,
            peso=10,
            difficolta=2,
            ordine=0,
            attivo=True,
        )
        MinigiocoPatternEntry.objects.create(
            pattern=self.pattern,
            tipo=MinigiocoQrConfig.TIPO_TAP_ORDER,
            peso=1,
            difficolta=4,
            ordine=1,
            attivo=True,
        )

    @patch("personaggi.qr_minigioco.minigioco_ha_immagine_disponibile", return_value=False)
    def test_pattern_weighted_pick_deterministic(self, _mock):
        cfg = _Cfg(
            pattern=self.pattern,
            pattern_id=self.pattern.pk,
            tipi_abilitati=[MinigiocoQrConfig.TIPO_MEMORY],
            difficolta=1,
            regole_difficolta=[],
        )
        t1, d1 = scegli_tipo_e_difficolta(cfg, 42)
        t2, d2 = scegli_tipo_e_difficolta(cfg, 42)
        self.assertEqual((t1, d1), (t2, d2))
        self.assertIn(t1, (MinigiocoQrConfig.TIPO_SIMON, MinigiocoQrConfig.TIPO_TAP_ORDER))
        self.assertIn(d1, (2, 4))

    @patch("personaggi.qr_minigioco.minigioco_ha_immagine_disponibile", return_value=False)
    def test_legacy_when_no_pattern(self, _mock):
        cfg = _Cfg(
            pattern=None,
            pattern_id=None,
            tipi_abilitati=[MinigiocoQrConfig.TIPO_SIMON],
            difficolta=3,
            regole_difficolta=[],
            tipo="",
        )
        tipo, diff = scegli_tipo_e_difficolta(cfg, 7)
        self.assertEqual(tipo, MinigiocoQrConfig.TIPO_SIMON)
        self.assertEqual(diff, 3)

    @patch("personaggi.qr_minigioco.minigioco_ha_immagine_disponibile", return_value=False)
    def test_pattern_ignores_legacy_tipi(self, _mock):
        """Con pattern attivo non deve uscire MEMORY (legacy) se non è nelle entry."""
        cfg = _Cfg(
            pattern=self.pattern,
            pattern_id=self.pattern.pk,
            tipi_abilitati=[MinigiocoQrConfig.TIPO_MEMORY],
            difficolta=1,
            regole_difficolta=[],
        )
        for seed in range(30):
            tipo, _ = scegli_tipo_e_difficolta(cfg, seed)
            self.assertNotEqual(tipo, MinigiocoQrConfig.TIPO_MEMORY)


class MinigiocoSezioneDefaultApiTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="kor35-sez-def",
            nome="Sez Def",
            attiva=True,
            is_default=True,
        )
        self.user = User.objects.create_user(username="staff_pat", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.user,
            ruolo=CAMPAGNA_ROLE_MASTER,
            attivo=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}

    def test_upsert_sezione_default(self):
        pattern = MinigiocoPattern.objects.create(
            nome="P",
            campagna=self.campagna,
            attivo=True,
        )
        url = "/api/personaggi/api/staff/minigioco-sezione-defaults/"
        res = self.client.post(
            url,
            {
                "page_key": "manifesti",
                "apply_to_new": True,
                "sezione_attiva": True,
                "attivo": True,
                "difficolta": 2,
                "pattern": str(pattern.pk),
                "messaggio_pre": "ciao",
            },
            format="json",
            **self.headers,
        )
        self.assertIn(res.status_code, (200, 201), res.content)
        self.assertEqual(MinigiocoSezioneDefault.objects.filter(page_key="manifesti").count(), 1)
        by_page = self.client.get(
            "/api/personaggi/api/staff/minigioco-sezione-defaults/by-page/manifesti/",
            **self.headers,
        )
        self.assertEqual(by_page.status_code, 200)
        self.assertTrue(by_page.data["apply_to_new"])
        self.assertEqual(by_page.data["config"]["messaggio_pre"], "ciao")
        self.assertEqual(by_page.data["config"]["pattern_id"], str(pattern.pk))

        res2 = self.client.post(
            url,
            {
                "page_key": "manifesti",
                "apply_to_new": False,
                "messaggio_pre": "aggiornato",
                "pattern": str(pattern.pk),
            },
            format="json",
            **self.headers,
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(MinigiocoSezioneDefault.objects.filter(page_key="manifesti").count(), 1)
        row = MinigiocoSezioneDefault.objects.get(page_key="manifesti")
        self.assertFalse(row.apply_to_new)
        self.assertEqual(row.messaggio_pre, "aggiornato")


class MinigiocoPatternSyncAndLayoutTests(TestCase):
    def test_sync_registry_includes_pattern_models(self):
        registry = get_sync_model_registry()
        self.assertIn("personaggi.minigiocopattern", registry)
        self.assertIn("personaggi.minigiocopatternentry", registry)
        self.assertIn("personaggi.minigiocosezionedefault", registry)

    def test_staff_tool_minigioco_pattern(self):
        self.assertIn("minigioco-pattern", KNOWN_STAFF_TOOL_IDS)
        layout = default_staff_dashboard_layout()
        evento_tools = layout["groups"][0]["tool_ids"]
        self.assertIn("minigioco-pattern", evento_tools)
        validate_staff_dashboard_layout(layout)
