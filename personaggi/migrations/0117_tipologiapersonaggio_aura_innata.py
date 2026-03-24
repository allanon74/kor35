# Generated manually for KOR35 — Aura innata (razza) sulla tipologia personaggio

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0116_usersocialpreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipologiapersonaggio',
            name='aura_innata',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='0: in scheda solo archetipo Umano; 1: anche altri archetipi; 2: anche forme.',
                verbose_name='Aura innata (razza)',
            ),
        ),
    ]
