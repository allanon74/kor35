# Generated manually: Caratteristica 2 e 3 opzionali su Abilita
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0108_mattone_mostra_classi_arma'),
    ]

    operations = [
        migrations.AddField(
            model_name='abilita',
            name='caratteristica_2',
            field=models.ForeignKey(blank=True, limit_choices_to={'tipo__in': ['CA', 'CO']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='abilita_caratteristica_2', to='personaggi.punteggio', verbose_name='Caratteristica 2'),
        ),
        migrations.AddField(
            model_name='abilita',
            name='caratteristica_3',
            field=models.ForeignKey(blank=True, limit_choices_to={'tipo__in': ['CA', 'CO']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='abilita_caratteristica_3', to='personaggi.punteggio', verbose_name='Caratteristica 3'),
        ),
    ]
