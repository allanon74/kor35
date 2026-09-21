from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0053_staff_compito_automatico"),
    ]

    operations = [
        migrations.AddField(
            model_name="missioneevento",
            name="attiva",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text=(
                    "Default: attiva all'inizio dell'evento. Se disattiva, la task è "
                    "invisibile ai personaggi e non può essere segnata come risolta."
                ),
                verbose_name="Attiva per l'evento",
            ),
        ),
    ]
