from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0244_card_studio_multitemplate_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartestudiotemplate",
            name="mse_assets_manifest",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Elenco file estratti dal package MSE con metadati (grafici e non).",
            ),
        ),
        migrations.AddField(
            model_name="cartestudiotemplate",
            name="mse_extracted_root",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Path relativo media della directory estratta del template MSE.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="cartestudiotemplate",
            name="mse_style_package",
            field=models.FileField(
                blank=True,
                help_text="Archivio originale .mse-style/.zip caricato.",
                null=True,
                upload_to="card_studio/mse_styles/",
            ),
        ),
    ]

