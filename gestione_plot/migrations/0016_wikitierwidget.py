# Generated manually for WikiTierWidget

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0015_wikibuttonwidget_wikibutton'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('personaggi', '0101_alter_transazionesospesa_options_and_more'),  # Tier exists in personaggi
    ]

    operations = [
        migrations.CreateModel(
            name='WikiTierWidget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('abilities_collapsible', models.BooleanField(default=True)),
                ('abilities_collapsed_by_default', models.BooleanField(default=False)),
                ('show_description', models.BooleanField(default=True)),
                ('color_style', models.CharField(default='default', max_length=20)),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('data_modifica', models.DateTimeField(auto_now=True)),
                ('creatore', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wiki_tier_widgets_creati', to=settings.AUTH_USER_MODEL)),
                ('tier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wiki_tier_widgets', to='personaggi.tier')),
            ],
            options={
                'verbose_name': 'Widget Tier',
                'verbose_name_plural': 'Widget Tier',
                'ordering': ['-data_creazione'],
            },
        ),
    ]
