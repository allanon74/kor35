import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0021_evento_sync_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='WikiTierCollectionWidget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, help_text='Titolo opzionale del widget (per identificazione interna)', max_length=200)),
                ('source_mode', models.CharField(choices=[('all', 'Tutti i widget tier'), ('selected', 'Solo widget selezionati')], default='all', max_length=20)),
                ('tier_type_filter', models.CharField(choices=[('all', 'Tutti i tipi'), ('TG', 'Tabelle Generali'), ('T1', 'Tier 1'), ('T2', 'Tier 2'), ('T3', 'Tier 3'), ('T4', 'Tier 4')], default='all', max_length=8)),
                ('sort_by', models.CharField(choices=[('tier_name', 'Nome Tier'), ('widget_created', 'Data creazione widget')], default='tier_name', max_length=32)),
                ('sort_dir', models.CharField(choices=[('asc', 'Crescente'), ('desc', 'Decrescente')], default='asc', max_length=8)),
                ('show_runtime_filters', models.BooleanField(default=True, help_text='Mostra ricerca/filtro/ordinamento direttamente nel widget.')),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('data_modifica', models.DateTimeField(auto_now=True)),
                ('creatore', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wiki_tier_collection_widgets_creati', to=settings.AUTH_USER_MODEL)),
                ('widgets', models.ManyToManyField(blank=True, help_text='Widget Tier inclusi (usati quando source_mode = solo selezionati).', related_name='collections', to='gestione_plot.wikitierwidget')),
            ],
            options={
                'verbose_name': 'Widget Collezione Tier',
                'verbose_name_plural': 'Widget Collezione Tier',
                'ordering': ['-data_creazione'],
            },
        ),
    ]
