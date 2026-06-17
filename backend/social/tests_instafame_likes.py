"""Like InstaFame: un like per personaggio, non per giocatore."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from personaggi.models import Campagna, Personaggio
from social.models import SocialLike, SocialPost
from social.serializers import resolve_active_personaggio
from social.views import SocialPostViewSet


class InstafameMultiCharacterLikeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="like_multi_pg", password="test")
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.alt_campagna = Campagna.objects.create(slug="alt-like-test", nome="Alt", attiva=True)
        cls.pg_a = Personaggio.objects.create(
            nome="PG Alpha", proprietario=cls.user, campagna=cls.campagna
        )
        cls.pg_b = Personaggio.objects.create(
            nome="PG Beta", proprietario=cls.user, campagna=cls.campagna
        )
        cls.pg_alt = Personaggio.objects.create(
            nome="PG Alt Camp", proprietario=cls.user, campagna=cls.alt_campagna
        )
        cls.author = Personaggio.objects.create(nome="Autore Post", campagna=cls.campagna)
        cls.post = SocialPost.objects.create(
            autore=cls.author,
            titolo="Post test",
            testo="x",
            visibilita="PUB",
            likes_base=1,
        )

    def setUp(self):
        SocialLike.objects.filter(post=self.post, autore__in=[self.pg_a, self.pg_b, self.pg_alt]).delete()

    def test_resolve_explicit_personaggio_ignores_campaign_filter(self):
        factory = APIRequestFactory()
        request = factory.get("/api/social/posts/")
        request.META["HTTP_X_CAMPAGNA"] = "kor35"
        resolved = resolve_active_personaggio(self.user, str(self.pg_alt.id), request=request)
        self.assertEqual(resolved.id, self.pg_alt.id)

    def test_two_personaggi_same_user_can_like_same_post(self):
        factory = APIRequestFactory()
        view = SocialPostViewSet.as_view({"post": "like"})

        for pg in (self.pg_a, self.pg_b):
            request = factory.post(f"/api/social/posts/{self.post.id}/like/?personaggio_id={pg.id}")
            force_authenticate(request, user=self.user)
            response = view(request, pk=self.post.id)
            self.assertEqual(response.status_code, 201, response.data)
            self.assertTrue(response.data["liked"])

        like_ids = set(
            SocialLike.objects.filter(post=self.post, autore__in=[self.pg_a, self.pg_b]).values_list(
                "autore_id", flat=True
            )
        )
        self.assertEqual(like_ids, {self.pg_a.id, self.pg_b.id})

    def test_liked_by_me_is_per_active_personaggio(self):
        SocialLike.objects.create(post=self.post, autore=self.pg_a, peso_like=1)
        factory = APIRequestFactory()
        list_view = SocialPostViewSet.as_view({"get": "list"})

        for pg, expected in ((self.pg_a, True), (self.pg_b, False)):
            request = factory.get(f"/api/social/posts/?personaggio_id={pg.id}")
            force_authenticate(request, user=self.user)
            response = list_view(request)
            self.assertEqual(response.status_code, 200)
            items = response.data.get("results", response.data)
            row = next(item for item in items if item["id"] == self.post.id)
            self.assertEqual(row["liked_by_me"], expected, pg.nome)
