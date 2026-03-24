# Aura innata è un Punteggio (Aura) AIN, non un campo su TipologiaPersonaggio

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0117_tipologiapersonaggio_aura_innata'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tipologiapersonaggio',
            name='aura_innata',
        ),
    ]
