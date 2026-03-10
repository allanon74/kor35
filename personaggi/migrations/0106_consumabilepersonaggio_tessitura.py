# Generated manually: FK tessitura su ConsumabilePersonaggio per formattazione

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0105_aura_consumabili_creazione_in_corso'),
    ]

    operations = [
        migrations.AddField(
            model_name='consumabilepersonaggio',
            name='tessitura',
            field=models.ForeignKey(
                blank=True,
                help_text='Se il consumabile è stato creato da una tessitura (Alchimia), per formattazione corretta con statistiche.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='consumabili_da_tessitura',
                to='personaggi.tessitura'
            ),
        ),
    ]
