# Rinomina per non collidere con Personaggio.crediti_deposito (property).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0297_qr_usi_crediti_inventario"),
    ]

    operations = [
        migrations.RenameField(
            model_name="inventario",
            old_name="crediti_deposito",
            new_name="crediti_deposito_contenuti",
        ),
    ]
