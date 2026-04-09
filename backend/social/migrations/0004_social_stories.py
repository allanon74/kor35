from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def _default_expires():
    return timezone.now() + timezone.timedelta(hours=24)


def _story_media_upload_to(instance, filename):
    # Evita import di modelli in migrazione.
    autore_id = getattr(instance, "autore_id", "unknown")
    return f"social/stories/{autore_id}/{filename}"


class Migration(migrations.Migration):
    dependencies = [
        ("personaggi", "0001_initial"),
        ("gestione_plot", "0001_initial"),
        ("social", "0003_social_groups"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialStory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("testo", models.TextField(blank=True, null=True)),
                ("media", models.FileField(blank=True, null=True, upload_to=_story_media_upload_to)),
                ("visibilita", models.CharField(choices=[("PUB", "Pubblico"), ("KORP", "Solo KORP")], default="PUB", max_length=4)),
                ("expires_at", models.DateTimeField(blank=True, null=True, default=_default_expires)),
                ("autore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_stories", to="personaggi.personaggio")),
                ("evento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="social_stories", to="gestione_plot.evento")),
                ("korp_visibilita", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="social_stories_riservate", to="personaggi.korp")),
            ],
            options={
                "verbose_name": "Story Social",
                "verbose_name_plural": "Stories Social",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SocialStoryHighlight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("titolo", models.CharField(max_length=80)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_story_highlights", to="personaggi.personaggio")),
            ],
            options={
                "verbose_name": "Highlight Stories",
                "verbose_name_plural": "Highlights Stories",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SocialStoryReply",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("testo", models.TextField()),
                ("autore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_story_replies", to="personaggi.personaggio")),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="social.socialstory")),
            ],
            options={
                "verbose_name": "Risposta Story",
                "verbose_name_plural": "Risposte Stories",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SocialStoryReaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("emoji", models.CharField(default="❤️", max_length=16)),
                ("autore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_story_reactions", to="personaggi.personaggio")),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reactions", to="social.socialstory")),
            ],
            options={
                "verbose_name": "Reazione Story",
                "verbose_name_plural": "Reazioni Stories",
                "ordering": ["-created_at", "-id"],
                "unique_together": {("story", "autore")},
            },
        ),
        migrations.CreateModel(
            name="SocialStoryTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("personaggio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tagged_in_social_stories", to="personaggi.personaggio")),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tags", to="social.socialstory")),
            ],
            options={
                "verbose_name": "Tag Story Social",
                "verbose_name_plural": "Tag Stories Social",
                "unique_together": {("story", "personaggio")},
            },
        ),
        migrations.CreateModel(
            name="SocialStoryView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("viewed_at", models.DateTimeField(default=timezone.now)),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="views", to="social.socialstory")),
                ("viewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_story_views", to="personaggi.personaggio")),
            ],
            options={
                "verbose_name": "Visualizzazione Story",
                "verbose_name_plural": "Visualizzazioni Stories",
                "ordering": ["-viewed_at", "-id"],
                "unique_together": {("story", "viewer")},
            },
        ),
        migrations.CreateModel(
            name="SocialStoryHighlightItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(unique=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("added_at", models.DateTimeField(default=timezone.now)),
                ("highlight", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="social.socialstoryhighlight")),
                ("story", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="in_highlights", to="social.socialstory")),
            ],
            options={
                "verbose_name": "Item Highlight",
                "verbose_name_plural": "Items Highlights",
                "ordering": ["-added_at", "-id"],
                "unique_together": {("highlight", "story")},
            },
        ),
    ]

