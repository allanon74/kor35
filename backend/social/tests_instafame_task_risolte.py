"""La riga «risolta» di un post InstaFame resta al proprietario e allo staff."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from gestione_plot.models import Evento, Missione, MissioneRisoluzione
from personaggi.models import CAMPAGNA_ROLE_PLAYER, CAMPAGNA_ROLE_STAFFER, Campagna, CampagnaUtente, Personaggio
from social.models import SocialPost
from social.views import SocialPostViewSet, SocialPublicPostDetailView


class TaskRisolteSulPostTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.owner = User.objects.create_user(username="task_post_owner", password="test")
        cls.altro = User.objects.create_user(username="task_post_altro", password="test")
        cls.staffer = User.objects.create_user(username="task_post_staff", password="test")
        for user, ruolo in (
            (cls.owner, CAMPAGNA_ROLE_PLAYER),
            (cls.altro, CAMPAGNA_ROLE_PLAYER),
            (cls.staffer, CAMPAGNA_ROLE_STAFFER),
        ):
            CampagnaUtente.objects.update_or_create(
                campagna=cls.campagna,
                user=user,
                defaults={"ruolo": ruolo, "attivo": True},
            )
        cls.autore = Personaggio.objects.create(
            nome="Autore del post", proprietario=cls.owner, campagna=cls.campagna
        )
        cls.altro_pg_owner = Personaggio.objects.create(
            nome="Secondo PG del proprietario", proprietario=cls.owner, campagna=cls.campagna
        )
        cls.lettore = Personaggio.objects.create(
            nome="Lettore", proprietario=cls.altro, campagna=cls.campagna
        )
        cls.staff_pg = Personaggio.objects.create(
            nome="PG staff", proprietario=cls.staffer, campagna=cls.campagna
        )
        ora = timezone.now()
        cls.evento = Evento.objects.create(
            titolo="Raduno al porto",
            data_inizio=ora,
            data_fine=ora + timedelta(days=1),
        )
        cls.post = SocialPost.objects.create(
            autore=cls.autore,
            titolo="Cartolina",
            testo="Dal molo",
            visibilita="PUB",
            evento=cls.evento,
        )
        missione = Missione.objects.create(titolo="Foto al molo", tipo_risoluzione=Missione.TIPO_POST_SOCIAL)
        MissioneRisoluzione.objects.create(
            missione=missione,
            evento=cls.evento,
            personaggio=cls.autore,
            social_post=cls.post,
        )

    def _riga(self, user, personaggio):
        factory = APIRequestFactory()
        view = SocialPostViewSet.as_view({"get": "list"})
        request = factory.get(
            "/api/social/posts/",
            {"personaggio_id": personaggio.id},
            HTTP_X_CAMPAGNA="kor35",
        )
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEqual(response.status_code, 200, response.data)
        items = response.data.get("results", response.data)
        return next(row for row in items if row["id"] == self.post.id)

    def test_proprietario_vede_la_riga_anche_da_un_altro_suo_personaggio(self):
        come_autore = self._riga(self.owner, self.autore)
        come_altro_pg = self._riga(self.owner, self.altro_pg_owner)
        for row in (come_autore, come_altro_pg):
            self.assertEqual(len(row["task_risolte"]), 1)
            self.assertEqual(row["task_risolte"][0]["missione_titolo"], "Foto al molo")
            self.assertEqual(row["task_risolte"][0]["evento_titolo"], "Raduno al porto")

    def test_staffer_vede_la_riga_e_un_altro_giocatore_no(self):
        staff = self._riga(self.staffer, self.staff_pg)
        self.assertEqual(staff["task_risolte"][0]["missione_titolo"], "Foto al molo")
        altro = self._riga(self.altro, self.lettore)
        self.assertEqual(altro["task_risolte"], [])

    def test_link_pubblico_non_mostra_la_risoluzione(self):
        factory = APIRequestFactory()
        view = SocialPublicPostDetailView.as_view()
        request = factory.get(f"/social/post/{self.post.public_slug}")
        response = view(request, slug=self.post.public_slug)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["task_risolte"], [])
