# PV, PA, PS (guscio), CHA come risorse pool: contatore in risorse_consumabili.
# Migra da statistiche_temporanee (*_CUR / CHK_CUR) e rimuove la statistica fantasma CHK.

from django.db import migrations


TACTICAL_SIGLE = ("PV", "PA", "PS", "CHA")


def forwards(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    Personaggio = apps.get_model("personaggi", "Personaggio")

    for sigla in TACTICAL_SIGLE:
        Statistica.objects.filter(sigla__iexact=sigla).update(is_risorsa_pool=True)

    # massimo_pool_sigla su CHA non serve più (tetto = CHA stessa)
    Statistica.objects.filter(sigla__iexact="CHA").update(massimo_pool_sigla=None)

    for pg in Personaggio.objects.all().iterator():
        rc = dict(pg.risorse_consumabili or {})
        temp = dict(pg.statistiche_temporanee or {})

        def set_pool(sigla, val):
            try:
                rc[sigla] = int(val)
            except (TypeError, ValueError):
                pass

        if "PV_CUR" in temp:
            set_pool("PV", temp["PV_CUR"])
        if "PA_CUR" in temp:
            set_pool("PA", temp["PA_CUR"])
        if "PS_CUR" in temp:
            set_pool("PS", temp["PS_CUR"])
        if "CHA_CUR" in temp:
            set_pool("CHA", temp["CHA_CUR"])
        elif "CHK_CUR" in temp:
            set_pool("CHA", temp["CHK_CUR"])

        for k in ("PV_CUR", "PA_CUR", "PS_CUR", "CHA_CUR", "CHK_CUR"):
            temp.pop(k, None)

        pg.risorse_consumabili = rc
        pg.statistiche_temporanee = temp
        pg.save(update_fields=["risorse_consumabili", "statistiche_temporanee", "updated_at"])

    Statistica.objects.filter(sigla__iexact="CHK").delete()


def backwards(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    for sigla in TACTICAL_SIGLE:
        Statistica.objects.filter(sigla__iexact=sigla).update(is_risorsa_pool=False)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0134_create_statistica_chk_runtime"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
