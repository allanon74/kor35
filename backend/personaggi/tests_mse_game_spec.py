from django.test import SimpleTestCase

from personaggi.mse_kor35_game_spec import kor35_mse_game_spec, merge_kor35_game_meta
from personaggi.mse_set_import import map_mse_card_to_kor35, parse_mse_set, parse_mse_symbol_font
from personaggi.mse_style_import import parse_mse_game_spec, parse_mse_style_spec


class MseGameSpecParserTests(SimpleTestCase):
    def test_parse_choice_colors_and_package_choice(self):
        sample = """
card field:
    type: choice
    name: Color
    choice colors cardlist:
        red: rgb(255,0,0)
card field:
    type: package choice
    name: Font
    match: magic-*.mse-symbol-font
    required: false
    empty name: (none)
card list color script:
    if card.color then card.color else rgb(0,0,0)
"""
        spec = parse_mse_game_spec(sample)
        self.assertEqual(spec["card_fields"][0]["choice_colors_cardlist"]["red"], "rgb(255,0,0)")
        self.assertEqual(spec["card_fields"][1]["match"], "magic-*.mse-symbol-font")
        self.assertFalse(spec["card_fields"][1]["required"])
        self.assertIn("card.color", spec["card_list_color_script"])


class Kor35MseGameSpecTests(SimpleTestCase):
    def test_kor35_spec_has_card_fields(self):
        spec = kor35_mse_game_spec()
        names = [f["name"] for f in spec["card_fields"]]
        self.assertIn("name", names)
        self.assertIn("code", names)
        self.assertIn("type", names)
        self.assertTrue(spec["has_keywords"])

    def test_kor35_spec_sette_aure_e_tipi_carta(self):
        from personaggi.carte_collezionabili_models import (
            CARTA_ENERGIA_ARCANA,
            CARTA_ENERGIA_INNATA,
            CARTA_ENERGIA_MAGICA,
            CARTA_ENERGIA_MARZIALE,
            CARTA_ENERGIA_PSIONICA,
            CARTA_ENERGIA_SACRA,
            CARTA_ENERGIA_TECNOLOGICA,
            CARTA_TIPO_EVENTO,
            CARTA_TIPO_LUOGO,
            CARTA_TIPO_OGGETTO,
            CARTA_TIPO_PERSONAGGIO,
        )

        spec = kor35_mse_game_spec()
        energy_field = next(f for f in spec["card_fields"] if f["name"] == "energy")
        type_field = next(f for f in spec["card_fields"] if f["name"] == "type")
        energy_choices = [c["name"] for c in energy_field["choices"]]
        type_choices = [c["name"] for c in type_field["choices"]]

        self.assertEqual(
            energy_choices,
            [
                CARTA_ENERGIA_MARZIALE,
                CARTA_ENERGIA_TECNOLOGICA,
                CARTA_ENERGIA_INNATA,
                CARTA_ENERGIA_MAGICA,
                CARTA_ENERGIA_SACRA,
                CARTA_ENERGIA_PSIONICA,
                CARTA_ENERGIA_ARCANA,
            ],
        )
        self.assertEqual(
            type_choices,
            [CARTA_TIPO_PERSONAGGIO, CARTA_TIPO_OGGETTO, CARTA_TIPO_LUOGO, CARTA_TIPO_EVENTO],
        )
        self.assertNotIn("FUO", energy_choices)
        self.assertNotIn("Creatura", type_choices)

    def test_merge_refreshes_stale_placeholder_spec(self):
        meta = {
            "mse_game_spec": {
                "version": "1",
                "card_fields": [
                    {
                        "name": "energy",
                        "choices": [{"name": "MAR"}, {"name": "FUO"}, {"name": "NAT"}],
                    }
                ],
            }
        }
        merged = merge_kor35_game_meta(meta)
        self.assertEqual(merged["mse_game_spec"]["version"], "kor35-sette-elegie-2")
        energy = next(f for f in merged["mse_game_spec"]["card_fields"] if f["name"] == "energy")
        self.assertEqual(len(energy["choices"]), 7)

    def test_merge_keeps_custom_spec_without_stale_choices(self):
        meta = {"mse_game_spec": {"version": "custom", "card_fields": []}}
        merged = merge_kor35_game_meta(meta)
        self.assertEqual(merged["mse_game_spec"]["version"], "custom")
        self.assertTrue(merged["mse_game_spec"].get("pack_types"))

    def test_merge_only_when_missing(self):
        merged2 = merge_kor35_game_meta({})
        self.assertEqual(merged2["mse_game_spec"]["version"], "kor35-sette-elegie-2")


class MseStyleSpecParserTests(SimpleTestCase):
    def test_parse_card_style_and_styling_fields(self):
        sample = """
game: mtg
card width: 375
card height: 523
card dpi: 300
card background: rgb(32,32,32)
styling field:
    type: boolean
    name: show border
    initial: true
card style:
    name:
        left: 34
        top: 53
        width: 307
        height: 31
        z index: 5
        visible: {card.name != ""}
        alignment: bottom center
        font:
            name: Arial
            size: 18
            color: black
    image:
        left: 19
        top: 19
        width: 337
        height: 400
        z index: 0
        render style: image
        image: {card.image}
"""
        spec = parse_mse_style_spec(sample)
        self.assertEqual(spec["card_size"]["width"], 375.0)
        self.assertEqual(spec["card_styles"]["name"]["left"]["kind"], "literal")
        self.assertEqual(spec["card_styles"]["name"]["visible"]["kind"], "script")
        self.assertEqual(spec["card_styles"]["image"]["render_style"]["value"], "image")
        self.assertEqual(len(spec["styling_fields"]), 1)
        self.assertEqual(spec["styling_fields"][0]["name"], "show border")


