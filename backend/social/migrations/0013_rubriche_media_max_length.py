from django.db import migrations, models
import social.models_rubriche


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0012_rubriche"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rubrica",
            name="logo",
            field=models.ImageField(
                blank=True,
                max_length=255,
                null=True,
                upload_to=social.models_rubriche.rubrica_logo_upload_to,
            ),
        ),
        migrations.AlterField(
            model_name="rubricaarticolo",
            name="hero_immagine",
            field=models.ImageField(
                blank=True,
                max_length=255,
                null=True,
                upload_to=social.models_rubriche.rubrica_articolo_hero_upload_to,
            ),
        ),
        migrations.AlterField(
            model_name="rubricaarticolo",
            name="video",
            field=models.FileField(
                blank=True,
                max_length=255,
                null=True,
                upload_to=social.models_rubriche.rubrica_articolo_hero_upload_to,
            ),
        ),
        migrations.AlterField(
            model_name="rubricaarticoloimmagine",
            name="immagine",
            field=models.ImageField(
                max_length=255,
                upload_to=social.models_rubriche.rubrica_articolo_gallery_upload_to,
            ),
        ),
    ]
