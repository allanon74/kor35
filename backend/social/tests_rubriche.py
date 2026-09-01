"""Rubriche InstaFame: permessi, post di lancio e pubblicazione wiki."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from gestione_plot.models import PaginaRegolamento
from personaggi.campagna_moduli import (
    MODULO_RUBRICHE,
    apply_moduli_accesso,
    staff_tool_abilitato,
)
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
    Personaggio,
)
from social.models import SocialPost
from social.models_rubriche import (
    RUBRICA_ARTICOLO_BOZZA,
    RUBRICA_ARTICOLO_PUBBLICATO,
    Rubrica,
    RubricaArticolo,
    RubricaArticoloLike,
    RubricaPermessoScrittura,
)
from social.rubriche_wiki import (
    sync_id_pagina_articolo,
    sync_id_pagina_rubrica,
    sync_rubrica_to_wiki,
)
from social.views_rubriche import RubricaArticoloViewSet, RubricaViewSet


class RubricheTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.user_master = User.objects.create_user(username="rub_master", password="test")
        cls.user_staffer = User.objects.create_user(username="rub_staffer", password="test")
        cls.user_player = User.objects.create_user(username="rub_player", password="test")
        for user, ruolo in (
            (cls.user_master, CAMPAGNA_ROLE_MASTER),
            (cls.user_staffer, CAMPAGNA_ROLE_STAFFER),
            (cls.user_player, CAMPAGNA_ROLE_PLAYER),
        ):
            CampagnaUtente.objects.update_or_create(
                user=user, campagna=cls.campagna, defaults={"ruolo": ruolo, "attivo": True}
            )

        cls.pg_master = Personaggio.objects.create(
            nome="Master PG", proprietario=cls.user_master, campagna=cls.campagna
        )
        cls.pg_redattore = Personaggio.objects.create(
            nome="Cronista Vex", proprietario=cls.user_player, campagna=cls.campagna
        )
        cls.pg_lettore = Personaggio.objects.create(
            nome="Lettore Qua", proprietario=cls.user_player, campagna=cls.campagna
        )
        cls.factory = APIRequestFactory()

    def _chiama(self, view, request, user, **kwargs):
        force_authenticate(request, user=user)
        return view(request, **kwargs)


class RubricaCrudPermessiTests(RubricheTestBase):
    def test_staffer_non_puo_creare_rubrica(self):
        view = RubricaViewSet.as_view({"post": "create"})
        request = self.factory.post("/api/social/rubriche/", {"nome": "Eco del Bosco"})
        response = self._chiama(view, request, self.user_staffer)
        self.assertEqual(response.status_code, 403, response.data)

    def test_master_crea_rubrica_con_slug(self):
        view = RubricaViewSet.as_view({"post": "create"})
        request = self.factory.post("/api/social/rubriche/", {"nome": "Eco del Bosco"})
        response = self._chiama(view, request, self.user_master)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["slug"], "eco-del-bosco")
        self.assertTrue(response.data["can_write"])

    def test_permessi_scrittura_solo_staff(self):
        """Via URL reale: l'action ha permessi propri (staff+), diversi dal CRUD rubrica."""
        rubrica = Rubrica.objects.create(nome="Cronache Rubrica Test")
        url = f"/api/social/rubriche/{rubrica.id}/permessi/"
        payload = {"personaggio_target_id": str(self.pg_redattore.id)}

        self.client.force_login(self.user_player)
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 403, response.content)

        self.client.force_login(self.user_staffer)
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            RubricaPermessoScrittura.objects.filter(
                rubrica=rubrica, personaggio=self.pg_redattore, attivo=True
            ).exists()
        )


