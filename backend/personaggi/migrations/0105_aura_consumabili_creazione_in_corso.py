# Generated manually: campi consumabili su Aura + CreazioneConsumabileInCorso

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0104_effetti_casuali_consumabili'),
    ]

    operations = [
        migrations.AddField(
            model_name='punteggio',
            name='stat_costo_consumabili',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aure_stat_costo_consumabili', to='personaggi.statistica', verbose_name='Stat. Costo Creazione Consumabili'),
        ),
        migrations.AddField(
            model_name='punteggio',
            name='stat_numero_consumabili',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aure_stat_numero_consumabili', to='personaggi.statistica', verbose_name='Stat. Numero Consumabili'),
        ),
        migrations.AddField(
            model_name='punteggio',
            name='stat_tempo_creazione_consumabili',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aure_stat_tempo_creazione_consumabili', to='personaggi.statistica', verbose_name='Stat. Tempo Creazione Consumabili (sec)'),
        ),
        migrations.AddField(
            model_name='punteggio',
            name='stat_durata_consumabili',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aure_stat_durata_consumabili', to='personaggi.statistica', verbose_name='Stat. Durata Consumabili (giorni)'),
        ),
        migrations.CreateModel(
            name='CreazioneConsumabileInCorso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_fine_creazione', models.DateTimeField()),
                ('completata', models.BooleanField(default=False)),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='creazioni_consumabili_in_corso', to='personaggi.personaggio')),
                ('tessitura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='creazioni_consumabili_in_corso', to='personaggi.tessitura')),
            ],
            options={
                'verbose_name': 'Creazione Consumabile In Corso',
                'verbose_name_plural': 'Creazioni Consumabili In Corso',
                'ordering': ['data_fine_creazione'],
            },
        ),
    ]
