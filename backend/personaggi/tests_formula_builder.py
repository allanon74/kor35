from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .formula_builder import (
    build_formula_template,
    build_stats_by_selection,
    render_formula_preview,
)
from .models import (
    Abilita,
    AbilitaFormulaRule,
    AbilitaStatistica,
    Mattone,
    Punteggio,
    Statistica,
    AURA,
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    formatta_testo_generico,
    infer_weapon_damage_mode,
)


class FormulaBuilderLogicTests(TestCase):
    def test_build_stats_by_selection_resets_controlled_params(self):
        current = {"prefisso_puro": 1, "dardo": 1, "custom_param": 5}
        selections = {
            "formula_prefix": ["prefisso_diretto"],
            "formula_target": "tocco",
        }

        merged = build_stats_by_selection(current, selections)

        self.assertEqual(merged["prefisso_puro"], 0)
        self.assertEqual(merged["prefisso_diretto"], 1)
        self.assertEqual(merged["dardo"], 0)
        self.assertEqual(merged["tocco"], 1)
        self.assertEqual(merged["custom_param"], 5)

    def test_damage_mode_preserves_numeric_components(self):
        current = {"dannigen": 2, "dannimis": 3, "dannidis": 5}
        selections = {"formula_damage": "mischia"}

        merged = build_stats_by_selection(current, selections)

        self.assertEqual(merged["dmg_mischia"], 1)
        self.assertEqual(merged["dmg_distanza"], 0)
        self.assertEqual(merged["dannigen"], 2)
        self.assertEqual(merged["dannimis"], 3)
        self.assertEqual(merged["dannidis"], 0)

    def test_mischia_damage_preview_sums_dannigen_and_dannimis(self):
        stats = build_stats_by_selection(
            {"dannigen": 2, "dannimis": 1},
            {"formula_damage": "mischia"},
        )
        formula = build_formula_template("attack", {"formula_damage": "mischia"})
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertIn("tre!", rendered.lower())

    def test_distanza_damage_preview_sums_dannigen_and_dannidis(self):
        stats = build_stats_by_selection(
            {"dannigen": 2, "dannidis": 1},
            {"formula_damage": "distanza"},
        )
        formula = build_formula_template("attack", {"formula_damage": "distanza"})
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertIn("tre!", rendered.lower())

    def test_damage_total_one_is_omitted(self):
        stats = build_stats_by_selection(
            {"dannigen": 1, "dannimis": 0},
            {"formula_damage": "mischia"},
        )
        formula = build_formula_template("attack", {"formula_damage": "mischia"})
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertNotIn("uno", rendered.lower())
        self.assertNotIn("due!", rendered.lower())

    def test_infer_weapon_damage_mode_from_base_stats(self):
        self.assertEqual(infer_weapon_damage_mode({"dannidis": 1}), "distanza")
        self.assertEqual(infer_weapon_damage_mode({"dannimis": 1}), "mischia")

    def test_ranged_weapon_keeps_damage_with_global_dannimis_bonus(self):
        st_mis = Statistica.objects.filter(parametro="dannimis").first()
        if not st_mis:
            self.skipTest("Statistica dannimis non presente nel DB di test")
        abilita, _ = Abilita.objects.get_or_create(
            nome="Test bonus mischia globale",
            defaults={"costo_pc": 0, "costo_crediti": 0},
        )
        AbilitaStatistica.objects.update_or_create(
            abilita=abilita,
            statistica=st_mis,
            defaults={"valore": 1, "tipo_modificatore": MODIFICATORE_ADDITIVO},
        )

        class FakeStat:
            def __init__(self, parametro):
                self.parametro = parametro

        class FakeItem:
            def __init__(self, parametro, valore_base):
                self.statistica = FakeStat(parametro)
                self.valore_base = valore_base

        stats = [FakeItem("dannidis", 2)]
        formula = "{rango|:RANGO}{molt|:MOLT}Pierce! {formula_damage}"

        user_model = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model()
        user = user_model.objects.create_user(username="formula_weapon_dmg", password="x")
        from .models import Personaggio, PersonaggioAbilita

        pg = Personaggio.objects.create(nome="PG formula weapon", proprietario=user)
        PersonaggioAbilita.objects.create(personaggio=pg, abilita=abilita)
        if hasattr(pg, "_modificatori_calcolati_cache"):
            del pg._modificatori_calcolati_cache

        rendered = formatta_testo_generico(
            "",
            formula=formula,
            statistiche_base=stats,
            personaggio=pg,
            context={"item_modifiers": [], "attack_formula_template": formula},
            solo_formula=True,
        ).lower()
        self.assertIn("pierce!", rendered)
        self.assertIn("due!", rendered)


class FormulaBuilderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="staff_formula_builder",
            password="test-pass-123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_schema_endpoint_returns_sections(self):
        res = self.client.get("/api/personaggi/api/staff/formula-builder/schema/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("sections", res.data)
        self.assertTrue(any(section.get("id") == "formula_status" for section in res.data["sections"]))

    def test_preview_endpoint_renders_status_with_duration(self):
        payload = {
            "formula": "{formula_status}",
            "stats_by_param": {"durata": 15},
            "selections": {"formula_status": "paralisi"},
            "custom_text": "testo libero",
        }
        res = self.client.post("/api/personaggi/api/staff/formula-builder/preview/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        rendered = res.data.get("formula_rendered", "")
        self.assertIn("Paralisi 15 secondi!", rendered)
        self.assertTrue(rendered.endswith("testo libero"))


class AbilitaFormulaRulesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="staff_formula_rules",
            password="test-pass-123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)

        self.caratt_a = Punteggio.objects.create(
            nome="Forza Test",
            sigla="FRT",
            tipo=CARATTERISTICA,
            colore="#111111",
        )
        self.caratt_b = Punteggio.objects.create(
            nome="Mente Test",
            sigla="MNT",
            tipo=CARATTERISTICA,
            colore="#222222",
        )
        self.aura_magica = Punteggio.objects.create(
            nome="Aura Magica",
            sigla="AMA",
            tipo=AURA,
            colore="#333333",
        )
        self.aura_alt = Punteggio.objects.create(
            nome="Aura Alt",
            sigla="ALT",
            tipo=AURA,
            colore="#444444",
        )
        self.mattone_fuoco = Mattone.objects.create(
            nome="Fuoco",
            sigla="MFU",
            tipo="MA",
            colore="#ff3300",
            aura=self.aura_magica,
            caratteristica_associata=self.caratt_a,
            dichiarazione="Fuoco",
        )
        self.mattone_gelo = Mattone.objects.create(
            nome="Gelo",
            sigla="MGE",
            tipo="MA",
            colore="#33ccff",
            aura=self.aura_magica,
            caratteristica_associata=self.caratt_b,
            dichiarazione="Gelo",
        )
        Mattone.objects.create(
            nome="Altro",
            sigla="MAL",
            tipo="MA",
            colore="#999999",
            aura=self.aura_alt,
            caratteristica_associata=self.caratt_a,
            dichiarazione="Altro",
        )
        self.abilita = Abilita.objects.create(
            nome="Abilita Regola Formula",
            caratteristica=self.caratt_a,
            costo_pc=0,
            costo_crediti=0,
        )

    def test_semantic_options_endpoint_returns_only_ama_mattoni(self):
        res = self.client.get("/api/personaggi/api/staff/formula-semantic-options/")
        self.assertEqual(res.status_code, 200)
        labels = [row.get("label") for row in res.data.get("elementi_mattoni", [])]
        self.assertIn("Fuoco", labels)
        self.assertIn("Gelo", labels)
        self.assertNotIn("Altro", labels)

    def test_staff_abilita_patch_and_get_formula_rules(self):
        payload = {
            "formula_rules": [
                {
                    "scope": "WEA",
                    "rule_type": "ELEMENT_REPLACE",
                    "from_mattone": self.mattone_fuoco.id,
                    "to_mattone": self.mattone_gelo.id,
                    "priority": 10,
                }
            ]
        }
        patch_res = self.client.patch(
            f"/api/personaggi/api/staff/abilita/{self.abilita.id}/",
            payload,
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(AbilitaFormulaRule.objects.filter(abilita=self.abilita).count(), 1)

        get_res = self.client.get(f"/api/personaggi/api/staff/abilita/{self.abilita.id}/")
        self.assertEqual(get_res.status_code, 200)
        rules = get_res.data.get("formula_rules", [])
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].get("from_mattone"), self.mattone_fuoco.id)
        self.assertEqual(rules[0].get("to_mattone"), self.mattone_gelo.id)
