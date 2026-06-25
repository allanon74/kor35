from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0220_stat_modificatore_valore_decimal"),
    ]

    operations = [
        migrations.AddField(
            model_name="statisticacontaineritem",
            name="nascondi_se_due",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, non renderizza la statistica quando il valore e 2.",
            ),
        ),
    ]
