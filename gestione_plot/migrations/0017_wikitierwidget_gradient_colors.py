# Add gradient_colors to WikiTierWidget

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0016_wikitierwidget'),
    ]

    operations = [
        migrations.AddField(
            model_name='wikitierwidget',
            name='gradient_colors',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
