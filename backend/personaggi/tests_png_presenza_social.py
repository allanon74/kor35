"""Presenza social opzionale dei PnG: tag, chiamate, messaggi, pubblicazione."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from personaggi.chiamate_vocali import avvia_chiamata
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    Campagna,
    CampagnaUtente,
    ChiamataVocale,
    Messaggio,
    Personaggio,
    TipologiaPersonaggio,
)
from personaggi.png_presenza_social import CAMPO_TAG, filtra_ids_funzione
from social.models import extract_mentioned_personaggi_ids
from social.views import SocialPostViewSet

User = get_user_model()


class PngPresenzaSocialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.player = User.objects.create_user(username="pngsoc_player", password="x")
        cls.peer = User.objects.create_user(username="pngsoc_peer", password="x")
        cls.master = User.objects.create_user(username="pngsoc_master", password="x")
        CampagnaUtente.objects.update_or_create(
            user=cls.player,
            campagna=cls.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_PLAYER, "attivo": True},
        )
        CampagnaUtente.objects.update_or_create(
            user=cls.master,
            campagna=cls.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_MASTER, "attivo": True},
        )
        cls.tipo_pg = TipologiaPersonaggio.objects.create(nome="Tipo PG presenza", giocante=True)
        cls.tipo_png = TipologiaPersonaggio.objects.create(nome="Tipo PnG presenza", giocante=False)
        cls.pg = Personaggio.objects.create(
            nome="Luce Presenza",
            proprietario=cls.player,
            campagna=cls.campagna,
            tipologia=cls.tipo_pg,
            png_tag_instafame=False,
            png_chiamabile=False,
            png_destinatario_messaggi=False,
            png_pubblica_instafame=False,
        )
        cls.png = Personaggio.objects.create(
            nome="Ombra Presenza",
            proprietario=cls.peer,
            campagna=cls.campagna,
            tipologia=cls.tipo_png,
            png_tag_instafame=False,
            png_chiamabile=False,
            png_destinatario_messaggi=False,
            png_pubblica_instafame=False,
        )
        cls.png_aperto = Personaggio.objects.create(
            nome="Voce Presenza",
            proprietario=cls.peer,
            campagna=cls.campagna,
            tipologia=cls.tipo_png,
        )

    def setUp(self):
        Personaggio.objects.filter(pk=self.png.pk).update(
            proprietario=self.peer,
            png_tag_instafame=False,
            png_chiamabile=False,
            png_destinatario_messaggi=False,
            png_pubblica_instafame=False,
        )
        self.png.refresh_from_db()
        ChiamataVocale.objects.filter(chiamante=self.pg).update(stato=ChiamataVocale.STATO_TERMINATA)

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        client.credentials(HTTP_X_CAMPAGNA=self.campagna.slug)
        return client

    def test_ricerca_uso_nasconde_solo_png_disattivato(self):
        client = self._client(self.player)
        base = "/api/personaggi/api/personaggi/search/"
        aperti = client.get(base, {"q": "Presenza"})
        self.assertEqual(aperti.status_code, 200)
        ids_aperti = {row["id"] for row in aperti.data}
        self.assertIn(self.png.id, ids_aperti)
        self.assertIn(self.pg.id, ids_aperti)
        self.assertIn(self.png_aperto.id, ids_aperti)

        messaggi = client.get(base, {"q": "Presenza", "uso": "messaggio"})
        ids_msg = {row["id"] for row in messaggi.data}
        self.assertNotIn(self.png.id, ids_msg)
        self.assertIn(self.pg.id, ids_msg)
        self.assertIn(self.png_aperto.id, ids_msg)

        menzioni = client.get(base, {"q": "Ombra", "uso": "menzione"})
        self.assertEqual({row["id"] for row in menzioni.data}, set())

        chiamate = client.get(base, {"q": "Ombra", "uso": "chiamata"})
        self.assertEqual({row["id"] for row in chiamate.data}, set())

    def test_menzione_ignora_png_non_taggabile_ma_non_il_pg(self):
        self.assertEqual(extract_mentioned_personaggi_ids(f"@{self.png.id}"), [])
        self.assertIn(self.pg.id, extract_mentioned_personaggi_ids(f"@{self.pg.id}"))
        self.assertEqual(filtra_ids_funzione([self.png.id, self.pg.id], CAMPO_TAG), [self.pg.id])

    def test_messaggio_rifiutato_e_risposta_consentita(self):
        client = self._client(self.player)
        url = "/api/personaggi/api/messaggi/send/"
        rifiuto = client.post(
            url,
            {
                "mittente_personaggio_id": self.pg.id,
                "destinatario_id": self.png.id,
                "titolo": "Ciao",
                "testo": "Testo",
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(rifiuto.status_code, 400, rifiuto.data)

        Messaggio.objects.create(
            mittente=self.peer,
            mittente_personaggio=self.png,
            destinatario_personaggio=self.pg,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            titolo="Prima io",
            testo="Apro io",
            campagna=self.campagna,
        )
        risposta = client.post(
            url,
            {
                "mittente_personaggio_id": self.pg.id,
                "destinatario_id": self.png.id,
                "titolo": "Re",
                "testo": "Ti rispondo",
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(risposta.status_code, 201, getattr(risposta, "data", None))

    def test_chiamata_rifiutata_per_png_non_chiamabile(self):
        with self.assertRaisesMessage(ValueError, "non può ricevere chiamate"):
            avvia_chiamata(chiamante=self.pg, chiamato=self.png, verso_staff=False)
        call = avvia_chiamata(chiamante=self.pg, chiamato=self.png_aperto, verso_staff=False)
        self.assertEqual(call.chiamato_id, self.png_aperto.id)
        call.stato = ChiamataVocale.STATO_TERMINATA
        call.save(update_fields=["stato", "updated_at"])

    def test_pubblicazione_bloccata_solo_sul_png(self):
        factory = APIRequestFactory()
        view = SocialPostViewSet.as_view({"post": "create"})

        def _post(personaggio):
            request = factory.post(
                f"/api/social/posts/?personaggio_id={personaggio.id}",
                {
                    "titolo": "Titolo",
                    "testo": "Corpo del post",
                    "visibilita": "PUB",
                    "personaggio_id": personaggio.id,
                },
                format="json",
            )
            force_authenticate(request, user=personaggio.proprietario)
            request.META["HTTP_X_CAMPAGNA"] = self.campagna.slug
            return view(request)

        blocco = _post(self.png)
        self.assertEqual(blocco.status_code, 403, blocco.data)
        ok = _post(self.pg)
        self.assertIn(ok.status_code, (200, 201), ok.data)

    def test_staff_imposta_flag_da_profilo_e_dashboard(self):
        client = self._client(self.master)
        player = self._client(self.peer)
        ignorato = player.patch(
            f"/api/social/profile/me/?personaggio_id={self.png.id}",
            {"presenza_social": {"pubblica_instafame": True, "destinatario_messaggi": True}},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(ignorato.status_code, 200, ignorato.data)
        self.png.refresh_from_db()
        self.assertFalse(self.png.png_pubblica_instafame)
        self.assertFalse(self.png.png_destinatario_messaggi)

        self.png.proprietario = self.master
        self.png.save(update_fields=["proprietario", "updated_at"])
        profilo = client.patch(
            f"/api/social/profile/me/?personaggio_id={self.png.id}",
            {"presenza_social": {"tag_instafame": True, "chiamabile": False}},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(profilo.status_code, 200, profilo.data)
        self.png.refresh_from_db()
        self.assertTrue(self.png.png_tag_instafame)
        self.assertFalse(self.png.png_chiamabile)
        self.assertTrue(profilo.data["presenza_social"]["modificabile"])

        dashboard = client.patch(
            f"/api/personaggi/api/staff/personaggi/{self.png.id}/",
            {"png_pubblica_instafame": True, "png_destinatario_messaggi": True},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.png.refresh_from_db()
        self.assertTrue(self.png.png_pubblica_instafame)
        self.assertTrue(self.png.png_destinatario_messaggi)

        pg_blocco = client.patch(
            f"/api/personaggi/api/staff/personaggi/{self.pg.id}/",
            {"png_chiamabile": False},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(pg_blocco.status_code, 400, pg_blocco.data)

    def test_profilo_pubblico_espone_i_permessi_effettivi(self):
        client = self._client(self.player)
        data = client.get(f"/api/social/profiles/{self.png.id}/", HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(data.status_code, 200, data.data)
        self.assertFalse(data.data["chiamabile"])
        self.assertFalse(data.data["puo_ricevere_messaggi"])
        pg = client.get(f"/api/social/profiles/{self.pg.id}/", HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertTrue(pg.data["chiamabile"])
        self.assertTrue(pg.data["puo_ricevere_messaggi"])