class ArticoloScritturaTests(RubricheTestBase):
    def setUp(self):
        self.rubrica = Rubrica.objects.create(nome="Voci dal Fronte")

    def _payload(self, **extra):
        payload = {
            "rubrica": str(self.rubrica.id),
            "titolo": "Il silenzio delle torri",
            "corpo": "<p>Parole a sufficienza per il conteggio.</p>",
            "stato": RUBRICA_ARTICOLO_PUBBLICATO,
        }
        payload.update(extra)
        return payload

    def test_personaggio_senza_permesso_non_scrive(self):
        view = RubricaArticoloViewSet.as_view({"post": "create"})
        request = self.factory.post(
            f"/api/social/rubriche-articoli/?personaggio_id={self.pg_redattore.id}",
            self._payload(),
        )
        response = self._chiama(view, request, self.user_player)
        self.assertEqual(response.status_code, 403, response.data)

    def test_personaggio_autorizzato_scrive_e_firma_col_proprio_pg(self):
        RubricaPermessoScrittura.objects.create(
            rubrica=self.rubrica, personaggio=self.pg_redattore
        )
        view = RubricaArticoloViewSet.as_view({"post": "create"})
        request = self.factory.post(
            f"/api/social/rubriche-articoli/?personaggio_id={self.pg_redattore.id}",
            self._payload(),
        )
        response = self._chiama(view, request, self.user_player)
        self.assertEqual(response.status_code, 201, response.data)
        articolo = RubricaArticolo.objects.get(id=response.data["id"])
        self.assertEqual(articolo.autore_personaggio_id, self.pg_redattore.id)
        self.assertIsNotNone(articolo.data_pubblicazione)

    def test_staff_puo_firmare_con_firma_libera(self):
        view = RubricaArticoloViewSet.as_view({"post": "create"})
        request = self.factory.post(
            "/api/social/rubriche-articoli/",
            self._payload(firma_libera="La Redazione"),
        )
        response = self._chiama(view, request, self.user_staffer)
        self.assertEqual(response.status_code, 201, response.data)
        articolo = RubricaArticolo.objects.get(id=response.data["id"])
        self.assertIsNone(articolo.autore_personaggio_id)
        self.assertEqual(articolo.firma, "La Redazione")

    def test_hero_immagine_con_path_uuid_non_supera_max_length(self):
        """
        Path tipico: social/rubriche/<uuid>/articoli/<uuid>/<file>.jpg (>100 char).
        Senza max_length=255 Django risponde 400 SuspiciousFileOperation.
        """
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (320, 200), (30, 60, 90)).save(buf, format="JPEG", quality=85)
        hero = SimpleUploadedFile("copertina.jpg", buf.getvalue(), content_type="image/jpeg")

        view = RubricaArticoloViewSet.as_view({"post": "create"})
        request = self.factory.post(
            f"/api/social/rubriche-articoli/?personaggio_id={self.pg_master.id}",
            self._payload(firma_libera="Redazione", hero_immagine=hero),
            format="multipart",
        )
        response = self._chiama(view, request, self.user_master)
        self.assertEqual(response.status_code, 201, getattr(response, "data", None))
        articolo = RubricaArticolo.objects.get(id=response.data["id"])
        self.assertTrue(articolo.hero_immagine.name)
        self.assertLessEqual(len(articolo.hero_immagine.name), 255)
        self.assertIn(str(self.rubrica.id), articolo.hero_immagine.name)
        self.assertIn(str(articolo.id), articolo.hero_immagine.name)

    def test_bozza_non_visibile_agli_altri_personaggi(self):
        RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Bozza riservata",
            firma_libera="Redazione",
            stato=RUBRICA_ARTICOLO_BOZZA,
        )
        view = RubricaArticoloViewSet.as_view({"get": "list"})
        request = self.factory.get(
            f"/api/social/rubriche-articoli/?personaggio_id={self.pg_lettore.id}"
        )
        response = self._chiama(view, request, self.user_player)
        self.assertEqual(response.status_code, 200)
        titoli = [riga["titolo"] for riga in response.data["results"]]
        self.assertNotIn("Bozza riservata", titoli)


