# Mercato scambio carte tra personaggi (MVP modello + admin)

import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import kor35.syncing


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0235_carte_reliquiario_combo_stat"),
    ]

    operations = [
        migrations.CreateModel(
            name="OffertaScambioCarte",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "richiesta_crediti",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Crediti richiesti in aggiunta o al posto di una carta.",
                        max_digits=10,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("messaggio", models.TextField(blank=True, default="")),
                (
                    "stato",
                    models.CharField(
                        choices=[
                            ("APR", "Aperta"),
                            ("ACC", "Accettata"),
                            ("ANN", "Annullata"),
                            ("SCD", "Scaduta"),
                        ],
                        db_index=True,
                        default="APR",
                        max_length=3,
                    ),
                ),
                ("accettata_at", models.DateTimeField(blank=True, null=True)),
                (
                    "accettante",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="offerte_scambio_accettate",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="offerte_scambio_carte",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "carta_offerta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offerte_scambio",
                        to="personaggi.cartaposseduta",
                    ),
                ),
                (
                    "offerente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="offerte_scambio_carte_inviate",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "richiesta_carta",
                    models.ForeignKey(
                        blank=True,
                        help_text="Carta catalogo desiderata (qualsiasi copia posseduta dall'accettante).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="offerte_scambio_richieste",
                        to="personaggi.cartacollezionabile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Offerta scambio carte",
                "verbose_name_plural": "Offerte scambio carte",
                "ordering": ["-updated_at"],
            },
            bases=(kor35.syncing.SyncableModel, models.Model),
        ),
    ]
