from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from django.contrib.auth import get_user_model

from personaggi.models import Campagna, Personaggio
from social.models import SocialPost, extract_hashtags
from social.views import SocialPostViewSet


class HashtagExtractionTests(TestCase):
    def test_hyphenated_hashtag(self):
        self.assertEqual(extract_hashtags("Guardate #A-phone oggi!"), ["a-phone"])

    def test_underscore_and_hyphen(self):
        self.assertEqual(extract_hashtags("Mix #foo_bar e #A-phone-2"), ["a-phone-2", "foo_bar"])

    def test_ignores_invalid(self):
        self.assertEqual(extract_hashtags("#-bad #x"), [])


class HashtagFeedFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="hash_user", password="x")
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.pg = Personaggio.objects.create(nome="PG Hash", proprietario=cls.user, campagna=cls.campagna)
        cls.author = Personaggio.objects.create(nome="Autore", campagna=cls.campagna)
        cls.post = SocialPost.objects.create(
            autore=cls.author,
            titolo="Titolo",
            testo="Evento #A-phone live",
            visibilita="PUB",
        )

    def test_filter_by_hyphenated_hashtag(self):
        factory = APIRequestFactory()
        view = SocialPostViewSet.as_view({"get": "list"})
        request = factory.get("/api/social/posts/", {"personaggio_id": self.pg.id, "hashtag": "A-phone"})
        request.META["HTTP_X_CAMPAGNA"] = "kor35"
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data.get("results", response.data)}
        self.assertIn(self.post.id, ids)
