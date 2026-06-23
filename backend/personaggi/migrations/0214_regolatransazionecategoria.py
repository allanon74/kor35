from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_regole_transazione(apps, schema_editor):
    Campagna = apps.get_model('personaggi', 'Campagna')
    RegolaTransazioneCategoria = apps.get_model('personaggi', 'RegolaTransazioneCategoria')
    codici = [
        ('crediti', 'Crediti', 0, False, False),
        ('oggetti', 'Oggetti', 10, False, False),
        ('materia', 'Materia', 20, False, False),
        ('mod', 'Mod', 30, False, False),
        ('consumabili', 'Consumabili', 40, False, False),
        ('innesti', 'Innesti', 50, False, False),
        ('mutazioni', 'Mutazioni', 60, False, False),
        ('infusioni', 'Infusioni', 70, True, True),
        ('tessiture', 'Tessiture', 80, True, True),
        ('cerimoniali', 'Cerimoniali', 90, True, True),
    ]
    for campagna in Campagna.objects.all():
        for codice, nome, ordine, solo_poss, copia in codici:
            RegolaTransazioneCategoria.objects.get_or_create(
                campagna_id=campagna.id,
                codice=codice,
                defaults={
                    'sync_id': uuid.uuid4(),
                    'nome': nome,
                    'ordine': ordine,
                    'vendibile_giocatori': True,
                    'requisiti_gruppo': {},
                    'solo_posseduti': solo_poss,
                    'trasferimento_copia': copia,
                    'rispetta_non_insegnabile': True,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0213_personaggio_note_master'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegolaTransazioneCategoria',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codice', models.CharField(choices=[('crediti', 'Crediti'), ('oggetti', 'Oggetti'), ('materia', 'Materia'), ('mod', 'Mod'), ('consumabili', 'Consumabili'), ('innesti', 'Innesti'), ('mutazioni', 'Mutazioni'), ('infusioni', 'Infusioni'), ('tessiture', 'Tessiture'), ('cerimoniali', 'Cerimoniali')], max_length=32)),
                ('nome', models.CharField(max_length=80)),
                ('vendibile_giocatori', models.BooleanField(default=True, help_text='Se disattivo, la categoria non può comparire nelle proposte di scambio.', verbose_name='Scambiabile tra giocatori')),
                ('requisiti_gruppo', models.JSONField(blank=True, default=dict, help_text='{"operator":"AND|OR","requisiti":[...]} — vuoto = sempre consentito (se vendibile).')),
                ('solo_posseduti', models.BooleanField(default=False, help_text='Solo beni già in inventario del personaggio (es. tecniche non dal tab Nuove Accademia).')),
                ('trasferimento_copia', models.BooleanField(default=False, help_text="Per tecniche: il destinatario riceve una copia; il mittente conserva l'originale.")),
                ('rispetta_non_insegnabile', models.BooleanField(default=True, help_text='Blocca il trasferimento se la tecnica è marcata non acquistabile/insegnabile.')),
                ('ordine', models.PositiveSmallIntegerField(default=0)),
                ('campagna', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='regole_transazione_categorie', to='personaggi.campagna')),
            ],
            options={
                'verbose_name': 'Regola transazione (categoria)',
                'verbose_name_plural': 'Regole transazione (categorie)',
                'ordering': ['campagna', 'ordine', 'codice'],
            },
        ),
        migrations.AddConstraint(
            model_name='regolatransazionecategoria',
            constraint=models.UniqueConstraint(fields=('campagna', 'codice'), name='uniq_regola_tx_campagna_codice'),
        ),
        migrations.RunPython(seed_regole_transazione, migrations.RunPython.noop),
    ]
