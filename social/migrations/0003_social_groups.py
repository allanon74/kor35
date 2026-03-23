import django.db.models.deletion
import django.utils.timezone
import social.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0114_social_core_korp_carriera_segni"),
        ("social", "0002_mentions_profiles_permalink"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=64, unique=True)),
                ("descrizione", models.TextField(blank=True, null=True)),
                ("is_hidden", models.BooleanField(default=False)),
                ("requires_approval", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "creatore",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="social_groups_created",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Gruppo Social",
                "verbose_name_plural": "Gruppi Social",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SocialGroupMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("testo", models.TextField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "autore",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_group_messages",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="social.socialgroup"
                    ),
                ),
            ],
            options={
                "verbose_name": "Messaggio Gruppo Social",
                "verbose_name_plural": "Messaggi Gruppi Social",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="SocialGroupPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("titolo", models.CharField(max_length=180)),
                ("testo", models.TextField(blank=True, null=True)),
                ("immagine", models.ImageField(blank=True, null=True, upload_to=social.models.social_post_media_upload_to)),
                ("video", models.FileField(blank=True, null=True, upload_to=social.models.social_post_media_upload_to)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "autore",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_group_posts",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="posts", to="social.socialgroup"
                    ),
                ),
            ],
            options={
                "verbose_name": "Post Gruppo Social",
                "verbose_name_plural": "Post Gruppi Social",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SocialGroupMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ruolo",
                    models.CharField(
                        choices=[("MEMBER", "Membro"), ("ADMIN", "Admin")], default="MEMBER", max_length=10
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("INVITED", "Invitato"),
                            ("REQUESTED", "Richiesta inviata"),
                            ("ACTIVE", "Attivo"),
                            ("REJECTED", "Rifiutato"),
                        ],
                        default="REQUESTED",
                        max_length=10,
                    ),
                ),
                ("joined_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="social.socialgroup",
                    ),
                ),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="social_group_invites_sent",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_group_memberships",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Membro Gruppo Social",
                "verbose_name_plural": "Membri Gruppi Social",
                "ordering": ["-created_at", "-id"],
                "unique_together": {("group", "personaggio")},
            },
        ),
    ]
