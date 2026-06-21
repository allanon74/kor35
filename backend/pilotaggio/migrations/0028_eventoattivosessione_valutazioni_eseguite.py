from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0027_eventoattivosessione_prossima_valutazione_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoattivosessione",
            name="valutazioni_eseguite",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=(
                    "Numero di tick evento gia' valutati. La CA e la scadenza critica precipizio "
                    "non si applicano al primo check (tempo di reazione pilota)."
                ),
            ),
        ),
    ]
