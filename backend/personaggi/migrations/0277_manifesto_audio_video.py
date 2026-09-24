# Generated manually — manifesto QR: audio/video opzionali alla scansione

from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0276_abilita_flags_t2_t3_residui"),
    ]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="audio_file",
            field=models.FileField(
                blank=True,
                help_text="Audio opzionale (mp3/m4a/ogg…). Riprodotto alla scansione se il PG può leggere.",
                null=True,
                upload_to="manifesti/audio/%Y/%m/",
                validators=[
                    FileExtensionValidator(
                        allowed_extensions=["mp3", "m4a", "aac", "ogg", "wav", "opus"]
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="video_file",
            field=models.FileField(
                blank=True,
                help_text="Video opzionale (mp4/webm…). Preferire file compressi: sync via rsync.",
                null=True,
                upload_to="manifesti/video/%Y/%m/",
                validators=[
                    FileExtensionValidator(allowed_extensions=["mp4", "webm", "mov", "m4v"])
                ],
            ),
        ),
    ]
