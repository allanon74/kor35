"""Ripara ca_effetto di «Missili traccianti»: UUID sottosistema obsoleto → Deflettori (E)."""

from django.db import migrations


def fix_missili_ca_effetto(apps, schema_editor):
    EventoNave = apps.get_model("pilotaggio", "EventoNave")
    SottosistemaNave = apps.get_model("pilotaggio", "SottosistemaNave")
    ev = EventoNave.objects.filter(nome="Missili traccianti").first()
    sdef = SottosistemaNave.objects.filter(codice="E").first()
    if ev is None or sdef is None:
        return
    regole = dict(ev.regole_json or {})
    cae = dict(regole.get("ca_effetto") or {})
    cae["tipo"] = "guasto_sottosistema"
    cae["sottosistema_id"] = str(sdef.pk)
    cae["sottosistema_codice"] = "E"
    regole["ca_effetto"] = cae
    ev.regole_json = regole
    ev.save(update_fields=["regole_json"])


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0028_eventoattivosessione_valutazioni_eseguite"),
    ]

    operations = [
        migrations.RunPython(fix_missili_ca_effetto, migrations.RunPython.noop),
    ]
