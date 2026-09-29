"""Crea la statistica RDM (riduzione difficoltà minigioco) se manca.

sync_id fisso: la stessa riga su test, mirror e prod, così il sync non la duplica.
Ogni punto di RDM abbassa di 1 la difficoltà dei minigioco QR; se scende a ≤0
il minigioco viene saltato (effetto QR diretto).
"""
import uuid

from django.db import migrations

# uuid5(NAMESPACE_URL, "https://www.kor35.it/statistica/RDM")
RDM_SYNC_ID = uuid.UUID("60c13360-b0c3-5f06-8816-bcacd4816f08")


def crea_rdm_se_assente(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    esistente = Statistica.objects.filter(sigla__iexact="RDM").first()
    if esistente:
        if not (esistente.parametro or "").strip():
            occupato = (
                Statistica.objects.filter(parametro__iexact="RDM")
                .exclude(pk=esistente.pk)
                .exists()
            )
            if not occupato:
                esistente.parametro = "RDM"
                esistente.save(update_fields=["parametro"])
        return
    if Statistica.objects.filter(parametro__iexact="RDM").exists():
        return
    Statistica.objects.create(
        nome="Riduzione difficoltà minigioco",
        descrizione=(
            "Abbassa la difficoltà dei minigiochi sui QR. "
            "Ogni punto riduce di 1 la difficoltà; se scende a zero o meno "
            "il minigioco viene saltato e si applica subito l'effetto del QR. "
            "Si assegna da abilità, oggetti (e sezioni), infusioni e "
            "modificatori runtime delle tessiture."
        ),
        sigla="RDM",
        parametro="RDM",
        tipo="ST",
        ordine=981,
        valore_predefinito=0,
        valore_base_predefinito=0,
        is_numero=True,
        sync_id=RDM_SYNC_ID,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0281_manifesto_serie_immagini"),
    ]

    operations = [
        migrations.RunPython(crea_rdm_se_assente, noop_reverse),
    ]
