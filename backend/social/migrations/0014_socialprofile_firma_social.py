from django.db import migrations, models

import social.models


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0013_rubriche_media_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialprofile",
            name="firma_testo",
            field=models.TextField(
                blank=True,
                help_text="Testo firma mostrato sotto post e articoli di rubrica del personaggio.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="socialprofile",
            name="firma_banner",
            field=models.ImageField(
                blank=True,
                help_text="Banner firma mostrato sotto post e articoli di rubrica del personaggio.",
                max_length=255,
                null=True,
                upload_to=social.models.social_profile_firma_banner_upload_to,
            ),
        ),
    ]