class ArticoloInterazioniTests(RubricheTestBase):
    def setUp(self):
        self.rubrica = Rubrica.objects.create(nome="Rubrica Interazioni")
        self.articolo = RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Notizie dal bosco",
            firma_libera="Redazione",
            stato=RUBRICA_ARTICOLO_PUBBLICATO,
        )

    def test_like_toggle_per_personaggio(self):
        view = RubricaArticoloViewSet.as_view({"post": "like"})
        url = f"/api/social/rubriche-articoli/{self.articolo.id}/like/?personaggio_id={self.pg_lettore.id}"

        response = self._chiama(view, self.factory.post(url), self.user_player, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            RubricaArticoloLike.objects.filter(
                articolo=self.articolo, autore=self.pg_lettore
            ).exists()
        )

        response = self._chiama(view, self.factory.post(url), self.user_player, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(
            RubricaArticoloLike.objects.filter(
                articolo=self.articolo, autore=self.pg_lettore
            ).exists()
        )

    def test_commento_creato_dal_personaggio_attivo(self):
        view = RubricaArticoloViewSet.as_view({"post": "comments"})
        request = self.factory.post(
            f"/api/social/rubriche-articoli/{self.articolo.id}/comments/?personaggio_id={self.pg_lettore.id}",
            {"testo": "Ottimo pezzo."},
        )
        response = self._chiama(view, request, self.user_player, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["autore"], self.pg_lettore.id)
        self.assertTrue(response.data["can_delete"])
        self.assertEqual(self.articolo.comments.count(), 1)

    def test_commento_altrui_non_cancellabile_dal_lettore(self):
        commento = self.articolo.comments.create(autore=self.pg_redattore, testo="Mio commento")
        view = RubricaArticoloViewSet.as_view({"delete": "comment_detail"})
        request = self.factory.delete(
            f"/api/social/rubriche-articoli/{self.articolo.id}/comments/{commento.id}/"
            f"?personaggio_id={self.pg_lettore.id}"
        )
        response = self._chiama(
            view, request, self.user_player, pk=str(self.articolo.id), comment_id=str(commento.id)
        )
        self.assertEqual(response.status_code, 403, getattr(response, "data", None))
        self.assertTrue(self.articolo.comments.filter(id=commento.id).exists())


class PostAnnuncioTests(RubricheTestBase):
    def setUp(self):
        self.rubrica = Rubrica.objects.create(nome="Rubrica Annunci")
        self.articolo = RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Esce il nuovo numero",
            sommario="Tutto quello che serve sapere.",
            autore_personaggio=self.pg_redattore,
            stato=RUBRICA_ARTICOLO_PUBBLICATO,
        )

    def test_post_annuncio_collega_articolo_e_non_si_duplica(self):
        view = RubricaArticoloViewSet.as_view({"post": "post_annuncio"})
        url = f"/api/social/rubriche-articoli/{self.articolo.id}/post-annuncio/"

        response = self._chiama(view, self.factory.post(url, {}), self.user_master, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 201, response.data)
        self.articolo.refresh_from_db()
        post = SocialPost.objects.get(id=response.data["post_id"])
        self.assertEqual(post.articolo_collegato_id, self.articolo.id)
        self.assertEqual(self.articolo.post_annuncio_id, post.id)
        self.assertIn("Rubrica Annunci", post.testo)

        response = self._chiama(view, self.factory.post(url, {}), self.user_master, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(SocialPost.objects.filter(articolo_collegato=self.articolo).count(), 1)

    def test_annuncio_rifiutato_su_bozza(self):
        bozza = RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Ancora in lavorazione",
            autore_personaggio=self.pg_redattore,
            stato=RUBRICA_ARTICOLO_BOZZA,
        )
        view = RubricaArticoloViewSet.as_view({"post": "post_annuncio"})
        request = self.factory.post(f"/api/social/rubriche-articoli/{bozza.id}/post-annuncio/", {})
        response = self._chiama(view, request, self.user_master, pk=str(bozza.id))
        self.assertEqual(response.status_code, 400, response.data)

    def test_annuncio_senza_personaggio_firmatario_da_errore(self):
        articolo = RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Firma libera",
            firma_libera="Redazione",
            stato=RUBRICA_ARTICOLO_PUBBLICATO,
        )
        view = RubricaArticoloViewSet.as_view({"post": "post_annuncio"})
        User = get_user_model()
        user_senza_pg = User.objects.create_user(username="rub_master_nopg", password="test")
        CampagnaUtente.objects.update_or_create(
            user=user_senza_pg,
            campagna=self.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_MASTER, "attivo": True},
        )
        request = self.factory.post(f"/api/social/rubriche-articoli/{articolo.id}/post-annuncio/", {})
        response = self._chiama(view, request, user_senza_pg, pk=str(articolo.id))
        self.assertEqual(response.status_code, 400, response.data)

    def test_annuncio_fallito_annulla_anche_la_creazione_articolo(self):
        view = RubricaArticoloViewSet.as_view({"post": "create"})
        request = self.factory.post(
            "/api/social/rubriche-articoli/",
            {
                "rubrica": str(self.rubrica.id),
                "titolo": "Pezzo con annuncio impossibile",
                "firma_libera": "Redazione",
                "stato": RUBRICA_ARTICOLO_PUBBLICATO,
                "crea_post_annuncio": "1",
            },
        )
        User = get_user_model()
        user_senza_pg = User.objects.create_user(username="rub_staff_nopg", password="test")
        CampagnaUtente.objects.update_or_create(
            user=user_senza_pg,
            campagna=self.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_STAFFER, "attivo": True},
        )
        response = self._chiama(view, request, user_senza_pg)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(
            RubricaArticolo.objects.filter(titolo="Pezzo con annuncio impossibile").exists()
        )

    def test_preview_articolo_nel_serializer_del_post(self):
        from social.serializers import SocialPostSerializer

        post = SocialPost.objects.create(
            autore=self.pg_redattore,
            titolo="Segnalazione",
            testo="Leggete qui",
            visibilita="PUB",
            articolo_collegato=self.articolo,
        )
        dati = SocialPostSerializer(post, context={"personaggio": self.pg_lettore}).data
        self.assertIsNotNone(dati["articolo_preview"])
        self.assertEqual(dati["articolo_preview"]["titolo"], "Esce il nuovo numero")
        self.assertEqual(dati["articolo_preview"]["rubrica_nome"], "Rubrica Annunci")


