from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0026_sessione_ultimo_tick_motore_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoattivosessione",
            name="prossima_valutazione_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    "Primo e successivi check CA/ST/SP dell'evento: non prima di questo istante "
                    "(intervallo = tempo_risoluzione_secondi del DEFCON corrente)."
                ),
            ),
        ),
    ]
