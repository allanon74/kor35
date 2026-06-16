from django.db import migrations, models


def popola_random_defaults(apps, schema_editor):
    MinigiocoQrConfig = apps.get_model("personaggi", "MinigiocoQrConfig")
    tipi_tutti = ["sliding_puzzle", "memory", "rotate_tiles"]
    for cfg in MinigiocoQrConfig.objects.all():
        if not cfg.tipi_abilitati:
            cfg.tipi_abilitati = tipi_tutti
        if not cfg.difficolta_min:
            cfg.difficolta_min = 1
        if cfg.difficolta_min > cfg.difficolta:
            cfg.difficolta_min, cfg.difficolta = cfg.difficolta, cfg.difficolta_min
        cfg.save(update_fields=["tipi_abilitati", "difficolta_min", "difficolta"])


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0193_minigioco_qr"),
    ]

    operations = [
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="difficolta_min",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Difficoltà minima (1–4) estratta a caso a ogni sessione.",
            ),
        ),
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="tipi_abilitati",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Pool giochi estratti a caso (es. sliding_puzzle, memory, rotate_tiles).",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="difficolta",
            field=models.PositiveSmallIntegerField(
                default=4,
                help_text="Difficoltà massima (1–4) estratta a caso a ogni sessione.",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="tipo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sliding_puzzle", "Sliding puzzle"),
                    ("memory", "Memory"),
                    ("rotate_tiles", "Tessere rotabili"),
                ],
                default="sliding_puzzle",
                help_text="Legacy: ignorato se tipi_abilitati è valorizzato.",
                max_length=32,
            ),
        ),
        migrations.RunPython(popola_random_defaults, migrations.RunPython.noop),
    ]
