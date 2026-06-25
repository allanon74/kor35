from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0218_carriera_abilita_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="abilitastatistica",
            name="valore",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                max_digits=7,
            ),
        ),
    ]
