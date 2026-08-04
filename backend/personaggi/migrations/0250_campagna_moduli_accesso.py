# Generated manually for Campagna.moduli_accesso

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0249_carriera_fattore_task_prestigio_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="campagna",
            name="moduli_accesso",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Accesso moduli campagna: mappa chiave→OFF|TEST|OPEN "
                    "(tasks, pilotaggio, carte, scommesse, social, negozi, …). "
                    "Chiavi assenti usano i default del registry; «carte» senza override "
                    "legge ConfigurazioneCarteCollezionabili."
                ),
            ),
        ),
    ]
