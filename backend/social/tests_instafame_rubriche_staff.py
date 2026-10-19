"""Citazioni, hashtag e gestione staff di post InstaFame e articoli rubrica."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import Evento
from personaggi.models import (
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
    Korp,
    Personaggio,
    TIER_3,
    TipoCarriera,
)
from social.models import SocialComment, SocialCommentLike, SocialPost, extract_hashtags
from social.models_rubriche import (
    RUBRICA_ARTICOLO_PUBBLICATO,
    Rubrica,
    RubricaArticolo,
    RubricaArticoloCommentTag,
    RubricaArticoloTag,
)
from social.views_rubriche import RubricaArticoloViewSet
from rest_framework.test import APIRequestFactory, force_authenticate


class RubricheMenzioniEStaffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.user_staff = User.objects.create_user(username="if_staff", password="test", email="if_staff@kor35.test")
        cls.user_player = User.objects.create_user(username="if_player", password="test")
        cls.user_autore = User.objects.create_user(username="if_autore", password="test")
        cls.user_citato = User.objects.create_user(username="if_citato", password="test")
        CampagnaUtente.objects.update_or_create(
            user=cls.user_staff, campagna=cls.campagna, defaults={"ruolo": CAMPAGNA_ROLE_STAFFER, "attivo": True}
        )
        cls.pg_staff = Personaggio.objects.create(nome="Staff Social", proprietario=cls.user_staff, campagna=cls.campagna)
        cls.pg_player = Personaggio.objects.create(nome="Lettore Feed", proprietario=cls.user_player, campagna=cls.campagna)
        cls.pg_autore = Personaggio.objects.create(nome="Cronista Nera", proprietario=cls.user_autore, campagna=cls.campagna)
        cls.pg_citato = Personaggio.objects.create(nome="Vance Citato", proprietario=cls.user_citato, campagna=cls.campagna)
        cls.rubrica = Rubrica.objects.create(nome="Cronache Instafame")
        ora = timezone.now()
        cls.evento = Evento.objects.create(
            titolo="Veglia di prova",
            data_inizio=ora - timedelta(hours=1),
            data_fine=ora + timedelta(hours=5),
        )
        tipo, _ = TipoCarriera.objects.get_or_create(codice="korp", defaults={"nome": "KORP"})
        cls.korp = Korp.objects.create(nome="KORP Staff Test", descrizione="", tipo=TIER_3, tipo_carriera=tipo)
        cls.factory = APIRequestFactory()

    def _articolo(self, **extra):
        dati = {
            "rubrica": self.rubrica,
            "titolo": "Notte sul fiume",
            "corpo": "<p>Un pezzo con #fiume e abbastanza parole.</p>",
            "autore_personaggio": self.pg_autore,
            "stato": RUBRICA_ARTICOLO_PUBBLICATO,
            "evento": self.evento,
        }
        dati.update(extra)
        return RubricaArticolo.objects.create(**dati)

    def test_commento_crea_tag_hashtag_e_notifiche(self):
        articolo = self._articolo()
        view = RubricaArticoloViewSet.as_view({"post": "comments"})
        request = self.factory.post(
            f"/api/social/rubriche-articoli/{articolo.id}/comments/?personaggio_id={self.pg_player.id}",
            {"testo": f"Letto @{self.pg_citato.id} #fiume"},
            format="json",
        )
        force_authenticate(request, user=self.user_player)
        with patch("personaggi.notify.notify_user") as mock_notify:
            response = view(request, pk=str(articolo.id))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["hashtags"], ["fiume"])
        self.assertEqual(response.data["tags"][0]["personaggio_id"], self.pg_citato.id)
        self.assertTrue(
            RubricaArticoloCommentTag.objects.filter(
                comment_id=response.data["id"], personaggio=self.pg_citato
            ).exists()
        )
        corpi = [call.kwargs.get("body", "") for call in mock_notify.call_args_list]
        self.assertTrue(any("ha citato" in corpo and "commento di rubrica" in corpo for corpo in corpi))
        self.assertTrue(any("ha commentato il tuo articolo" in corpo for corpo in corpi))
        destinatari = {call.args[0].id for call in mock_notify.call_args_list}
        self.assertIn(self.user_citato.id, destinatari)
        self.assertIn(self.user_autore.id, destinatari)

    def test_hashtag_nel_testo_articolo_e_filtro(self):
        articolo = self._articolo(titolo="Speciale #A-phone", sommario="Oggi parliamo di #A-phone.")
        from social.serializers_rubriche import RubricaArticoloDetailSerializer

        dati = RubricaArticoloDetailSerializer(articolo).data
        self.assertIn("a-phone", dati["hashtags"])
        self.assertFalse(RubricaArticoloTag.objects.filter(articolo=articolo).exists())
        view = RubricaArticoloViewSet.as_view({"get": "list"})
        request = self.factory.get(
            "/api/social/rubriche-articoli/",
            {"hashtag": "A-phone", "personaggio_id": self.pg_player.id},
        )
        force_authenticate(request, user=self.user_player)
        response = view(request)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        ids = [riga["id"] for riga in response.data["results"]]
        self.assertIn(str(articolo.id), ids)

    def test_notifiche_in_app_commento_e_citazione(self):
        articolo = self._articolo()
        view = RubricaArticoloViewSet.as_view({"post": "comments"})
        request = self.factory.post(
            f"/api/social/rubriche-articoli/{articolo.id}/comments/?personaggio_id={self.pg_player.id}",
            {"testo": f"Occhio @{self.pg_citato.id}"},
            format="json",
        )
        force_authenticate(request, user=self.user_player)
        with patch("personaggi.notify.notify_user"):
            response = view(request, pk=str(articolo.id))
        self.assertEqual(response.status_code, 201, response.data)

        self.client.force_login(self.user_autore)
        note = self.client.get(f"/api/social/notifications/?personaggio_id={self.pg_autore.id}")
        self.assertEqual(note.status_code, 200, note.content)
        self.assertIn("comment_rubrica", [riga["kind"] for riga in note.json()["results"]])

        self.client.force_login(self.user_citato)
        note = self.client.get(f"/api/social/notifications/?personaggio_id={self.pg_citato.id}")
        self.assertEqual(note.status_code, 200, note.content)
        self.assertIn("mention_comment_rubrica", [riga["kind"] for riga in note.json()["results"]])

    def test_citazione_nel_corpo_articolo(self):
        articolo = self._articolo(corpo=f"<p>Intervista a @{self.pg_citato.id} sul #porto.</p>")
        self.assertTrue(RubricaArticoloTag.objects.filter(articolo=articolo, personaggio=self.pg_citato).exists())

    def test_giocatore_non_gestisce_i_contenuti(self):
        self.client.force_login(self.user_player)
        response = self.client.get("/api/social/staff/contenuti/")
        self.assertEqual(response.status_code, 403)

    def test_staff_filtra_modifica_e_sposta(self):
        post = SocialPost.objects.create(
            autore=self.pg_player,
            titolo="Cartolina dal porto",
            testo=f"Saluti @{self.pg_citato.id} #porto",
            evento=self.evento,
            visibilita="KORP",
            korp_visibilita=self.korp,
        )
        commento = SocialComment.objects.create(post=post, autore=self.pg_autore, testo="Bello il post")
        SocialCommentLike.objects.create(comment=commento, autore=self.pg_citato, peso_like=3)
        self.client.force_login(self.user_staff)

        lista = self.client.get(
            "/api/social/staff/contenuti/",
            {"tipo": "post", "utente": "if_player", "korp_id": self.korp.id, "evento_id": self.evento.id, "hashtag": "porto"},
        )
        self.assertEqual(lista.status_code, 200, lista.content)
        self.assertEqual(lista.json()["count"], 1)
        self.assertEqual(lista.json()["results"][0]["id"], post.id)

        quando = "2024-03-02T18:30:00+00:00"
        patch = self.client.patch(
            f"/api/social/staff/contenuti/post/{post.id}/",
            data=json.dumps(
                {
                    "titolo": "Cartolina corretta",
                    "testo": f"Riedito @{self.pg_citato.id} #porto",
                    "autore": self.pg_autore.id,
                    "evento_id": self.evento.id,
                    "created_at": quando,
                    "visibilita": "PUB",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        post.refresh_from_db()
        self.assertEqual(post.titolo, "Cartolina corretta")
        self.assertEqual(post.autore_id, self.pg_autore.id)
        self.assertEqual(post.visibilita, "PUB")
        self.assertIsNone(post.korp_visibilita_id)
        self.assertEqual(post.created_at, datetime.fromisoformat(quando))
        self.assertIn(self.pg_citato.id, list(post.tags.values_list("personaggio_id", flat=True)))

        sposta = self.client.post(
            f"/api/social/staff/contenuti/post/{post.id}/sposta-in-rubrica/",
            data=json.dumps({"rubrica_id": str(self.rubrica.id), "mantieni_post_lancio": True}),
            content_type="application/json",
        )
        self.assertEqual(sposta.status_code, 201, sposta.content)
        post.refresh_from_db()
        self.assertIsNotNone(post.articolo_collegato_id)
        self.assertEqual(post.comments.count(), 0)
        articolo = post.articolo_collegato
        self.assertEqual(articolo.rubrica_id, self.rubrica.id)
        self.assertEqual(articolo.autore_personaggio_id, self.pg_autore.id)
        self.assertEqual(articolo.evento_id, self.evento.id)
        self.assertEqual(articolo.post_annuncio_id, post.id)
        self.assertEqual(articolo.comments.count(), 1)
        self.assertEqual(SocialCommentLike.objects.filter(comment__post=post).count(), 0)
        spostato = articolo.comments.get(testo="Bello il post")
        self.assertEqual(spostato.likes.count(), 1)
        self.assertEqual(spostato.likes.get().peso_like, 3)
        self.assertEqual(spostato.likes.get().autore_id, self.pg_citato.id)
        self.assertIn("#porto", articolo.corpo)
        self.assertTrue(articolo.comments.filter(testo="Bello il post").exists())
        self.assertIn("porto", extract_hashtags(articolo.corpo))
