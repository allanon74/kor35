from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0006_alter_socialpost_immagine_alter_socialpost_video_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialprofile",
            name="nickname",
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
    ]
