from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0047_missione_tasks"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="prestigio_base_inizio_evento",
            field=models.IntegerField(
                default=0,
                help_text=(
                    "Variazione Prestigio assegnata a ogni PG partecipante all'avvio ufficiale evento. "
                    "Può essere negativa (malus)."
                ),
                verbose_name="Prestigio base inizio evento",
            ),
        ),
    ]
