from django.db import migrations, models


def attiva_sezione_dove_minigioco_attivo(apps, schema_editor):
    MinigiocoQrConfig = apps.get_model("personaggi", "MinigiocoQrConfig")
    MinigiocoQrConfig.objects.filter(attivo=True).update(sezione_attiva=True)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0208_minigioco_usa_default_pagina"),
    ]

    operations = [
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="messaggio_accesso_negato",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Testo mostrato se si scansiona senza i requisiti (se vuoto, messaggio automatico).",
            ),
        ),
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="sezione_attiva",
            field=models.BooleanField(
                default=False,
                help_text="Se True, la sezione minigiochi governa l'accesso al QR (requisiti + minigioco opzionale).",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="attivo",
            field=models.BooleanField(
                default=False,
                help_text="Se True (con sezione attiva), richiede il minigioco prima dell'effetto QR.",
            ),
        ),
        migrations.AlterField(
            model_name="minigiocoqrconfig",
            name="requisiti_attivazione",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Con sezione attiva: blocca il QR se il PG non soddisfa questi requisiti (vuoto = accesso libero).",
            ),
        ),
        migrations.RunPython(attiva_sezione_dove_minigioco_attivo, migrations.RunPython.noop),
    ]
