"""Crea la statistica SCT (slot contratto extra) se manca.

sync_id fisso: la stessa riga su test, mirror e prod, così il sync non la duplica.
"""
import uuid

from django.db import migrations

# uuid5(NAMESPACE_URL, "https://www.kor35.it/statistica/SCT")
SCT_SYNC_ID = uuid.UUID("eea896e0-a0e5-5d74-bf1d-20d6b748f44b")


def crea_sct_se_assente(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    esistente = Statistica.objects.filter(sigla__iexact="SCT").first()
    if esistente:
        if not (esistente.parametro or "").strip():
            occupato = (
                Statistica.objects.filter(parametro__iexact="SCT")
                .exclude(pk=esistente.pk)
                .exists()
            )
            if not occupato:
                esistente.parametro = "SCT"
                esistente.save(update_fields=["parametro"])
        return
    if Statistica.objects.filter(parametro__iexact="SCT").exists():
        return
    Statistica.objects.create(
        nome="Slot contratto",
        descrizione=(
            "Slot di contratto extra del proponente. "
            "Le abilità e gli oggetti la aumentano. Conta solo se la Korp sottoscrive i contratti."
        ),
        sigla="SCT",
        parametro="SCT",
        tipo="ST",
        ordine=980,
        valore_predefinito=0,
        valore_base_predefinito=0,
        sync_id=SCT_SYNC_ID,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0278_contratti"),
    ]

    operations = [
        migrations.RunPython(crea_sct_se_assente, noop_reverse),
    ]
