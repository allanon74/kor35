from django.test import SimpleTestCase

from gestione_plot.wiki_pdf_styles import merge_manuale_stile, resolve_manuale_stile
from gestione_plot.wiki_pdf import build_toc_entries
from gestione_plot.models import ManualePdf, PaginaRegolamento


class WikiPdfStylesTests(SimpleTestCase):
    def test_merge_override_font_size(self):
        stile = merge_manuale_stile("giocatore", {"font_size_pt": 11})
        self.assertEqual(stile["font_size_pt"], 11)
        self.assertEqual(stile["formato"], "A5")

    def test_reference_hide_images(self):
        stile = merge_manuale_stile("reference", None)
        self.assertTrue(stile["hide_images"])

    def test_resolve_manuale_stile(self):
        manuale = ManualePdf(stile_preset="master", stile={"font_size_pt": 12})
        stile = resolve_manuale_stile(manuale)
        self.assertEqual(stile["formato"], "A4")
        self.assertEqual(stile["font_size_pt"], 12)


class WikiPdfTocTests(SimpleTestCase):
    def test_toc_depth(self):
        """La profondità dell'indice segue `inizio_capitolo`, non l'albero wiki."""
        root = PaginaRegolamento(titolo="Root", slug="root", pk=1, parent_id=None)
        child = PaginaRegolamento(titolo="Child", slug="child", pk=2, parent_id=1)
        pages = [root, child]
        rendered = [
            {
                "slug": "root",
                "titolo": "Root",
                "chapter_num": 1,
                "solo_indice": False,
                "inizio_capitolo": True,
            },
            {
                "slug": "child",
                "titolo": "Child",
                "chapter_num": None,
                "solo_indice": False,
                "inizio_capitolo": False,
            },
        ]
        toc = build_toc_entries(pages, rendered, max_depth=3)
        self.assertEqual(toc[0]["depth"], 0)
        self.assertEqual(toc[1]["depth"], 1)

    def test_toc_depth_limitata_da_max_depth(self):
        rendered = [{"slug": "child", "titolo": "Child", "inizio_capitolo": False}]
        toc = build_toc_entries([], rendered, max_depth=1)
        self.assertEqual(toc[0]["depth"], 0)
