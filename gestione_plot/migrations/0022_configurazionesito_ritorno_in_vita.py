from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0021_evento_sync_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionesito",
            name="abilita_ritorno_in_vita",
            field=models.BooleanField(
                default=True,
                help_text="Se disattivo, al termine del coma non parte il countdown OFFGAME di ritorno in vita.",
            ),
        ),
        migrations.AddField(
            model_name="configurazionesito",
            name="parametro_ritorno_in_vita",
            field=models.CharField(
                default="TRI",
                help_text="Valore del countdown OFFGAME: numero di secondi (es. 300) oppure sigla caratteristica (es. TRI).",
                max_length=32,
            ),
        ),
    ]
