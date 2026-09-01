from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0014_socialprofile_firma_social"),
    ]

    operations = [
        migrations.AddField(
            model_name="rubricaarticoloimmagine",
            name="layout",
            field=models.CharField(
                choices=[
                    ("full", "A tutta colonna"),
                    ("wide", "Ampia (full-bleed)"),
                    ("float_left", "Affiancata a sinistra"),
                    ("float_right", "Affiancata a destra"),
                    ("grid_pair", "Metà griglia (in coppia)"),
                ],
                default="full",
                help_text="Preset editoriale in lettura (full, wide, float, metà griglia).",
                max_length=20,
            ),
        ),
    ]
