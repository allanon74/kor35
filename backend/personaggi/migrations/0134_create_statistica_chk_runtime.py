# Crea la statistica CHK (contatore chakra in CHK_CUR) se assente: necessaria per rigenerazioni JSON e logica runtime.

from django.db import migrations


def crea_chk_se_assente(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    qs = Statistica.objects.filter(sigla__iexact="CHK")
    if qs.exists():
        row = qs.first()
        if row and not (getattr(row, "massimo_pool_sigla", None) or "").strip():
            qs.update(massimo_pool_sigla="CHA")
        return
    Statistica.objects.create(
        nome="Chakra (runtime)",
        descrizione="Contatore chakra in partita (chiave statistiche_temporanee: CHK_CUR). Il tetto massimo è la statistica CHA.",
        sigla="CHK",
        tipo="ST",
        ordine=990,
        is_primaria=False,
        is_risorsa_pool=False,
        massimo_pool_sigla="CHA",
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0133_statistica_massimo_pool_sigla"),
    ]

    operations = [
        migrations.RunPython(crea_chk_se_assente, noop_reverse),
    ]
