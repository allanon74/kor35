import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0287_prestito_tecniche"),
        ("pilotaggio", "0044_console_comunicazioni"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="protocollocomunicazione",
            name="dipartimento",
        ),
        migrations.AddField(
            model_name="protocollocomunicazione",
            name="korp",
            field=models.ForeignKey(
                blank=True,
                help_text="Dipartimento: carriera di tipo KORP. I membri attivi ricevono il testo.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="protocolli_comunicazione",
                to="personaggi.carriera",
            ),
        ),
        migrations.DeleteModel(
            name="DipartimentoBordo",
        ),
    ]
