from django.test import SimpleTestCase

from personaggi.mse_kor35_game_spec import kor35_mse_game_spec, merge_kor35_game_meta
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
        self.assertIn("type", names)
        self.assertTrue(spec["has_keywords"])

    def test_merge_only_when_missing(self):
        meta = {"mse_game_spec": {"version": "custom"}}
        merged = merge_kor35_game_meta(meta)
        self.assertEqual(merged["mse_game_spec"]["version"], "custom")
        self.assertTrue(merged["mse_game_spec"].get("pack_types"))
        merged2 = merge_kor35_game_meta({})
        self.assertEqual(merged2["mse_game_spec"]["version"], "1")


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
