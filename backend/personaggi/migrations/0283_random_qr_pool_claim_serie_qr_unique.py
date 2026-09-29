# Anti-farm: claim pool QR + vincolo unico QR→assegnazione serie

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0282_statistica_rdm"),
    ]

    operations = [
        migrations.CreateModel(
            name="RandomQrPoolClaim",
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
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="random_pool_claims",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="claims",
                        to="personaggi.randomqrpool",
                    ),
                ),
                (
                    "qr_code",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="random_pool_claims",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "Claim pool QR",
                "verbose_name_plural": "Claim pool QR",
            },
        ),
        migrations.AddIndex(
            model_name="randomqrpoolclaim",
            index=models.Index(
                fields=["personaggio", "qr_code"],
                name="personaggi__persona_043267_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="randomqrpoolclaim",
            constraint=models.UniqueConstraint(
                fields=("personaggio", "qr_code"),
                name="uq_random_qr_pool_claim_pg_qr",
            ),
        ),
        migrations.AddConstraint(
            model_name="serieassegnazione",
            constraint=models.UniqueConstraint(
                condition=models.Q(("qr_code__isnull", False)),
                fields=("qr_code",),
                name="uq_serie_assegnazione_qr_code",
            ),
        ),
    ]
