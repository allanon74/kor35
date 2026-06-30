import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0228_keyword_carte"),
    ]

    operations = [
        migrations.AddField(
            model_name="duellocarte",
            name="avvio_tipo",
            field=models.CharField(
                blank=True,
                choices=[("TST", "Lista (testing)"), ("LOB", "Lobby QR (open)")],
                db_index=True,
                default="",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="duellocarte",
            name="modalita_partita",
            field=models.CharField(
                choices=[("LIV", "Turni live"), ("MAN", "Manuale")],
                db_index=True,
                default="LIV",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="duellocarte",
            name="posta_cr",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="duellocarte",
            name="qr_code",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duello_lobby",
                to="personaggi.qrcode",
            ),
        ),
        migrations.AddField(
            model_name="duellocarte",
            name="stato_prematch",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="duellocarte",
            name="stato",
            field=models.CharField(
                choices=[
                    ("LOB", "Lobby aperta"),
                    ("PRE", "Pre-partita"),
                    ("ATT", "In attesa"),
                    ("COR", "In corso"),
                    ("FIN", "Terminato"),
                    ("ANN", "Annullato"),
                ],
                db_index=True,
                default="ATT",
                max_length=3,
            ),
        ),
        migrations.CreateModel(
            name="ScontroCartePortale",
            fields=[
                (
                    "a_vista_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.a_vista",
                    ),
                ),
                (
                    "duello",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portale_avista",
                        to="personaggi.duellocarte",
                    ),
                ),
            ],
            options={
                "verbose_name": "Portale scontro carte",
                "verbose_name_plural": "Portali scontri carte",
            },
            bases=("personaggi.a_vista",),
        ),
    ]
