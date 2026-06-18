from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0010_backfill_story_expires_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="socialprofile",
            name="nickname",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
    ]
