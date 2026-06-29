from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0038_navigation_stats_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="pilotconsoleloginticket",
            name="ruolo",
            field=models.CharField(
                choices=[
                    ("navigazione", "Console Navigazione"),
                    ("scientifica", "Console Scientifica"),
                ],
                default="navigazione",
                help_text="Console destinataria del ticket login inverso.",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_scan_profondo_abilitato",
            field=models.BooleanField(
                default=True,
                help_text="Abilita scan profondo (consumo componenti stiva) in console scientifica.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_scan_max_per_volo",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="Numero massimo di scan profondi per sessione di volo.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_scan_requisiti_json",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Requisiti componenti per scan profondo (come riparazione QR). Vuoto = 1 unità qualsiasi.",
            ),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="scans_profondi_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Scan profondi eseguiti in questa sessione (max da runtime).",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="scan_profondo_eseguito",
            field=models.BooleanField(
                default=False,
                help_text="Scan profondo già usato su questo evento attivo.",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="scan_profondo_hint_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Indizio rivelato dall'ultimo scan profondo su questo evento.",
            ),
        ),
    ]
