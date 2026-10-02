"""Prestigio come punteggio del personaggio.

- ``Personaggio.peso_influencer`` → ``Personaggio.prestigio`` (default 0).
- Rimosso il bonus Prestigio delle cariche: niente più Prestigio da cariche/carriere/KORP.
- Fattori task KORP separati: Crediti e Prestigio.
"""

from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0289_pool_mercante_pesi_diff_archivio"),
    ]

    operations = [
        migrations.RenameField(
            model_name="personaggio",
            old_name="peso_influencer",
            new_name="prestigio",
        ),
        migrations.AlterField(
            model_name="personaggio",
            name="prestigio",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Punteggio di Prestigio del personaggio: peso social su post, commenti e like. "
                    "Assegnato dallo staff, dalla partecipazione agli eventi e dalle task. "
                    "Cariche, carriere e KORP non lo modificano."
                ),
                verbose_name="Prestigio",
            ),
        ),
        migrations.RemoveField(
            model_name="carica",
            name="bonus_peso_influencer",
        ),
        migrations.RenameField(
            model_name="carriera",
            old_name="fattore_task",
            new_name="fattore_task_crediti",
        ),
        migrations.AlterField(
            model_name="carriera",
            name="fattore_task_crediti",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1.00"),
                help_text=(
                    "Moltiplicatore dei Crediti delle task di questa KORP "
                    "per i membri attivi (es. 2.00 = doppi). Rilevante se tipo = korp."
                ),
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                verbose_name="Fattore task Crediti (KORP)",
            ),
        ),
        migrations.AddField(
            model_name="carriera",
            name="fattore_task_prestigio",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("1.00"),
                help_text=(
                    "Moltiplicatore del Prestigio delle task di questa KORP per i membri attivi, "
                    "indipendente dal fattore Crediti (0.00 = la KORP non dà Prestigio). "
                    "Rilevante se tipo = korp."
                ),
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                verbose_name="Fattore task Prestigio (KORP)",
            ),
        ),
    ]
