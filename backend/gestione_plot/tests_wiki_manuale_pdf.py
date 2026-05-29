from django.test import RequestFactory, TestCase

from gestione_plot.models import ManualePdf, PaginaRegolamento
from gestione_plot.wiki_pdf import get_pages_for_manuale


class WikiManualePdfTests(TestCase):
    def setUp(self):
        self.manuale = ManualePdf.objects.create(
            slug="test-manuale",
            titolo="Test",
            attivo=True,
        )
        self.pagina = PaginaRegolamento.objects.create(
            titolo="Pagina test",
            slug="pagina-test-pdf",
            contenuto="<p>Test</p>",
            public=True,
            includi_in_pdf=True,
        )
        self.pagina.manuali_pdf.add(self.manuale)

    def test_get_pages_for_manuale_filtra_opt_in(self):
        pages = get_pages_for_manuale(self.manuale, force_public=True)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].slug, "pagina-test-pdf")

    def test_pagina_non_inclusa_se_flag_spento(self):
        self.pagina.includi_in_pdf = False
        self.pagina.save(update_fields=["includi_in_pdf"])
        pages = get_pages_for_manuale(self.manuale, force_public=True)
        self.assertEqual(pages, [])
