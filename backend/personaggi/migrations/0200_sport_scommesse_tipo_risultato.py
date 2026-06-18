from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0199_merge_20260618_1034'),
    ]

    operations = [
        migrations.AddField(
            model_name='sportscommesse',
            name='tipo_risultato',
            field=models.CharField(
                choices=[
                    ('calcio', 'Calcio'),
                    ('rugby', 'Rugby'),
                    ('basket', 'Basket'),
                    ('football_usa', 'Football americano'),
                    ('baseball', 'Baseball'),
                    ('tennis', 'Tennis'),
                    ('volley', 'Pallavolo'),
                    ('hockey', 'Hockey su ghiaccio'),
                ],
                default='calcio',
                help_text='Formato punteggio e regole pareggio per questo sport.',
                max_length=20,
            ),
        ),
    ]
