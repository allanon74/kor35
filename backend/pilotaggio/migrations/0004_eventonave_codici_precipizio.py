# Generated manually for codici_precipizio

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0003_pilotconsoleloginticket"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventonave",
            name="codici_precipizio",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Pattern che causano precipitazione immediata (DEFCON oltre il massimo). "
                    'Stessa sintassi dei parziali. Es. ["XX9","ZZ(8-9)"]. Valutati dopo la soluzione esatta.'
                ),
            ),
        ),
    ]
