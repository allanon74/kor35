from django.test import RequestFactory, TestCase

from gestione_plot.models import ManualePdf, ManualePdfPagina, PaginaRegolamento
from gestione_plot.wiki_pdf import build_rendered_pages, get_pages_for_manuale


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

    def test_ordine_manuale_rispettato(self):
        p2 = PaginaRegolamento.objects.create(
            titolo="Seconda",
            slug="seconda-pdf",
            contenuto="<p>B</p>",
            public=True,
            includi_in_pdf=True,
        )
        p2.manuali_pdf.add(self.manuale)
        ManualePdfPagina.objects.filter(manuale=self.manuale, pagina=self.pagina).update(ordine=20)
        ManualePdfPagina.objects.filter(manuale=self.manuale, pagina=p2).update(ordine=10)

        pages = get_pages_for_manuale(self.manuale, force_public=True)
        self.assertEqual([p.slug for p in pages], ["seconda-pdf", "pagina-test-pdf"])

    def test_inizio_capitolo_non_incrementa_numero(self):
        p2 = PaginaRegolamento.objects.create(
            titolo="Sottosezione",
            slug="sottosezione-pdf",
            contenuto="<p>S</p>",
            public=True,
            includi_in_pdf=True,
        )
        p2.manuali_pdf.add(self.manuale)
        ManualePdfPagina.objects.filter(manuale=self.manuale, pagina=p2).update(inizio_capitolo=False)

        pages = get_pages_for_manuale(self.manuale, force_public=True)
        rendered = build_rendered_pages(pages, None, lambda html, _req: html)
        by_slug = {r["slug"]: r for r in rendered}
        self.assertEqual(by_slug["pagina-test-pdf"]["chapter_num"], 1)
        self.assertFalse(by_slug["sottosezione-pdf"]["inizio_capitolo"])
        self.assertIsNone(by_slug["sottosezione-pdf"]["chapter_num"])