class RubricaWikiTests(RubricheTestBase):
    def setUp(self):
        self.parent = PaginaRegolamento.objects.create(titolo="Ambientazione", slug="ambientazione")
        self.rubrica = Rubrica.objects.create(
            nome="Il Corriere di Kor",
            pubblica_in_wiki=True,
            wiki_parent=self.parent,
            wiki_titolo="Corriere di Kor",
            wiki_ordine=3,
        )
        self.articolo = RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Prima pagina",
            corpo="<p>Testo dell'articolo.</p>",
            firma_libera="Redazione",
            stato=RUBRICA_ARTICOLO_PUBBLICATO,
        )

    def test_sync_crea_indice_e_sottopagina_con_sync_id_deterministico(self):
        esito = sync_rubrica_to_wiki(self.rubrica)
        self.assertTrue(esito["pubblicata"])
        self.assertEqual(esito["articoli"], 1)

        pagina = PaginaRegolamento.objects.get(sync_id=sync_id_pagina_rubrica(self.rubrica))
        self.assertEqual(pagina.titolo, "Corriere di Kor")
        self.assertEqual(pagina.parent_id, self.parent.id)
        self.assertEqual(pagina.ordine, 3)

        sottopagina = PaginaRegolamento.objects.get(sync_id=sync_id_pagina_articolo(self.articolo))
        self.assertEqual(sottopagina.parent_id, pagina.id)
        self.assertIn("Testo dell'articolo.", sottopagina.contenuto)

        # Idempotente: nessun duplicato al secondo passaggio.
        sync_rubrica_to_wiki(self.rubrica)
        self.assertEqual(PaginaRegolamento.objects.filter(parent=pagina).count(), 1)

    def test_bozza_non_finisce_in_wiki(self):
        self.articolo.stato = RUBRICA_ARTICOLO_BOZZA
        self.articolo.save()
        sync_rubrica_to_wiki(self.rubrica)
        self.assertFalse(
            PaginaRegolamento.objects.filter(sync_id=sync_id_pagina_articolo(self.articolo)).exists()
        )

    def test_disattivare_pubblicazione_rimuove_le_pagine(self):
        sync_rubrica_to_wiki(self.rubrica)
        self.rubrica.pubblica_in_wiki = False
        esito = sync_rubrica_to_wiki(self.rubrica)
        self.assertFalse(esito["pubblicata"])
        self.assertEqual(esito["pagine_rimosse"], 2)
        self.assertFalse(
            PaginaRegolamento.objects.filter(sync_id=sync_id_pagina_rubrica(self.rubrica)).exists()
        )

    def test_eliminare_la_rubrica_non_lascia_pagine_orfane(self):
        sync_rubrica_to_wiki(self.rubrica)
        with self.captureOnCommitCallbacks(execute=True):
            self.rubrica.delete()
        self.assertFalse(
            PaginaRegolamento.objects.filter(sync_id=sync_id_pagina_rubrica(self.rubrica)).exists()
        )
        self.assertFalse(
            PaginaRegolamento.objects.filter(sync_id=sync_id_pagina_articolo(self.articolo)).exists()
        )


