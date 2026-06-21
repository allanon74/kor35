from datetime import timedelta

from django.db import migrations, models


def backfill_reazione_fino(apps, schema_editor):
    EventoAttivoSessione = apps.get_model("pilotaggio", "EventoAttivoSessione")
    for row in EventoAttivoSessione.objects.filter(reazione_fino_at__isnull=True).iterator():
        if row.prossima_valutazione_at:
            row.reazione_fino_at = row.prossima_valutazione_at
            delta = int(
                max(1, (row.prossima_valutazione_at - row.created_at).total_seconds())
            )
            row.intervallo_reazione_secondi = delta
        else:
            row.intervallo_reazione_secondi = 22
            row.reazione_fino_at = row.created_at + timedelta(seconds=22)
            row.prossima_valutazione_at = row.reazione_fino_at
        row.save(
            update_fields=[
                "reazione_fino_at",
                "intervallo_reazione_secondi",
                "prossima_valutazione_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0029_fix_missili_traccianti_ca_effetto"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoattivosessione",
            name="reazione_fino_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Fine del tempo di reazione pilota: congelato alla comparsa dell'evento "
                    "(DEFCON al momento dello spawn). Nessuna valutazione CA/ST/SP prima di "
                    "questo istante."
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="intervallo_reazione_secondi",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text=(
                    "Secondi di reazione fissati alla comparsa "
                    "(tempo_risoluzione DEFCON allo spawn)."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="eventoattivosessione",
            name="prossima_valutazione_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Prossimo check CA/ST/SP programmato (dopo il primo intervallo di "
                    "reazione, usa intervallo DEFCON corrente)."
                ),
                null=True,
            ),
        ),
        migrations.RunPython(backfill_reazione_fino, migrations.RunPython.noop),
    ]
