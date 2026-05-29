import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from gestione_plot.models import ManualePdf, ManualePdfBatchJob, ManualePdfGenerazione, PaginaRegolamento
from gestione_plot.wiki_pdf_service import (
    build_manuali_zip_bundle,
    compute_wiki_pdf_diagnostica,
    create_batch_job,
    esegui_generazione_manuale,
)


class WikiPdfPhase3Tests(TestCase):
    def setUp(self):
        self.manuale = ManualePdf.objects.create(slug="p3-test", titolo="P3", attivo=True)
        self.pagina = PaginaRegolamento.objects.create(
            titolo="Pag",
            slug="pag-p3",
            contenuto="<p>x</p>",
            public=True,
            includi_in_pdf=True,
        )
        self.pagina.manuali_pdf.add(self.manuale)

    def test_diagnostica_segnala_senza_manuale(self):
        orphan = PaginaRegolamento.objects.create(
            titolo="Orfana",
            slug="orfana-p3",
            includi_in_pdf=True,
            public=True,
        )
        data = compute_wiki_pdf_diagnostica()
        slugs = [p["slug"] for p in data["incluse_senza_manuale"]]
        self.assertIn(orphan.slug, slugs)

    def test_create_batch_job_blocks_duplicate(self):
        ManualePdfBatchJob.objects.create(status=ManualePdfBatchJob.STATUS_RUNNING)
        with self.assertRaises(RuntimeError):
            create_batch_job()

    @patch("gestione_plot.wiki_pdf_service.generate_manuale_pdf")
    def test_esegui_generazione_crea_log(self, mock_gen):
        mock_gen.return_value = b"%PDF-fake"
        request = RequestFactory().get("/")
        request.META["HTTP_HOST"] = "testserver"
        log = esegui_generazione_manuale(
            self.manuale,
            request,
            lambda c, r: c,
            triggered_by_email="test@example.com",
        )
        self.assertTrue(log.success)
        self.assertEqual(ManualePdfGenerazione.objects.filter(manuale=self.manuale).count(), 1)
        self.assertGreater(log.file_size_bytes, 0)

    @patch("gestione_plot.wiki_pdf_service.generate_manuale_pdf")
    def test_zip_bundle(self, mock_gen):
        mock_gen.return_value = b"%PDF-fake"
        request = RequestFactory().get("/")
        request.META["HTTP_HOST"] = "testserver"
        esegui_generazione_manuale(self.manuale, request, lambda c, r: c)
        path = build_manuali_zip_bundle()
        self.assertTrue(path.exists())
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
        self.assertTrue(any("p3-test" in n for n in names))