class ModuloRubricheTests(RubricheTestBase):
    """Interruttore campagna OFF / TEST (staff only) / OPEN."""

    def setUp(self):
        Rubrica.objects.create(nome="Rubrica gated")

    def _imposta_modulo(self, modo):
        apply_moduli_accesso(self.campagna, {MODULO_RUBRICHE: modo})

    def _lista_rubriche(self, user, personaggio):
        view = RubricaViewSet.as_view({"get": "list"})
        request = self.factory.get(f"/api/social/rubriche/?personaggio_id={personaggio.id}")
        return self._chiama(view, request, user)

    def test_default_aperto_a_tutti(self):
        response = self._lista_rubriche(self.user_player, self.pg_lettore)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))

    def test_off_blocca_anche_lo_staff(self):
        self._imposta_modulo("OFF")
        for user, personaggio in (
            (self.user_player, self.pg_lettore),
            (self.user_master, self.pg_master),
        ):
            with self.subTest(user=user.username):
                response = self._lista_rubriche(user, personaggio)
                self.assertEqual(response.status_code, 403, getattr(response, "data", None))

    def test_test_riservato_a_staff_e_master(self):
        self._imposta_modulo("TEST")

        response = self._lista_rubriche(self.user_player, self.pg_lettore)
        self.assertEqual(response.status_code, 403, getattr(response, "data", None))

        response = self._lista_rubriche(self.user_master, self.pg_master)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))

    def test_articoli_seguono_lo_stesso_interruttore(self):
        self._imposta_modulo("OFF")
        view = RubricaArticoloViewSet.as_view({"get": "list"})
        request = self.factory.get(
            f"/api/social/rubriche-articoli/?personaggio_id={self.pg_lettore.id}"
        )
        response = self._chiama(view, request, self.user_player)
        self.assertEqual(response.status_code, 403, getattr(response, "data", None))

    def test_tool_staff_nascosto_solo_con_off(self):
        self._imposta_modulo("OFF")
        self.assertFalse(staff_tool_abilitato(self.campagna, "rubriche"))
        self._imposta_modulo("TEST")
        self.assertTrue(staff_tool_abilitato(self.campagna, "rubriche"))


