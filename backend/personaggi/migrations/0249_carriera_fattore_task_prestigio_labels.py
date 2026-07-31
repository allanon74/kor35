from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0248_espansione_sigla"),
    ]

    operations = [
        migrations.AddField(
            model_name="carriera",
            name="fattore_task",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1.00"),
                help_text=(
                    "Moltiplicatore ricompense (Crediti/Prestigio) delle task di questa KORP "
                    "per i membri attivi (es. 2.00 = doppie). Solo rilevante se tipo = korp."
                ),
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Fattore task (KORP)",
            ),
        ),
        migrations.AlterField(
            model_name="carica",
            name="bonus_peso_influencer",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Bonus al Prestigio (ex peso social/influencer) per i membri con questa carica.",
                verbose_name="Bonus Prestigio",
            ),
        ),
        migrations.AlterField(
            model_name="personaggio",
            name="peso_influencer",
            field=models.PositiveIntegerField(
                default=1,
                help_text=(
                    "Prestigio del personaggio (conosciuto/influenza social). "
                    "Usato per like InstaFame (1 = minimo). Le cariche attive e le task possono aumentarlo."
                ),
                verbose_name="Prestigio",
            ),
        ),
    ]
