# PC/crediti evento + tracciamento premio presenza

import uuid

import django.core.validators
import django.db.models.deletion
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


def forwards_fix_pc_zero(apps, schema_editor):
    Evento = apps.get_model("gestione_plot", "Evento")
    Evento.objects.filter(pc_guadagnati=0).update(pc_guadagnati=1)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gestione_plot", "0027_iscrizioni_paypal_evento"),
        ("personaggi", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="crediti_guadagnati",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1000.00"),
                help_text="Crediti assegnati una sola volta a ogni PG iscritto al primo accesso durante i giorni d'evento.",
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Crediti guadagnati",
            ),
        ),
        migrations.AlterField(
            model_name="evento",
            name="pc_guadagnati",
            field=models.PositiveIntegerField(
                default=1,
                help_text="PC assegnati una sola volta a ogni PG iscritto al primo accesso durante i giorni d'evento.",
                verbose_name="PC guadagnati",
            ),
        ),
        migrations.RunPython(forwards_fix_pc_zero, migrations.RunPython.noop),
        migrations.CreateModel(
            name="EventoPremioPersonaggio",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="premi_presenza",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="premi_evento_presenza",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Premio presenza evento (PG)",
                "verbose_name_plural": "Premi presenza evento",
            },
        ),
        migrations.AddConstraint(
            model_name="eventopremiopersonaggio",
            constraint=models.UniqueConstraint(
                fields=("evento", "personaggio"),
                name="uq_evento_premio_presenza_pg",
            ),
        ),
    ]
