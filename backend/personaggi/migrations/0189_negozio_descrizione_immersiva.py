from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0188_negozio_mercante_portale_avista"),
    ]

    operations = [
        migrations.AddField(
            model_name="negoziomercante",
            name="descrizione_immersiva",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Testo HTML per i giocatori (atmosfera del negozio alla scansione QR).",
            ),
        ),
        migrations.AlterField(
            model_name="negoziomercante",
            name="descrizione",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Note interne / breve (non mostrata ai PG se è valorizzata la descrizione in-game).",
            ),
        ),
    ]
