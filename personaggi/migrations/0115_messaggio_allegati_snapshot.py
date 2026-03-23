from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0114_social_core_korp_carriera_segni"),
    ]

    operations = [
        migrations.AddField(
            model_name="messaggio",
            name="crediti_allegati",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="messaggio",
            name="oggetti_allegati_snapshot",
            field=models.JSONField(blank=True, default=list),
        ),
    ]

