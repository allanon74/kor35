from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0130_merge_0121_recupero_0129_stat_container"),
    ]

    operations = [
        migrations.AddField(
            model_name="recuperorisorsaattivo",
            name="pause_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

