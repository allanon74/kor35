# Negozio di prestiti: flag sul negozio + tracking prestiti attivi

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0285_negoziomercantevoce_serie"),
    ]

    operations = [
        migrations.AddField(
            model_name="negoziomercante",
            name="negozio_prestiti",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "Se attivo, gli oggetti del catalogo si prendono solo in prestito "
                    "(restituzione a fine evento). Il prezzo della voce è il costo di "
                    "noleggio (0 ammesso)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="negoziomercante",
            name="limite_prestiti_per_personaggio",
            field=models.PositiveIntegerField(
                default=1,
                help_text=(
                    "Quanti oggetti un personaggio può tenere in prestito contemporaneamente "
                    "da questo negozio (solo se negozio_prestiti è attivo). Default: 1."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="negoziomercantevoce",
            name="prezzo_crediti",
            field=models.PositiveIntegerField(
                help_text=(
                    "Prezzo in crediti (acquisto) oppure costo di noleggio se il negozio "
                    "è in modalità prestiti (0 = prestito gratuito)."
                ),
            ),
        ),
        migrations.CreateModel(
            name="NegozioMercantePrestito",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
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
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "costo_noleggio",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Crediti pagati come noleggio al momento del prestito (0 = gratuito).",
                    ),
                ),
                (
                    "stato",
                    models.CharField(
                        choices=[("ATT", "In prestito"), ("RES", "Restituito")],
                        db_index=True,
                        default="ATT",
                        max_length=3,
                    ),
                ),
                ("prestato_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("restituito_at", models.DateTimeField(blank=True, null=True)),
                ("nota_restituzione", models.CharField(blank=True, default="", max_length=255)),
                (
                    "negozio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prestiti",
                        to="personaggi.negoziomercante",
                    ),
                ),
                (
                    "oggetto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prestiti_negozio_mercante",
                        to="personaggi.oggetto",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prestiti_negozio_mercante",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "stock",
                    models.ForeignKey(
                        blank=True,
                        help_text="Riga stock di origine (se prestito da usato/magazzino).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="prestiti",
                        to="personaggi.negoziomercantestock",
                    ),
                ),
                (
                    "voce",
                    models.ForeignKey(
                        blank=True,
                        help_text="Voce catalogo di origine (se prestito da listino).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="prestiti",
                        to="personaggi.negoziomercantevoce",
                    ),
                ),
            ],
            options={
                "verbose_name": "Prestito negozio mercante",
                "verbose_name_plural": "Prestiti negozi mercante",
                "ordering": ["-prestato_at"],
            },
        ),
        migrations.AddIndex(
            model_name="negoziomercanteprestito",
            index=models.Index(
                fields=["negozio", "personaggio", "stato"],
                name="personaggi__negozio_a8f1c2_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="negoziomercanteprestito",
            index=models.Index(
                fields=["oggetto", "stato"],
                name="personaggi__oggetto_b3d4e5_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="negoziomercanteprestito",
            constraint=models.UniqueConstraint(
                condition=models.Q(("stato", "ATT")),
                fields=("oggetto",),
                name="uniq_oggetto_prestito_attivo",
            ),
        ),
    ]
