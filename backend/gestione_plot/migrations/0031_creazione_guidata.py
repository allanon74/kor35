# Generated manually for creazione guidata wizard

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0176_synctombstone'),
        ('gestione_plot', '0030_configurazionesito_maintenance_mode'),
    ]

    operations = [
        migrations.CreateModel(
            name='CreazioneGuidataFlusso',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=80, unique=True)),
                ('titolo', models.CharField(max_length=200)),
                ('attivo', models.BooleanField(default=False)),
                ('campagna', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='flussi_creazione_guidata', to='personaggi.campagna')),
            ],
            options={
                'verbose_name': 'Flusso creazione guidata',
                'verbose_name_plural': 'Flussi creazione guidata',
                'ordering': ['titolo'],
            },
        ),
        migrations.CreateModel(
            name='CreazioneGuidataPasso',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=80)),
                ('titolo', models.CharField(max_length=200)),
                ('contenuto', models.TextField(blank=True, default='')),
                ('immagine', models.ImageField(blank=True, null=True, upload_to='creazione_guidata/')),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('flusso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='passi', to='gestione_plot.creazioneguidataflusso')),
            ],
            options={
                'verbose_name': 'Passo creazione guidata',
                'verbose_name_plural': 'Passi creazione guidata',
                'ordering': ['ordine', 'titolo'],
                'unique_together': {('flusso', 'slug')},
            },
        ),
        migrations.AddField(
            model_name='creazioneguidataflusso',
            name='passo_iniziale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='flussi_come_iniziale', to='gestione_plot.creazioneguidatapasso'),
        ),
        migrations.CreateModel(
            name='CreazioneGuidataScelta',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('etichetta', models.CharField(max_length=200)),
                ('descrizione', models.CharField(blank=True, default='', max_length=500)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('tipo_azione', models.CharField(choices=[('naviga', 'Naviga verso altro passo'), ('imposta_campo', 'Imposta campo personaggio'), ('aggiungi_abilita', 'Aggiungi abilità suggerite'), ('fine', 'Fine percorso')], default='naviga', max_length=32)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('passo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scelte', to='gestione_plot.creazioneguidatapasso')),
                ('passo_destinazione', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scelte_in_entrata', to='gestione_plot.creazioneguidatapasso')),
            ],
            options={
                'verbose_name': 'Scelta creazione guidata',
                'verbose_name_plural': 'Scelte creazione guidata',
                'ordering': ['ordine', 'etichetta'],
            },
        ),
    ]
