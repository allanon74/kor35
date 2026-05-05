from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0016_sottosistema_curve_colori"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventonave",
            name="durata_tick",
            field=models.CharField(
                default="4",
                help_text='Durata evento in tick: "N", "A-B", "-N" o "-". -N: persiste e precipita se nessun ST entro N tick. -: persiste finche non arriva ST.',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="persiste_fino_st",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="precipita_a_scadenza",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="ticks_rimanenti",
            field=models.IntegerField(
                blank=True,
                help_text="Tick rimanenti dell'evento; null = durata infinita.",
                null=True,
            ),
        ),
    ]
