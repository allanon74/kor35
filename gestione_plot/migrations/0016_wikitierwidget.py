# Generated manually for WikiTierWidget

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0093_alter_tier_tipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gestione_plot', '0015_wikibuttonwidget_wikibutton'),
    ]

    operations = [
        migrations.CreateModel(
            name='WikiTierWidget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abilities_collapsible', models.BooleanField(default=True, verbose_name='Abilità in sezione collassabile')),
                ('abilities_collapsed_by_default', models.BooleanField(default=False, help_text='Se False, la sezione parte aperta', verbose_name='Sezione abilità chiusa di default')),
                ('show_description', models.BooleanField(default=True, verbose_name='Mostra descrizione tier')),
                ('color_style', models.CharField(choices=[('default', 'Default (attuale)'), ('white', 'Bianco'), ('gray', 'Grigio'), ('red', 'Rosso'), ('black', 'Nero'), ('ochre', 'Ocra'), ('blue', 'Blu'), ('yellow', 'Giallo'), ('purple', 'Viola'), ('green', 'Verde'), ('porpora', 'Porpora')], default='default', max_length=20)),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('data_modifica', models.DateTimeField(auto_now=True)),
                ('creatore', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tier_widgets_creati', to=settings.AUTH_USER_MODEL)),
                ('tier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wiki_widget_configs', to='personaggi.tier')),
            ],
            options={
                'verbose_name': 'Widget Tier',
                'verbose_name_plural': 'Widget Tier',
                'ordering': ['-data_creazione'],
            },
        ),
    ]
