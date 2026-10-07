# Cariche residue del giorno, per singola istanza di innesco timer.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0295_innesco_timer_gruppo_target_ack"),
    ]

    operations = [
        migrations.AddField(
            model_name="innescotimer",
            name="cariche_residue",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Residuo già materializzato per cariche_giorno. Vuoto = vale ancora il massimo del giorno.",
                null=True,
                verbose_name="Cariche residue del giorno",
            ),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="cariche_giorno",
            field=models.DateField(
                blank=True,
                help_text="Giorno locale a cui si riferisce cariche_residue. Un altro giorno ricalcola dal massimo.",
                null=True,
                verbose_name="Giorno delle cariche residue",
            ),
        ),
        migrations.AlterField(
            model_name="innescotimer",
            name="max_cariche",
            field=models.PositiveIntegerField(
                default=1,
                help_text=(
                    "Attivazioni disponibili oggi per questa istanza (0 = illimitato). "
                    "Lo staff può aggiungere o togliere il residuo; a mezzanotte torna a questo valore."
                ),
                verbose_name="Cariche al giorno",
            ),
        ),
        migrations.AlterField(
            model_name="innescotimer",
            name="rigenera_cariche_ogni_secondi",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Limite aggiuntivo per singolo giocatore. Vuoto = conta solo il residuo giornaliero dell'istanza."
                ),
                null=True,
                verbose_name="Rigenera cariche ogni (secondi)",
            ),
        ),
    ]
