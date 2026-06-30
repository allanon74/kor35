# Carte: flag abilitata + duello live

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0224_carte_collezionabili'),
    ]

    operations = [
        migrations.AddField(
            model_name='configurazionecartecollezionabili',
            name='abilitata',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Se disattiva, tab Carte / bustine / reliquiario / duelli non sono visibili ai giocatori.',
            ),
        ),
        migrations.CreateModel(
            name='DuelloCarte',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('mazzo_sfidante_ids', models.JSONField(blank=True, default=list)),
                ('mazzo_sfidato_ids', models.JSONField(blank=True, default=list)),
                ('stato', models.CharField(choices=[('ATT', 'In attesa'), ('COR', 'In corso'), ('FIN', 'Terminato'), ('ANN', 'Annullato')], db_index=True, default='ATT', max_length=3)),
                ('influenza_sfidante', models.PositiveSmallIntegerField(default=20)),
                ('influenza_sfidato', models.PositiveSmallIntegerField(default=20)),
                ('stato_gioco', models.JSONField(blank=True, default=dict)),
                ('codice_invito', models.CharField(blank=True, db_index=True, default='', max_length=8)),
                ('campagna', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='duelli_carte', to='personaggi.campagna')),
                ('sfidante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='duelli_carte_sfidante', to='personaggi.personaggio')),
                ('sfidato', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='duelli_carte_sfidato', to='personaggi.personaggio')),
                ('turno_personaggio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='duelli_carte_turno', to='personaggi.personaggio')),
                ('vincitore', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='duelli_carte_vinti', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Duello carte',
                'verbose_name_plural': 'Duelli carte',
                'ordering': ['-updated_at'],
            },
        ),
    ]