class RubricaImgMarkerTests(RubricheTestBase):
    def setUp(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from social.models_rubriche import RubricaArticoloImmagine, rubrica_img_marker

        self.rubrica = Rubrica.objects.create(nome="Marker Testata")
        self.articolo = RubricaArticolo.objects.create(
            rubrica=self.rubrica,
            titolo="Con marker",
            corpo="<p>Prima</p>",
            firma_libera="Redazione",
            stato=RUBRICA_ARTICOLO_PUBBLICATO,
        )
        buf = BytesIO()
        Image.new("RGB", (120, 80), (10, 20, 30)).save(buf, format="JPEG")
        uploaded = SimpleUploadedFile("g1.jpg", buf.getvalue(), content_type="image/jpeg")
        self.img = RubricaArticoloImmagine.objects.create(
            articolo=self.articolo,
            immagine=uploaded,
            didascalia="Figura 1",
            layout="wide",
            ordine=0,
        )
        self.marker = rubrica_img_marker(self.img.id)
        self.articolo.corpo = f"<p>Prima</p><p>{self.marker}</p><p>Dopo</p>"
        self.articolo.save(update_fields=["corpo", "updated_at", "tempo_lettura_min"])

    def test_detail_espone_layout_e_marker(self):
        view = RubricaArticoloViewSet.as_view({"get": "retrieve"})
        request = self.factory.get(f"/api/social/rubriche-articoli/{self.articolo.id}/")
        response = self._chiama(view, request, self.user_master, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["immagini"]), 1)
        self.assertEqual(response.data["immagini"][0]["layout"], "wide")
        self.assertEqual(response.data["immagini"][0]["marker"], self.marker)

    def test_immagini_meta_aggiorna_layout(self):
        import json

        view = RubricaArticoloViewSet.as_view({"patch": "partial_update"})
        request = self.factory.patch(
            f"/api/social/rubriche-articoli/{self.articolo.id}/",
            {
                "titolo": self.articolo.titolo,
                "immagini_meta": json.dumps(
                    [{"id": str(self.img.id), "layout": "float_left", "didascalia": "Nuova"}]
                ),
            },
            format="multipart",
        )
        response = self._chiama(view, request, self.user_master, pk=str(self.articolo.id))
        self.assertEqual(response.status_code, 200, response.data)
        self.img.refresh_from_db()
        self.assertEqual(self.img.layout, "float_left")
        self.assertEqual(self.img.didascalia, "Nuova")
        self.assertEqual(response.data["immagini"][0]["layout"], "float_left")

    def test_wiki_espande_marker_e_non_duplica_in_appendice(self):
        from social.rubriche_wiki import html_articolo

        html = html_articolo(self.articolo)
        self.assertIn("Figura 1", html)
        self.assertNotIn(self.marker, html)
        self.assertEqual(html.count("<figure"), 1)

    def test_extract_e_appendice(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from social.models_rubriche import RubricaArticoloImmagine
        from social.rubriche_markers import extract_rubrica_img_ids, immagini_non_posizionate

        self.assertEqual(extract_rubrica_img_ids(self.articolo.corpo), [str(self.img.id).lower()])

        buf = BytesIO()
        Image.new("RGB", (40, 40), (1, 2, 3)).save(buf, format="JPEG")
        orphan = RubricaArticoloImmagine.objects.create(
            articolo=self.articolo,
            immagine=SimpleUploadedFile("g2.jpg", buf.getvalue(), content_type="image/jpeg"),
            ordine=1,
        )
        orphans = immagini_non_posizionate(self.articolo.corpo, list(self.articolo.immagini.all()))
        self.assertEqual([o.id for o in orphans], [orphan.id])
