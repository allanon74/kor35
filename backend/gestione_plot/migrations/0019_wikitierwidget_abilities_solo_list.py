# Add abilities_solo_list to WikiTierWidget
#
# Generated manually: no runtime Django available in sandbox
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('gestione_plot', '0017_wikitierwidget_gradient_colors'),
    ]

    operations = [
        migrations.AddField(
            model_name='wikitierwidget',
            name='abilities_solo_list',
            field=models.BooleanField(default=False),
        ),
    ]

