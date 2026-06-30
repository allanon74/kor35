# Generated manually for carte collezionabili MVP

import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import personaggi.carte_collezionabili_models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0223_carica_carriere_m2m'),
    ]

    operations = [
        migrations.CreateModel(
            name='CartaCollezionabile',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('codice', models.CharField(db_index=True, help_text='Codice univoco per campagna, es. ST-KAEL-001', max_length=40)),
                ('nome', models.CharField(max_length=120)),
                ('tipo', models.CharField(choices=[('PG', 'Personaggio'), ('OGG', 'Oggetto'), ('LUO', 'Luogo'), ('EVT', 'Evento')], db_index=True, max_length=3)),
                ('energia', models.CharField(choices=[('MAR', 'Marziale (Addestramento)'), ('TEC', 'Tecnologica (Apprendimento)'), ('INN', 'Innata (Genetica)'), ('MAG', 'Magica (Elementali)'), ('SAC', 'Sacra (Divine)'), ('PSI', 'Psionica (Mentali)'), ('ARC', 'Arcana (Artistiche)')], db_index=True, max_length=3)),
                ('rarita', models.CharField(choices=[('COM', 'Comune'), ('NC', 'Non comune'), ('RAR', 'Rara'), ('EPI', 'Epica'), ('LEG', 'Leggendaria'), ('UNI', 'Unica')], db_index=True, max_length=3)),
                ('costo_gioco', models.PositiveSmallIntegerField(default=0, help_text='Costo energia in partita (0–3).', validators=[django.core.validators.MaxValueValidator(3)])),
                ('attacco', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('salute', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('iniziativa', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(5)])),
                ('testo_gioco', models.TextField(blank=True, default='')),
                ('testo_lore', models.TextField(blank=True, default='')),
                ('set_collezione', models.CharField(blank=True, db_index=True, default='', help_text='Slug set narrativo, es. caduta-del-consiglio', max_length=80)),
                ('campagna_origine', models.CharField(blank=True, default='', help_text='Slug campagna lore (ST, SP, CA, …).', max_length=40)),
                ('legame_id', models.CharField(blank=True, db_index=True, default='', help_text='Identificatore combo reliquiario.', max_length=80)),
                ('tag_tematici', models.JSONField(blank=True, default=list)),
                ('bonus_equip', models.JSONField(blank=True, default=dict, help_text='Bonus passivo reliquiario, es. {"stat_sigla":"FOR","valore":1}')),
                ('duplicabile', models.BooleanField(default=False, help_text='Se true, fino a 2 copie nel mazzo da duello.')),
                ('immagine', models.ImageField(blank=True, null=True, upload_to='carte_collezionabili/')),
                ('attiva', models.BooleanField(db_index=True, default=True)),
                ('ordine_set', models.PositiveSmallIntegerField(default=0)),
                ('campagna', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='carte_collezionabili', to='personaggi.campagna')),
            ],
            options={
                'verbose_name': 'Carta collezionabile',
                'verbose_name_plural': 'Carte collezionabili',
                'ordering': ['set_collezione', 'ordine_set', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='ConfigurazioneCarteCollezionabili',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pity_soglia', models.PositiveSmallIntegerField(default=20, help_text='Bustine senza Rara+ prima del pity.')),
                ('max_bustine_giorno', models.PositiveSmallIntegerField(default=10, help_text='Limite aperture bustina per PG al giorno.')),
                ('mercato_commissione_pct', models.DecimalField(decimal_places=2, default=Decimal('8.00'), max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('campagna', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='config_carte_collezionabili', to='personaggi.campagna')),
            ],
            options={
                'verbose_name': 'Configurazione carte collezionabili',
                'verbose_name_plural': 'Configurazioni carte collezionabili',
            },
        ),
        migrations.CreateModel(
            name='BustinaCarte',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('nome', models.CharField(max_length=120)),
                ('descrizione', models.TextField(blank=True, default='')),
                ('costo_crediti', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('carte_per_bustina', models.PositiveSmallIntegerField(default=5)),
                ('set_collezione', models.CharField(blank=True, default='', help_text='Se valorizzato, limita il pool a questo set.', max_length=80)),
                ('probabilita_rarita', models.JSONField(blank=True, default=dict)),
                ('garantisce_min_rarita', models.CharField(blank=True, choices=[('COM', 'Comune'), ('NC', 'Non comune'), ('RAR', 'Rara'), ('EPI', 'Epica'), ('LEG', 'Leggendaria'), ('UNI', 'Unica')], default='', help_text='Rarità minima garantita (es. NC = almeno una Non comune).', max_length=3)),
                ('attiva', models.BooleanField(db_index=True, default=True)),
                ('ordine', models.PositiveSmallIntegerField(default=0)),
                ('campagna', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bustine_carte', to='personaggi.campagna')),
            ],
            options={
                'verbose_name': 'Bustina carte',
                'verbose_name_plural': 'Bustine carte',
                'ordering': ['ordine', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='CartaPosseduta',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('fonte', models.CharField(choices=[('BUST', 'Bustina'), ('SCAM', 'Scambio'), ('MERC', 'Mercato'), ('STAF', 'Staff')], default='BUST', max_length=4)),
                ('serial_globale', models.PositiveIntegerField(blank=True, help_text='Numero seriale per carte Uniche (1 esemplare globale).', null=True, unique=True)),
                ('carta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='possessioni', to='personaggi.cartacollezionabile')),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carte_possedute', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Carta posseduta',
                'verbose_name_plural': 'Carte possedute',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MazzoDuello',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('nome', models.CharField(default='Mazzo principale', max_length=80)),
                ('carte_possedute_ids', models.JSONField(blank=True, default=list, help_text='Lista UUID CartaPosseduta (max 15).')),
                ('is_default', models.BooleanField(default=False)),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mazzi_duello', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Mazzo duello',
                'verbose_name_plural': 'Mazzi duello',
                'ordering': ['-is_default', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='AperturaBustinaCarte',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('costo_pagato', models.DecimalField(decimal_places=2, max_digits=10)),
                ('carte_ottenute_ids', models.JSONField(blank=True, default=list)),
                ('bustina', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='aperture', to='personaggi.bustinacarte')),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aperture_bustine_carte', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Apertura bustina carte',
                'verbose_name_plural': 'Aperture bustine carte',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReliquiarioSlot',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('slot_index', models.PositiveSmallIntegerField(validators=[django.core.validators.MaxValueValidator(4)])),
                ('carta_posseduta', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='slot_reliquiario', to='personaggi.cartaposseduta')),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reliquiario_slots', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Slot reliquiario',
                'verbose_name_plural': 'Slot reliquiario',
                'ordering': ['personaggio', 'slot_index'],
                'unique_together': {('personaggio', 'slot_index')},
            },
        ),
        migrations.AddIndex(
            model_name='cartacollezionabile',
            index=models.Index(fields=['campagna', 'rarita', 'attiva'], name='personaggi__campagn_8f4a21_idx'),
        ),
        migrations.AddIndex(
            model_name='cartacollezionabile',
            index=models.Index(fields=['campagna', 'set_collezione'], name='personaggi__campagn_2c9e8a_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='cartacollezionabile',
            unique_together={('campagna', 'codice')},
        ),
        migrations.AddIndex(
            model_name='cartaposseduta',
            index=models.Index(fields=['personaggio', 'carta'], name='personaggi__persona_7d3b12_idx'),
        ),
    ]
