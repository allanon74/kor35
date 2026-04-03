# Campi workflow stampa STL / QR su QrCode (allineamento schema a models.py)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0132_timerruntime"),
    ]

    operations = [
        migrations.AddField(
            model_name="qrcode",
            name="stl_creato",
            field=models.BooleanField(
                default=False,
                verbose_name="STL preparato",
            ),
        ),
        migrations.AddField(
            model_name="qrcode",
            name="qr_stampato",
            field=models.BooleanField(
                default=False,
                verbose_name="QR stampato",
            ),
        ),
    ]
