# Generated manually: nuovi tipi minigioco wire_match + tap_order su choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0257_innescotimer_broadcast_push"),
    ]

    operations = [
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="tipo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sliding_puzzle", "Sliding puzzle"),
                    ("memory", "Memory"),
                    ("rotate_tiles", "Tessere rotabili"),
                    ("simon", "Sequenza (Simon)"),
                    ("pattern_lock", "Pattern lock"),
                    ("pipe_connect", "Collega i tubi"),
                    ("wire_match", "Collega i fili"),
                    ("tap_order", "Tocca in ordine"),
                ],
                default="sliding_puzzle",
                help_text="Legacy: ignorato se tipi_abilitati è valorizzato.",
                max_length=32,
            ),
        ),
    ]
