from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0164_rename_personaggi_w_personag_7adf02_idx_personaggi__persona_f951c9_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="qrcode",
            name="inventario_colore_codice",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Colore del codice QR rilevato durante inventario (HEX, es. #FFFFFF).",
                max_length=7,
            ),
        ),
        migrations.AddField(
            model_name="qrcode",
            name="inventario_colore_sfondo",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Colore sfondo QR rilevato durante inventario (HEX, es. #000000).",
                max_length=7,
            ),
        ),
        migrations.AddField(
            model_name="qrcode",
            name="inventario_presente",
            field=models.BooleanField(
                default=False,
                help_text="Flag inventario QR staff: presente all'ultimo inventario.",
            ),
        ),
    ]
