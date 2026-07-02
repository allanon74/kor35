from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0230_keyword_effect_script"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionescommesse",
            name="bonus_quota_allibratore_pct",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.10"),
                help_text="Bonus quota con codice allibratore (es. 0.10 = +10% sulla quota).",
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name="configurazionescommesse",
            name="commissione_allibratore_pct",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.08"),
                help_text="Frazione della vincita (es. 0.08 = 8%) accreditata all'allibratore se la puntata vince.",
                max_digits=5,
            ),
        ),
    ]
