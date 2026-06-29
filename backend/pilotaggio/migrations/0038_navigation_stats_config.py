from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0037_sessione_allarme_equipaggio"),
    ]

    operations = [
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="navigazione_stat_accesso_sigla",
            field=models.CharField(
                default="0PI",
                help_text="Sigla statistica per accesso console navigazione (pilota, es. 0PI≥1).",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="sabotaggio_stat_sigla",
            field=models.CharField(
                default="0SA",
                help_text="Sigla statistica sabotaggio QR sottosistemi.",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="riparazione_stat_sigla",
            field=models.CharField(
                default="0RI",
                help_text="Sigla statistica riparazione (e ricarica) QR sottosistemi.",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_console_abilitata",
            field=models.BooleanField(
                default=False,
                help_text="Abilita console /pilot/?screen=scientifica (in implementazione).",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_login_richiesto",
            field=models.BooleanField(
                default=True,
                help_text="Richiede login alla console scientifica.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_stat_accesso_sigla",
            field=models.CharField(
                default="0SC",
                help_text="Sigla statistica accesso console scientifica (es. 0SC>0).",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="comunicazioni_console_abilitata",
            field=models.BooleanField(
                default=False,
                help_text="Riservato: console comunicazioni (non ancora implementata).",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="comunicazioni_stat_accesso_sigla",
            field=models.CharField(
                default="0CO",
                help_text="Sigla statistica futura console comunicazioni.",
                max_length=3,
            ),
        ),
        migrations.AlterField(
            model_name="pilotruntimeconfig",
            name="compattatore_console_abilitata",
            field=models.BooleanField(
                default=False,
                help_text="Abilita Console Ingegneria (/pilot/?screen=compattatore).",
            ),
        ),
        migrations.AlterField(
            model_name="pilotruntimeconfig",
            name="compattatore_login_richiesto",
            field=models.BooleanField(
                default=True,
                help_text="Richiede login alla Console Ingegneria.",
            ),
        ),
        migrations.AlterField(
            model_name="pilotruntimeconfig",
            name="compattatore_stat_accesso_sigla",
            field=models.CharField(
                default="0IN",
                help_text="Sigla statistica Console Ingegneria e tab Stiva app (es. 0IN>0).",
                max_length=3,
            ),
        ),
        migrations.AlterField(
            model_name="pilotruntimeconfig",
            name="compattatore_quantico_abilitato",
            field=models.BooleanField(
                default=False,
                help_text="Abilita operazione quantica in Console Ingegneria (default off fino a evento).",
            ),
        ),
    ]
