from django.db import migrations, models


def marca_vincite_gia_accreditate(apps, schema_editor):
    """Le puntate vinte liquidate prima della riscossione manuale erano già accreditate."""
    PuntataScommessa = apps.get_model("personaggi", "PuntataScommessa")
    PuntataScommessa.objects.filter(
        stato="WON",
        liquidata_at__isnull=False,
    ).update(vincita_riscossa=True)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0210_messaggio_mostra_proprietario_giocatore"),
    ]

    operations = [
        migrations.AddField(
            model_name="puntatascommessa",
            name="vincita_riscossa",
            field=models.BooleanField(
                default=False,
                help_text="True se il giocatore ha già incassato la vincita (riscossione manuale).",
            ),
        ),
        migrations.AddField(
            model_name="puntatascommessa",
            name="riscossa_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(marca_vincite_gia_accreditate, migrations.RunPython.noop),
    ]
