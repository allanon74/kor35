# Generated manually: Trappola/SerieQr da A_vista (AutoField) → UUID PK + OneToOne QrCode

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0255_qr_random_pool_trappola_serie"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="statotrappolapersonaggio",
            name="trappola",
        ),
        migrations.DeleteModel(
            name="SerieQr",
        ),
        migrations.DeleteModel(
            name="Trappola",
        ),
        migrations.CreateModel(
            name="Trappola",
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
                ("nome", models.CharField(max_length=100)),
                ("testo", models.TextField(blank=True, default="")),
                (
                    "durata_secondi",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Vuoto = solo messaggio descrittivo, senza countdown.",
                        null=True,
                        verbose_name="Durata timer (secondi)",
                    ),
                ),
                (
                    "qr_code",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="configurazione_trappola",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trappola QR",
                "verbose_name_plural": "Trappole QR",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SerieQr",
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
                ("nome", models.CharField(max_length=100)),
                ("testo", models.TextField(blank=True, default="")),
                (
                    "serie",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="qr_standalone",
                        to="personaggi.seriecollezione",
                    ),
                ),
                (
                    "qr_code",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="configurazione_serie",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "QR Serie",
                "verbose_name_plural": "QR Serie",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="statotrappolapersonaggio",
            name="trappola",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stati_personaggio",
                to="personaggi.trappola",
            ),
        ),
    ]
