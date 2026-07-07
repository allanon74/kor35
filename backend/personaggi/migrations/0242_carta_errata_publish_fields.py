from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0241_carta_errata_and_layout"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartaerrata",
            name="pubblicata",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Se true, mostrata ai giocatori nel riepilogo storico errata.",
            ),
        ),
        migrations.AddField(
            model_name="cartaerrata",
            name="pubblicata_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp pubblicazione errata verso i giocatori.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="cartaerrata",
            name="pubblicata_nota",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Nota di rilascio mostrata nell'interfaccia personaggi.",
            ),
        ),
        migrations.AddField(
            model_name="cartaerrata",
            name="versione",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Codice versione errata (es. 2026.07-A).",
                max_length=32,
            ),
        ),
    ]
