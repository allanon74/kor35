from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0219_abilitastatistica_valore_decimal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mattonestatistica",
            name="valore",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                max_digits=7,
            ),
        ),
        migrations.AlterField(
            model_name="infusionestatistica",
            name="valore",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                max_digits=7,
            ),
        ),
        migrations.AlterField(
            model_name="oggettostatistica",
            name="valore",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                max_digits=7,
            ),
        ),
        migrations.AlterField(
            model_name="oggettobasemodificatore",
            name="valore",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                max_digits=7,
            ),
        ),
    ]
