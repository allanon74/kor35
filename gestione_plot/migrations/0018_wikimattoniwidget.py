# Generated manually (no runtime Django available in sandbox)
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0017_wikitierwidget_gradient_colors'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('personaggi', '0058_remove_tessituramattone_mattone_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WikiMattoniWidget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, help_text='Titolo opzionale del widget (per identificazione interna)', max_length=200)),
                ('filter_type', models.CharField(choices=[('all', 'Tutti'), ('aura', 'Per Aura'), ('caratteristica', 'Per Caratteristica')], default='all', max_length=20)),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('data_modifica', models.DateTimeField(auto_now=True)),
                ('creatore', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='wiki_mattoni_widgets_creati', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Widget Mattoni',
                'verbose_name_plural': 'Widget Mattoni',
                'ordering': ['-data_creazione'],
            },
        ),
        migrations.AddField(
            model_name='wikimattoniwidget',
            name='aure',
            field=models.ManyToManyField(blank=True, help_text='Aure da includere (se filtro = Aura).', limit_choices_to={'tipo': 'AU'}, related_name='wiki_mattoni_widgets_aure', to='personaggi.punteggio'),
        ),
        migrations.AddField(
            model_name='wikimattoniwidget',
            name='caratteristiche',
            field=models.ManyToManyField(blank=True, help_text='Caratteristiche da includere (se filtro = Caratteristica).', limit_choices_to={'tipo': 'CA'}, related_name='wiki_mattoni_widgets_caratteristiche', to='personaggi.punteggio'),
        ),
    ]

