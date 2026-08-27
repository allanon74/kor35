# Generated manually: preferenze notifiche per-utente (webpush / telegram / email)

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import personaggi.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0260_campagnaruolo_helper"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificaPreferenze",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "canali",
                    models.JSONField(
                        blank=True, default=personaggi.models._default_notifica_canali
                    ),
                ),
                (
                    "telegram_chat_id",
                    models.CharField(blank=True, db_index=True, default="", max_length=32),
                ),
                (
                    "telegram_username",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "telegram_link_code",
                    models.CharField(blank=True, db_index=True, default="", max_length=16),
                ),
                ("telegram_link_expires", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifica_preferenze",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Preferenze notifiche",
                "verbose_name_plural": "Preferenze notifiche",
            },
        ),
    ]
