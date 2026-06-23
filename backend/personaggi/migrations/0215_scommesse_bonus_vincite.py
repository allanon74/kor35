from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0214_regolatransazionecategoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='personaggio',
            name='bonus_scommesse',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='CR vincolati alle scommesse: non spendibili altrove, solo per nuove puntate.',
                max_digits=12,
                verbose_name='Bonus scommesse',
            ),
        ),
        migrations.AddField(
            model_name='configurazionescommesse',
            name='max_ritiro_vincita_calendario',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('500.00'),
                help_text='Massimo CR ritirabili in contanti per calendario/evento.',
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name='configurazionescommesse',
            name='soglia_vincita_rilevante',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('500.00'),
                help_text="Oltre questa soglia, l'eccedenza va in bonus scommesse (non ritirabile subito).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name='puntatascommessa',
            name='importo_bonus',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Quota puntata pagata con bonus scommesse (non prelevabile altrove).',
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name='puntatascommessa',
            name='vincita_bonus',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='CR accreditati come bonus scommesse alla riscossione.',
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='puntatascommessa',
            name='vincita_ritirata',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='CR accreditati in contanti alla riscossione.',
                max_digits=12,
                null=True,
            ),
        ),
    ]
