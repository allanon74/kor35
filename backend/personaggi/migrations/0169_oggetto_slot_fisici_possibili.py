from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0168_abilitaformularule_from_mattone_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="oggetto",
            name="slot_fisici_possibili",
            field=models.CharField(
                blank=True,
                help_text="Solo FIS: lista slot equipaggiabili separati da virgola (es. armor,vest).",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="oggettobase",
            name="slot_fisici_possibili",
            field=models.CharField(
                blank=True,
                help_text="Solo FIS: lista slot equipaggiabili separati da virgola (es. armor,vest).",
                max_length=200,
                null=True,
            ),
        ),
    ]
