from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0054_missioneevento_attiva"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventopremiopersonaggio",
            name="avvio_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "started_at dell'evento a cui si riferisce questo accredito. "
                    "Se è diverso dall'avvio corrente, PC/crediti/prestigio vanno riassegnati."
                ),
                null=True,
                verbose_name="Avvio coperto",
            ),
        ),
    ]
