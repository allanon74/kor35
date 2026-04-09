import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("gestione_plot", "0021_evento_sync_fields"),
        ("personaggi", "0114_social_core_korp_carriera_segni"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("titolo", models.CharField(max_length=180)),
                ("testo", models.TextField(blank=True, null=True)),
                ("immagine", models.ImageField(blank=True, null=True, upload_to="social/posts")),
                ("video", models.FileField(blank=True, null=True, upload_to="social/posts")),
                ("visibilita", models.CharField(choices=[("PUB", "Pubblico"), ("KORP", "Solo KORP")], default="PUB", max_length=4)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("autore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_posts", to="personaggi.personaggio")),
                ("evento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="social_posts", to="gestione_plot.evento")),
                ("korp_visibilita", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="social_posts_riservati", to="personaggi.korp")),
            ],
            options={
                "verbose_name": "Post Social",
                "verbose_name_plural": "Post Social",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SocialProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("foto_principale", models.ImageField(blank=True, null=True, upload_to="social/profiles")),
                ("regione", models.CharField(blank=True, max_length=120, null=True)),
                ("prefettura", models.CharField(blank=True, max_length=120, null=True)),
                ("descrizione", models.TextField(blank=True, null=True)),
                ("professioni", models.TextField(blank=True, null=True)),
                ("era_provenienza", models.CharField(blank=True, max_length=120, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("personaggio", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="social_profile", to="personaggi.personaggio")),
            ],
            options={
                "verbose_name": "Profilo Social",
                "verbose_name_plural": "Profili Social",
            },
        ),
        migrations.CreateModel(
            name="SocialLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("autore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_likes", to="personaggi.personaggio")),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="social.socialpost")),
            ],
            options={
                "verbose_name": "Like Social",
                "verbose_name_plural": "Like Social",
                "ordering": ["-created_at", "-id"],
                "unique_together": {("post", "autore")},
            },
        ),
        migrations.CreateModel(
            name="SocialComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("testo", models.TextField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("autore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="social_comments", to="personaggi.personaggio")),
                ("evento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="social_comments", to="gestione_plot.evento")),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="social.socialpost")),
            ],
            options={
                "verbose_name": "Commento Social",
                "verbose_name_plural": "Commenti Social",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
