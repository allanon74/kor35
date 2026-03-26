from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0004_social_stories"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialstory",
            name="auto_publish_mode",
            field=models.CharField(
                choices=[
                    ("OFF", "Non pubblicare come post"),
                    ("NOW", "Pubblica subito anche come post"),
                    ("EXPIRE", "Pubblica come post alla scadenza"),
                ],
                default="OFF",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="socialstory",
            name="converted_post",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_stories",
                to="social.socialpost",
            ),
        ),
        migrations.AddField(
            model_name="socialstory",
            name="text_size",
            field=models.PositiveSmallIntegerField(default=22),
        ),
    ]

