"""Nickname InstaFame: emoji e limite per grafemi."""

from django.test import TestCase
from rest_framework import serializers

from social.models import SocialProfile
from social.nickname_validation import (
    NICKNAME_MAX_GRAPHEMES,
    clean_nickname_value,
    grapheme_len,
)
from social.serializers import SocialProfileSerializer


class NicknameValidationTests(TestCase):
    def test_grapheme_len_counts_emoji_as_one(self):
        self.assertEqual(grapheme_len("🦚"), 1)
        self.assertEqual(grapheme_len("Test 🦚"), 6)
        self.assertEqual(grapheme_len("❤️"), 1)

    def test_clean_accepts_emoji_nickname(self):
        self.assertEqual(clean_nickname_value("🦚 Re del bosco"), "🦚 Re del bosco")

    def test_clean_rejects_too_many_graphemes(self):
        too_long = "a" * (NICKNAME_MAX_GRAPHEMES + 1)
        with self.assertRaises(serializers.ValidationError):
            clean_nickname_value(too_long)

    def test_serializer_saves_emoji_nickname(self):
        profile = SocialProfile.objects.select_related("personaggio").first()
        if not profile:
            self.skipTest("Nessun SocialProfile nel DB di test")
        serializer = SocialProfileSerializer(profile, data={"nickname": "🦚"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.nickname, "🦚")
