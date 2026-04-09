# Generated manually for effetti casuali e consumabili

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0103_add_tessitura_favorite'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipologiaEffetto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('tipo', models.CharField(choices=[('OGG', 'Oggetto'), ('TES', 'Tessitura')], max_length=3)),
                ('aura_collegata', models.ForeignKey(blank=True, limit_choices_to={'tipo': 'AU'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tipologie_effetto_aura', to='personaggi.punteggio', verbose_name='Aura collegata (solo per tipo Oggetto)')),
            ],
            options={
                'verbose_name': 'Tipologia Effetto Casuale',
                'verbose_name_plural': 'Tipologie Effetto Casuale',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='EffettoCasuale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('descrizione', models.TextField(help_text='Usa {parametro} per le statistiche. Inclusi: {aura} (aura tipo), {elemento} (elemento)')),
                ('formula', models.TextField(blank=True, help_text='Stesso formato della descrizione. Obbligatorio se tipologia=Tessitura.', null=True)),
                ('elemento_principale', models.ForeignKey(blank=True, limit_choices_to=Q(aura__nome__icontains='magica') | Q(aura__sigla__iexact='mag'), null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='effetti_casuali_elemento', to='personaggi.mattone', verbose_name='Elemento principale (Mattoni con aura Magica)')),
                ('tipologia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='effetti', to='personaggi.tipologiaeffetto')),
            ],
            options={
                'verbose_name': 'Effetto Casuale',
                'verbose_name_plural': 'Effetti Casuali',
                'ordering': ['tipologia', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='ConsumabilePersonaggio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=200)),
                ('descrizione', models.TextField()),
                ('formula', models.TextField(blank=True, null=True)),
                ('utilizzi_rimanenti', models.PositiveIntegerField(default=1)),
                ('data_scadenza', models.DateField()),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('effetto_casuale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consumabili_personaggio', to='personaggi.effettocasuale')),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumabili', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Consumabile Personaggio',
                'verbose_name_plural': 'Consumabili Personaggio',
                'ordering': ['-data_creazione'],
            },
        ),
    ]
