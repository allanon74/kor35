# Allineamento a DEFAULT_AUTO_FIELD = BigAutoField (Attachment ereditava AutoField dalle migrazioni 1.x).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_summernote", "0002_update-help_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attachment",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
