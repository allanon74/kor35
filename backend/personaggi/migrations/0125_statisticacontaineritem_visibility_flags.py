from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0124_statistica_container_dimensioni"),
    ]

    operations = [
        migrations.AddField(
            model_name="statisticacontaineritem",
            name="nascondi_se_negativa",
            field=models.BooleanField(
                default=True,
                help_text="Se attivo, non renderizza la statistica quando il valore e negativo.",
            ),
        ),
        migrations.AddField(
            model_name="statisticacontaineritem",
            name="nascondi_se_zero",
            field=models.BooleanField(
                default=True,
                help_text="Se attivo, non renderizza la statistica quando il valore e 0.",
            ),
        ),
        migrations.AddField(
            model_name="statisticacontaineritem",
            name="nascondi_se_uno",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non renderizza la statistica quando il valore e 1.",
            ),
        ),
    ]

