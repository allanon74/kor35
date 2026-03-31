from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0125_era_prefettura_personaggio_reset"),
    ]

    operations = [
        migrations.AddField(
            model_name="era",
            name="abbreviazione",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="prefettura_esterna",
            field=models.BooleanField(default=False),
        ),
    ]
