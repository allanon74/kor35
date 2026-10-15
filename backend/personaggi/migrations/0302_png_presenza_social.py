from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0301_sondaggio_premi"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggio",
            name="png_tag_instafame",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Solo per personaggi non giocanti. Se disattivo, il PnG non compare "
                    "nei suggerimenti @ e non viene citato. I PG restano sempre taggabili."
                ),
                verbose_name="PnG taggabile su InstaFame",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="png_chiamabile",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Solo per PnG. Se disattivo, gli altri non possono avviare una chiamata "
                    "vocale verso questo personaggio. I PG sono sempre chiamabili."
                ),
                verbose_name="PnG chiamabile",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="png_destinatario_messaggi",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Solo per PnG. Se disattivo, non compare nella ricerca destinatari. "
                    "Rispondere a un messaggio già inviato dal PnG resta possibile. "
                    "I PG sono sempre destinatari."
                ),
                verbose_name="PnG destinatario messaggi",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="png_pubblica_instafame",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Solo per PnG. Se disattivo, non può pubblicare post, storie o post "
                    "nei gruppi. Commenti e like restano disponibili. I PG possono sempre pubblicare."
                ),
                verbose_name="PnG può postare su InstaFame",
            ),
        ),
    ]
