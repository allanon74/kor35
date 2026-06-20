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
    FORMULA_RULE_SOURCE_APPEND,
    Mattone,
    Punteggio,
    Statistica,
    AURA,
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    build_exclusive_group_text,
    formatta_danno_formula,
    formatta_testo_generico,
    infer_weapon_damage_mode,
)


class FormulaBuilderLogicTests(TestCase):
    def test_bersaglio_flusso_and_dardo_set_gittata(self):
        flusso_stats = build_stats_by_selection({}, {"formula_target": "flusso"})
        self.assertEqual(flusso_stats["flusso"], 1)
        self.assertEqual(flusso_stats["gittata"], 3)

        dardo_stats = build_stats_by_selection({}, {"formula_target": "dardo"})
        self.assertEqual(dardo_stats["dardo"], 1)
        self.assertEqual(dardo_stats["gittata"], 10)

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
        selections = {"formula_damage_mode": "mischia"}

        merged = build_stats_by_selection(current, selections)

        self.assertEqual(merged["dmg_mischia"], 1)
        self.assertEqual(merged["dmg_distanza"], 0)
        self.assertEqual(merged["dannigen"], 2)
        self.assertEqual(merged["dannimis"], 3)
        self.assertEqual(merged["dannidis"], 5)

    def test_mischia_damage_preview_sums_dannigen_and_dannimis(self):
        stats = build_stats_by_selection(
            {"dannigen": 2, "dannimis": 1},
            {"formula_damage_mode": "mischia"},
        )
        formula = build_formula_template("attack", {"formula_damage_mode": "mischia"})
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertIn("tre!", rendered.lower())

    def test_distanza_damage_preview_sums_dannigen_and_dannidis(self):
        stats = build_stats_by_selection(
            {"dannigen": 2, "dannidis": 1},
            {"formula_damage_mode": "distanza"},
        )
        formula = build_formula_template("attack", {"formula_damage_mode": "distanza"})
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertIn("tre!", rendered.lower())

    def test_damage_total_one_is_omitted(self):
        stats = build_stats_by_selection(
            {"dannigen": 1, "dannimis": 0},
            {"formula_damage_mode": "mischia"},
        )
        formula = build_formula_template("attack", {"formula_damage_mode": "mischia"})
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertNotIn("uno", rendered.lower())
        self.assertNotIn("due!", rendered.lower())

    def test_mischia_one_damage_without_chop_stat_shows_implicit_chop(self):
        """Spada: solo dannimis=1, template con danni mischia — non formula vuota."""
        stats = build_stats_by_selection(
            {"dannimis": 1, "dannigen": 0},
            {"formula_damage_mode": "mischia"},
        )
        formula = (
            "{rango|:RANGO}{molt|:MOLT}{formula_prefix}{formula_target}"
            "{formula_source}{danni_mischia}{formula_status}"
        )
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertIn("(chop!)", rendered.lower())

    def test_distanza_one_damage_without_pierce_stat_shows_implicit_pierce(self):
        stats = build_stats_by_selection(
            {"dannidis": 1, "dannigen": 0},
            {"formula_damage_mode": "distanza"},
        )
        formula = "{formula_source}{danni_distanza}"
        rendered = render_formula_preview(formula=formula, stats_by_param=stats)
        self.assertIn("(pierce!)", rendered.lower())
        self.assertNotIn("uno", rendered.lower())

    def test_mischia_chop_with_damage_one_shows_paren_chop(self):
        stats = build_stats_by_selection(
            {"dannimis": 1, "dannigen": 0},
            {"formula_damage_mode": "mischia", "formula_source": ["chop"]},
        )
        formula = "{formula_source}{danni_mischia}"
        rendered = render_formula_preview(formula=formula, stats_by_param=stats).lower()
        self.assertIn("(chop!)", rendered)
        self.assertNotIn("uno", rendered)

    def test_build_formula_template_mischia_includes_source_by_default(self):
        tpl = build_formula_template("attack", {"formula_damage_mode": "mischia"})
        self.assertIn("{formula_source}", tpl)
        self.assertIn("{danni_mischia}", tpl)

    def test_build_formula_template_omit_source_excludes_placeholder(self):
        tpl = build_formula_template(
            "attack",
            {"formula_damage_mode": "mischia", "omit_formula_source": True},
        )
        self.assertNotIn("{formula_source}", tpl)
        self.assertIn("{danni_mischia}", tpl)

    def test_annulled_source_override_suppresses_source_entirely(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="formula_source_annul", password="x")
        from .models import Personaggio, PersonaggioAbilita

        caratt = Punteggio.objects.create(
            nome="Forza Annul",
            sigla="FAN",
            tipo=CARATTERISTICA,
            colore="#111111",
        )
        abilita = Abilita.objects.create(
            nome="Nascondi Chop",
            caratteristica=caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        pg = Personaggio.objects.create(nome="PG annul chop", proprietario=user)
        PersonaggioAbilita.objects.create(personaggio=pg, abilita=abilita)
        AbilitaFormulaRule.objects.create(
            abilita=abilita,
            scope="ATT",
            rule_type="SOURCE_OVERRIDE",
            source_label="",
            priority=10,
        )

        class FakeStat:
            def __init__(self, parametro):
                self.parametro = parametro

        class FakeItem:
            def __init__(self, parametro, valore_base):
                self.statistica = FakeStat(parametro)
                self.valore_base = valore_base

        stats = [FakeItem("chop", 1), FakeItem("dannimis", 2), FakeItem("dannigen", 0)]
        formula = "{formula_source}{danni_mischia}"
        rendered = formatta_testo_generico(
            "",
            formula=formula,
            statistiche_base=stats,
            personaggio=pg,
            context={"formula_kind": "ATT", "attack_formula_template": formula},
            solo_formula=True,
        ).lower()
        self.assertNotIn("chop", rendered)
        self.assertIn("due!", rendered)

    def test_annulled_blam_override_suppresses_blam(self):
        rendered = build_exclusive_group_text(
            "formula_source",
            {"blam": 1, "__formula_source_labels__": {"blam": ""}},
        )
        self.assertEqual(rendered.strip(), "")

    def test_formatta_danno_formula_display_rules(self):
        self.assertEqual(formatta_danno_formula(1), "")
        self.assertEqual(formatta_danno_formula(2), "due!")
        self.assertEqual(formatta_danno_formula(9), "nove!")
        self.assertEqual(formatta_danno_formula(10), "10!")
        self.assertEqual(formatta_danno_formula(12), "12!")

    def test_explicit_damage_placeholder_uses_display_rules(self):
        class FakeStat:
            def __init__(self, parametro):
                self.parametro = parametro

        class FakeItem:
            def __init__(self, parametro, valore_base):
                self.statistica = FakeStat(parametro)
                self.valore_base = valore_base

        for total, expected in ((1, ""), (3, "tre"), (12, "12")):
            stats = [FakeItem("dannidis", total)]
            formula = "Pierce! {dannidis + dannigen|D}"
            rendered = render_formula_preview(
                formula=formula,
                stats_by_param={"dannidis": total, "dannigen": 0},
            ).lower()
            self.assertIn("pierce!", rendered)
            if expected:
                self.assertIn(expected, rendered)
            else:
                self.assertNotIn("uno", rendered)
                self.assertNotIn("!", rendered.replace("pierce!", ""))

    def test_build_formula_template_writes_explicit_damage_expression(self):
        mischia_tpl = build_formula_template(
            "attack",
            {"formula_damage_mode": "mischia", "formula_source": ["chop"]},
        )
        self.assertIn("{formula_source}", mischia_tpl)
        self.assertIn("{danni_mischia}", mischia_tpl)
        self.assertNotIn("{formula_damage}", mischia_tpl)
        self.assertNotIn("Chop!", mischia_tpl)

        dist_tpl = build_formula_template(
            "attack",
            {"formula_damage_mode": "distanza", "formula_source": ["pierce"]},
        )
        self.assertIn("{formula_source}", dist_tpl)
        self.assertIn("{danni_distanza}", dist_tpl)
        self.assertNotIn("{formula_damage}", dist_tpl)
        self.assertNotIn("Pierce!", dist_tpl)

    def test_build_formula_template_without_damage_and_with_specific_effect(self):
        tpl = build_formula_template(
            "weave",
            {
                "formula_type": "aura",
                "formula_damage_mode": "none",
                "include_specific_effect": True,
                "effect_description": "Spegni la luce",
            },
        )
        self.assertNotIn("{danni_mischia}", tpl)
        self.assertNotIn("{danni_distanza}", tpl)
        self.assertIn("Effetto: Spegni la luce!", tpl)

    def test_build_formula_template_keeps_prefix_and_status_by_default(self):
        tpl = build_formula_template("attack", {"formula_damage_mode": "none"})
        self.assertIn("{formula_prefix}", tpl)
        self.assertIn("{formula_status}", tpl)

    def test_build_formula_template_capacity_prefixes_entity_name(self):
        tpl = build_formula_template(
            "capacity",
            {"entity_name": "ScanLink", "formula_source": ["mental"]},
        )
        self.assertTrue(tpl.startswith("Capacità ScanLink: "))
        self.assertIn("{formula_source}", tpl)
        self.assertNotIn("{formula_type}", tpl)

    def test_capacity_preview_renders_entity_prefix(self):
        stats = build_stats_by_selection({}, {"formula_source": ["mental"]})
        formula = build_formula_template(
            "capacity",
            {"entity_name": "ScanLink", "formula_source": ["mental"]},
        )
        rendered = render_formula_preview(
            formula=formula,
            stats_by_param=stats,
            context={"entity_name": "ScanLink"},
        )
        self.assertIn("Capacità ScanLink:", rendered)
        self.assertIn("Mental", rendered)

    def test_pierce_source_with_distanza_damage_shows_pierce_not_chop(self):
        stats = build_stats_by_selection(
            {"dannidis": 1, "dannigen": 0},
            {"formula_damage_mode": "distanza", "formula_source": ["pierce"]},
        )
        formula = build_formula_template(
            "attack",
            {"formula_damage_mode": "distanza", "formula_source": ["pierce"]},
        )
        rendered = render_formula_preview(formula=formula, stats_by_param=stats).lower()
        self.assertIn("pierce", rendered)
        self.assertNotIn("chop", rendered)

    def test_pierce_on_mischia_attack_keeps_pierce_not_chop(self):
        stats = build_stats_by_selection(
            {"dannimis": 1, "dannigen": 0},
            {"formula_damage_mode": "mischia", "formula_source": ["pierce"]},
        )
        formula = build_formula_template(
            "attack",
            {"formula_damage_mode": "mischia", "formula_source": ["pierce"]},
        )
        rendered = render_formula_preview(formula=formula, stats_by_param=stats).lower()
        self.assertIn("pierce", rendered)
        self.assertNotIn("chop", rendered)

    def test_persisted_formula_builder_selezioni_used_on_render(self):
        formula = build_formula_template(
            "attack",
            {"formula_damage_mode": "mischia", "formula_source": ["pierce"]},
        )
        selezioni = {
            "formula_type": "attack",
            "formula_damage_mode": "mischia",
            "formula_source": ["pierce"],
        }
        rendered = formatta_testo_generico(
            None,
            formula=formula,
            statistiche_base=[],
            context={
                "formula_builder_selezioni": selezioni,
                "attack_formula_template": formula,
            },
            solo_formula=True,
        ).lower()
        self.assertIn("pierce", rendered)
        self.assertNotIn("chop", rendered)

    def test_oggetto_base_listino_attacco_rispetta_formula_builder_selezioni(self):
        from .models import OggettoBase, TIPO_OGGETTO_FISICO
        from .serializers import OggettoBaseSerializer

        template = OggettoBase.objects.create(
            nome="Spada negozio pierce",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            costo=10,
            attacco_base=build_formula_template(
                "attack",
                {"formula_damage_mode": "mischia", "formula_source": ["pierce"]},
            ),
            formula_builder_selezioni={
                "formula_type": "attack",
                "formula_damage_mode": "mischia",
                "formula_source": ["pierce"],
            },
            in_vendita=True,
        )
        ser = OggettoBaseSerializer(template)
        rendered = (ser.data.get("attacco_formattato") or "").lower()
        self.assertIn("pierce", rendered)
        self.assertNotIn("chop", rendered)

    def test_weave_sources_are_always_explicit_with_bang(self):
        stats = build_stats_by_selection(
            {},
            {"formula_source": ["chop", "blam"]},
        )
        formula = "{formula_source}"
        rendered = render_formula_preview(
            formula=formula,
            stats_by_param=stats,
            context={"formula_kind": "WEA", "allow_implicit_formula_source": False},
        )
        self.assertIn("Chop!", rendered)
        self.assertIn("Blam!", rendered)
        self.assertIn("/", rendered)
        self.assertNotIn("(Chop!)", rendered)

    def test_weave_without_source_does_not_infer_chop(self):
        stats = build_stats_by_selection(
            {"dannimis": 1, "dannigen": 0},
            {"formula_damage_mode": "mischia"},
        )
        formula = "{formula_source}{danni_mischia}"
        rendered = render_formula_preview(
            formula=formula,
            stats_by_param=stats,
            context={"formula_kind": "WEA", "allow_implicit_formula_source": False},
        ).lower()
        self.assertNotIn("chop", rendered)

    def test_build_formula_template_excludes_always_blocks_when_requested(self):
        tpl = build_formula_template(
            "attack",
            {
                "formula_damage_mode": "none",
                "formula_source": ["chop"],
                "exclude_always_rango": True,
                "exclude_always_molt": True,
                "exclude_always_prefix": True,
                "exclude_always_status": True,
            },
        )
        self.assertIn("{formula_source}", tpl)
        self.assertNotIn("{rango|:RANGO}", tpl)
        self.assertNotIn("{molt|:MOLT}", tpl)
        self.assertNotIn("{formula_prefix}", tpl)
        self.assertNotIn("{formula_status}", tpl)

    def test_weave_source_chop_and_elemento_preview(self):
        from .models import Punteggio, ELEMENTO

        elemento = Punteggio.objects.create(
            nome="Fuoco",
            sigla="FEL",
            tipo=ELEMENTO,
            colore="#ff4400",
        )
        stats = build_stats_by_selection(
            {},
            {"formula_source": ["chop", "elemento_principale"], "source_element_id": str(elemento.id)},
        )
        formula = "{formula_source}"
        rendered = render_formula_preview(
            formula=formula,
            stats_by_param=stats,
            context={"formula_kind": "WEA", "elemento": elemento},
        ).lower()
        self.assertIn("chop", rendered)
        self.assertIn("fuoco", rendered)
        self.assertIn("/", rendered)

    def test_source_append_shows_chop_and_fuoco(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="formula_source_append", password="x")
        from .models import Personaggio, PersonaggioAbilita

        caratt = Punteggio.objects.create(
            nome="Forza Append",
            sigla="FAP",
            tipo=CARATTERISTICA,
            colore="#111111",
        )
        abilita = Abilita.objects.create(
            nome="Infusione Fuoco mischia",
            caratteristica=caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        pg = Personaggio.objects.create(nome="PG source append", proprietario=user)
        PersonaggioAbilita.objects.create(personaggio=pg, abilita=abilita)
        AbilitaFormulaRule.objects.create(
            abilita=abilita,
            scope="ATT",
            rule_type=FORMULA_RULE_SOURCE_APPEND,
            source_label="Fuoco",
            when_expr="chop > 0",
            priority=10,
        )

        class FakeStat:
            def __init__(self, parametro):
                self.parametro = parametro

        class FakeItem:
            def __init__(self, parametro, valore_base):
                self.statistica = FakeStat(parametro)
                self.valore_base = valore_base

        stats = [FakeItem("chop", 1), FakeItem("dannimis", 2), FakeItem("dannigen", 1)]
        formula = (
            "{rango|:RANGO}{molt|:MOLT}{formula_prefix}{formula_target}"
            "{formula_source}{danni_mischia}{formula_status}"
        )
        rendered = formatta_testo_generico(
            "",
            formula=formula,
            statistiche_base=stats,
            personaggio=pg,
            context={"formula_kind": "ATT", "attack_formula_template": formula},
            solo_formula=True,
        )
        lower = rendered.lower()
        self.assertIn("chop", lower)
        self.assertIn("fuoco", lower)
        self.assertIn("/", lower)

    def test_source_append_respects_when_expr(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="formula_source_append_skip", password="x")
        from .models import Personaggio, PersonaggioAbilita

        caratt = Punteggio.objects.create(
            nome="Forza Append Skip",
            sigla="FAS",
            tipo=CARATTERISTICA,
            colore="#222222",
        )
        abilita = Abilita.objects.create(
            nome="Infusione Fuoco distanza",
            caratteristica=caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        pg = Personaggio.objects.create(nome="PG source append skip", proprietario=user)
        PersonaggioAbilita.objects.create(personaggio=pg, abilita=abilita)
        AbilitaFormulaRule.objects.create(
            abilita=abilita,
            scope="ATT",
            rule_type=FORMULA_RULE_SOURCE_APPEND,
            source_label="Fuoco",
            when_expr="chop > 0",
            priority=10,
        )

        class FakeStat:
            def __init__(self, parametro):
                self.parametro = parametro

        class FakeItem:
            def __init__(self, parametro, valore_base):
                self.statistica = FakeStat(parametro)
                self.valore_base = valore_base

        stats = [FakeItem("pierce", 1)]
        formula = "{formula_source}"
        rendered = formatta_testo_generico(
            "",
            formula=formula,
            statistiche_base=stats,
            personaggio=pg,
            context={"formula_kind": "ATT", "attack_formula_template": formula},
            solo_formula=True,
        ).lower()
        self.assertIn("pierce", rendered)
        self.assertNotIn("fuoco", rendered)

    def test_infer_weapon_damage_mode_from_saved_formula_not_stats(self):
        self.assertEqual(
            infer_weapon_damage_mode(
                {"dannimis": 99, "dannidis": 0},
                {"attack_formula_template": "Pierce! {dannidis + dannigen|D}"},
            ),
            "distanza",
        )
        self.assertEqual(
            infer_weapon_damage_mode(
                {"dannidis": 99, "dannimis": 0},
                {"attack_formula_template": "Chop! {dannimis + dannigen|D}"},
            ),
            "mischia",
        )
        self.assertIsNone(
            infer_weapon_damage_mode({"dannidis": 1, "dannimis": 0}, {})
        )

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

        explicit_formula = "{rango|:RANGO}{molt|:MOLT}Pierce! {dannidis + dannigen|D}"
        rendered = formatta_testo_generico(
            "",
            formula=explicit_formula,
            statistiche_base=stats,
            personaggio=pg,
            context={"item_modifiers": [], "attack_formula_template": explicit_formula},
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
