from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0185_qrcode_qr_stampato"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilita",
            name="escluso_negozio_ufficiale",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non compare nell'Accademia; può essere insegnata solo da negozi alternativi/corporativi.",
                verbose_name="Escluso Accademia",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="non_vendibile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non è acquistabile/insegnabile in nessun negozio.",
                verbose_name="Non vendibile",
            ),
        ),
        migrations.AddField(
            model_name="cerimoniale",
            name="escluso_negozio_ufficiale",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non compare nell'Accademia; solo negozi speciali.",
                verbose_name="Escluso Accademia",
            ),
        ),
        migrations.AddField(
            model_name="cerimoniale",
            name="non_vendibile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non è acquistabile in nessun negozio.",
                verbose_name="Non vendibile",
            ),
        ),
        migrations.AddField(
            model_name="infusione",
            name="escluso_negozio_ufficiale",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non compare nell'Accademia; solo negozi speciali.",
                verbose_name="Escluso Accademia",
            ),
        ),
        migrations.AddField(
            model_name="infusione",
            name="non_vendibile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non è acquistabile in nessun negozio.",
                verbose_name="Non vendibile",
            ),
        ),
        migrations.AddField(
            model_name="oggettobase",
            name="escluso_negozio_ufficiale",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non compare nel negozio Accademia; può essere offerto solo da negozi alternativi/corporativi.",
                verbose_name="Escluso Accademia",
            ),
        ),
        migrations.AddField(
            model_name="oggettobase",
            name="non_vendibile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non è acquistabile in nessun negozio (né Accademia né speciali).",
                verbose_name="Non vendibile",
            ),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="escluso_negozio_ufficiale",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non compare nell'Accademia; solo negozi speciali.",
                verbose_name="Escluso Accademia",
            ),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="non_vendibile",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non è acquistabile in nessun negozio.",
                verbose_name="Non vendibile",
            ),
        ),
        migrations.AlterField(
            model_name="oggettobase",
            name="in_vendita",
            field=models.BooleanField(default=True, verbose_name="Visibile in Accademia"),
        ),
    ]
