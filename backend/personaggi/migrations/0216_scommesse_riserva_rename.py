"""Rinomina bonus scommesse → riserva e allinea campi puntata."""
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0215_scommesse_bonus_vincite'),
    ]

    operations = [
        migrations.RenameField(
            model_name='personaggio',
            old_name='bonus_scommesse',
            new_name='riserva',
        ),
        migrations.RenameField(
            model_name='puntatascommessa',
            old_name='importo_bonus',
            new_name='importo_riserva',
        ),
        migrations.RenameField(
            model_name='puntatascommessa',
            old_name='vincita_bonus',
            new_name='vincita_versata_riserva',
        ),
        migrations.AlterField(
            model_name='personaggio',
            name='riserva',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='CR da vincite scommesse: spendibili solo per puntate; ritiro in contanti solo in evento attivo.',
                max_digits=12,
                verbose_name='Riserva scommesse',
            ),
        ),
        migrations.AlterField(
            model_name='puntatascommessa',
            name='importo_riserva',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Quota puntata pagata dalla riserva scommesse.',
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name='puntatascommessa',
            name='vincita_ritirata',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='CR prelevati dalla riserva e accreditati in contanti (solo in evento attivo).',
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='puntatascommessa',
            name='vincita_versata_riserva',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='CR versati in riserva alla riscossione della vincita.',
                max_digits=12,
                null=True,
            ),
        ),
    ]
