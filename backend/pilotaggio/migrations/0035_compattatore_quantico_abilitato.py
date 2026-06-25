from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0034_compattatore_stato_nave"),
    ]

    operations = [
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="compattatore_quantico_abilitato",
            field=models.BooleanField(
                default=False,
                help_text="Abilita operazione Compattatore Quantico in console (default disattivo fino a evento).",
            ),
        ),
    ]
