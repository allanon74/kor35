# Generated manually to align choices with models.py (AR=Arte, AT=Archetipo)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0106_consumabilepersonaggio_tessitura'),
    ]

    operations = [
        migrations.AlterField(
            model_name='punteggio',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('CA', 'Caratteristica'),
                    ('ST', 'Statistica'),
                    ('EL', 'Elemento'),
                    ('AU', 'Aura'),
                    ('CO', 'Condizione'),
                    ('CU', 'Culto'),
                    ('VI', 'Via'),
                    ('AR', 'Arte'),
                    ('AT', 'Archetipo'),
                ],
                max_length=2,
                verbose_name='Tipo di punteggio',
            ),
        ),
    ]

