# Usi QR, credito deposito, inventario (crediti/consumabili), pool crediti.

import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def set_usi_max_one_for_associated(apps, schema_editor):
    """Preserva il comportamento one-shot sui QR già collegati a una vista."""
    QrCode = apps.get_model("personaggi", "QrCode")
    QrCode.objects.filter(vista__isnull=False).update(usi_max=1)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0296_innesco_timer_cariche_giorno"),
    ]

    operations = [
        migrations.AddField(
            model_name="qrcode",
            name="usi_max",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Quante volte il contenuto può essere preso/appreso (o accreditato) "
                    "prima che il QR si svuoti. Vuoto = illimitato."
                ),
                null=True,
                verbose_name="Usi massimi",
            ),
        ),
        migrations.AddField(
            model_name="qrcode",
            name="usi_consumati",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Contatore acquisizioni/prelievi già effettuati su questo QR.",
                verbose_name="Usi consumati",
            ),
        ),
        migrations.AddField(
            model_name="inventario",
            name="crediti_deposito",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="Crediti (conto deposito) prelevabili da chi scansiona questo inventario QR.",
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                verbose_name="Crediti deposito contenuti",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="crediti_importo_min",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Solo crediti: importo minimo (o fisso se = max).",
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="crediti_importo_max",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Solo crediti: importo massimo.",
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AlterField(
            model_name="randomqrpooleffect",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("testo", "Testo"),
                    ("nodo", "Nodo"),
                    ("trappola", "Trappola"),
                    ("serie", "Serie"),
                    ("manifesto", "Manifesto"),
                    ("oggetto_base", "Oggetto (listino)"),
                    ("da_infusione", "Materia/Mod (da Infusione)"),
                    ("tessitura", "Tessitura"),
                    ("infusione", "Infusione (ricetta)"),
                    ("cerimoniale", "Cerimoniale"),
                    ("attivata", "Attivata"),
                    ("negozio_mercante", "Negozio mercante"),
                    ("crediti", "Crediti deposito"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="ConsumabileInInventario",
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
                ("nome", models.CharField(max_length=200)),
                ("descrizione", models.TextField(blank=True, default="")),
                (
                    "formula",
                    models.TextField(
                        blank=True,
                        default="{rango|:RANGO}{molt|:MOLT}{formula_prefix}{formula_target}{formula_source}{danni_mischia}{formula_cura}{formula_status}",
                        null=True,
                    ),
                ),
                ("utilizzi_rimanenti", models.PositiveIntegerField(default=1)),
                ("data_scadenza", models.DateField(blank=True, null=True)),
                (
                    "inventario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consumabili_contenuti",
                        to="personaggi.inventario",
                    ),
                ),
                (
                    "tessitura",
                    models.ForeignKey(
                        blank=True,
                        help_text="Tessitura di origine (Ad hoc / Alchimia), se nota.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="consumabili_in_inventari",
                        to="personaggi.tessitura",
                    ),
                ),
            ],
            options={
                "verbose_name": "Consumabile in inventario QR",
                "verbose_name_plural": "Consumabili in inventario QR",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="QrCreditoDeposito",
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
                    "importo_min",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Importo minimo (o fisso se uguale a importo_max).",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "importo_max",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Importo massimo (random uniforme incluso se diverso da min).",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "qr_code",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="configurazione_credito",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "QR Credito deposito",
                "verbose_name_plural": "QR Credito deposito",
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(set_usi_max_one_for_associated, noop_reverse),
    ]
