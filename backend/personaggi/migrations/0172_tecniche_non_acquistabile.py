from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0171_tessitura_runtime_effects"),
    ]

    operations = [
        migrations.AddField(
            model_name="cerimoniale",
            name="non_acquistabile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la tecnica non compare tra quelle acquistabili dalle tab giocatore.",
                verbose_name="Non acquistabile",
            ),
        ),
        migrations.AddField(
            model_name="infusione",
            name="non_acquistabile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la tecnica non compare tra quelle acquistabili dalle tab giocatore.",
                verbose_name="Non acquistabile",
            ),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="non_acquistabile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la tecnica non compare tra quelle acquistabili dalle tab giocatore.",
                verbose_name="Non acquistabile",
            ),
        ),
    ]