class MsePackTypeParserTests(SimpleTestCase):
    def test_parse_pack_type_and_items(self):
        sample = """
pack item:
    name: rare
    select: no replace
    filter: card.rarity == "rare"
pack item:
    name: common
    filter: card.rarity == "common"
pack type:
    name: booster pack
    select: all
    selectable: true
    item:
        name: rare
        amount: 1
    item: common
    item:
        name: common
        amount: 11
"""
        spec = parse_mse_game_spec(sample)
        self.assertEqual(len(spec["pack_items"]), 2)
        self.assertEqual(spec["pack_items"][0]["name"], "rare")
        self.assertEqual(spec["pack_items"][0]["filter"]["kind"], "script")
        self.assertEqual(len(spec["pack_types"]), 1)
        booster = spec["pack_types"][0]
        self.assertEqual(booster["name"], "booster pack")
        self.assertEqual(booster["select"], "all")
        self.assertGreaterEqual(len(booster["items"]), 2)


class MseSetParserTests(SimpleTestCase):
    def test_parse_mse_set_cards_and_set_info(self):
        sample = """
mse version: 2.0.0
game: kor35
stylesheet: demo.mse-style
short name: Demo
set info:
    title: Demo Set
    description: A test set
card:
    name: Fire Bolt
    code: FB01
    rules text: Deal 3 damage.
"""
        parsed = parse_mse_set(sample)
        self.assertEqual(parsed["meta"]["short_name"], "Demo")
        self.assertEqual(parsed["set_info"]["title"], "Demo Set")
        self.assertEqual(len(parsed["cards"]), 1)
        self.assertEqual(parsed["cards"][0]["name"], "Fire Bolt")

    def test_map_mse_card_to_kor35(self):
        mapped = map_mse_card_to_kor35({"name": "Bolt", "rules text": "Ping", "code": "B1"})
        self.assertEqual(mapped["nome"], "Bolt")
        self.assertEqual(mapped["codice"], "B1")
        self.assertEqual(mapped["testo_gioco"], "Ping")


class MseSymbolFontParserTests(SimpleTestCase):
    def test_parse_symbol_font_codes(self):
        sample = """
symbol:
    code: {W}
    image: white.png
symbol:
    code: {U}
    image: blue.png
"""
        parsed = parse_mse_symbol_font(sample)
        self.assertIn("{W}", parsed["symbols"])
        self.assertEqual(parsed["symbols"]["{W}"]["image"], "white.png")
        self.assertEqual(parsed["symbols"]["{U}"]["code"], "{U}")


class Kor35AuraSymbolFontTests(SimpleTestCase):
    def test_build_symbol_font_zip_has_seven_aure(self):
        from io import BytesIO

        from personaggi.mse_kor35_symbol_font import (
            KOR35_AURA_GLYPHS,
            build_kor35_symbol_font_text,
            build_kor35_symbol_font_zip,
        )
        from personaggi.mse_set_import import parse_mse_symbol_font

        text = build_kor35_symbol_font_text()
        parsed = parse_mse_symbol_font(text)
        self.assertEqual(len(parsed["symbols"]), len(KOR35_AURA_GLYPHS))
        self.assertIn("{MAR}", parsed["symbols"])
        self.assertIn("{ARC}", parsed["symbols"])

        data = build_kor35_symbol_font_zip()
        import zipfile

        with zipfile.ZipFile(BytesIO(data)) as zf:
            names = zf.namelist()
            self.assertIn("symbol font", names)
            self.assertIn("symbols/mar.png", names)
            self.assertTrue(zf.read("symbols/mar.png").startswith(b"\x89PNG"))

    def test_kor35_style_energy_uses_symbol_render(self):
        from personaggi.mse_kor35_style import build_kor35_style_text
        from personaggi.mse_style_import import parse_mse_style_spec

        spec = parse_mse_style_spec(build_kor35_style_text())
        energy = spec["card_styles"]["energy"]
        render = energy.get("render_style") or {}
        self.assertEqual(render.get("value"), "symbol")
        self.assertTrue(energy.get("font", {}).get("always_symbol"))


class Kor35MseStyleGeneratorTests(SimpleTestCase):
    def test_build_style_zip_has_card_styles(self):
        from personaggi.mse_kor35_style import build_kor35_mse_style_zip, build_kor35_style_text
        from personaggi.mse_style_import import parse_mse_style_spec

        spec = parse_mse_style_spec(build_kor35_style_text())
        self.assertEqual(spec["game"], "kor35")
        self.assertIn("name", spec["card_styles"])
        self.assertIn("rules", spec["card_styles"])
        self.assertIn("card_frame", spec["card_styles"])
        self.assertGreaterEqual(len(spec["styling_fields"]), 2)

        data = build_kor35_mse_style_zip()
        self.assertGreater(len(data), 200)
        import zipfile
        from io import BytesIO

        with zipfile.ZipFile(BytesIO(data)) as zf:
            names = zf.namelist()
            self.assertIn("style", names)
            self.assertIn("images/frame.png", names)
            self.assertTrue(zf.read("images/frame.png").startswith(b"\x89PNG"))
