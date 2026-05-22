from django.db import migrations, models

from gestione_plot.staff_dashboard_layout import DEFAULT_STAFF_DASHBOARD_LAYOUT


def populate_default_layout(apps, schema_editor):
    ConfigurazioneSito = apps.get_model("gestione_plot", "ConfigurazioneSito")
    ConfigurazioneSito.objects.filter(pk=1).update(
        staff_dashboard_layout=DEFAULT_STAFF_DASHBOARD_LAYOUT,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0036_creazione_guidata_giocatori_default_spento"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionesito",
            name="staff_dashboard_layout",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Ordine e raggruppamento voci menu Dashboard Staff (globale, sincronizzato).",
                verbose_name="Layout Dashboard Staff",
            ),
        ),
        migrations.RunPython(populate_default_layout, migrations.RunPython.noop),
    ]
