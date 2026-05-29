from django.db import migrations, models


def imposta_preset_default(apps, schema_editor):
    ManualePdf = apps.get_model("gestione_plot", "ManualePdf")
    defaults = {
        "completo": "master",
        "master": "master",
        "giocatore": "giocatore",
    }
    for manuale in ManualePdf.objects.all():
        preset = defaults.get(manuale.slug, "giocatore")
        if manuale.stile_preset != preset:
            manuale.stile_preset = preset
            manuale.save(update_fields=["stile_preset"])


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0040_manuale_pdf_wiki"),
    ]

    operations = [
        migrations.AddField(
            model_name="manualepdf",
            name="stile",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Override JSON sul preset (font, margini, immagini, widget, indice, ecc.).",
                verbose_name="Override stile PDF",
            ),
        ),
        migrations.AddField(
            model_name="manualepdf",
            name="stile_preset",
            field=models.CharField(
                default="giocatore",
                help_text="Preset di impaginazione; con «personalizzato» contano gli override in stile.",
                max_length=40,
                verbose_name="Preset stile PDF",
            ),
        ),
        migrations.RunPython(imposta_preset_default, migrations.RunPython.noop),
    ]
