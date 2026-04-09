# Deduplica righe through / join sincronizzabili con stessa chiave logica e sync_id diversi,
# poi UNIQUE su coppie (modello, requisito), (personaggio, …), ecc.

from django.db import migrations
from django.db.models import Count


# (nome_modello Django, campi DB *_id per il raggruppamento)
DEDUPE_SPEC = [
    ("PersonaggioAttivata", ["personaggio_id", "attivata_id"]),
    ("PersonaggioInfusione", ["personaggio_id", "infusione_id"]),
    ("PersonaggioCerimoniale", ["personaggio_id", "cerimoniale_id"]),
    ("PersonaggioModelloAura", ["personaggio_id", "modello_aura_id"]),
    ("AttivataElemento", ["attivata_id", "elemento_id"]),
    ("ModelloAuraRequisitoDoppia", ["modello_id", "requisito_id"]),
    ("ModelloAuraRequisitoMattone", ["modello_id", "requisito_id"]),
    ("ModelloAuraRequisitoCaratt", ["modello_id", "requisito_id"]),
    ("abilita_tier", ["abilita_id", "tabella_id"]),
    ("abilita_prerequisito", ["abilita_id", "prerequisito_id"]),
    ("abilita_requisito", ["abilita_id", "requisito_id"]),
    ("abilita_sbloccata", ["abilita_id", "sbloccata_id"]),
    ("abilita_punteggio", ["abilita_id", "punteggio_id"]),
]


def _dedupe_one(apps, model_name, key_fields):
    Model = apps.get_model("personaggi", model_name)
    dup_groups = (
        Model.objects.values(*key_fields)
        .annotate(_c=Count("id"))
        .filter(_c__gt=1)
    )
    for row in dup_groups:
        flt = {k: row[k] for k in key_fields}
        qs = Model.objects.filter(**flt).order_by("-updated_at", "-id")
        keep_pk = qs.values_list("id", flat=True).first()
        if keep_pk is None:
            continue
        Model.objects.filter(**flt).exclude(pk=keep_pk).delete()


def dedupe_all(apps, schema_editor):
    for model_name, key_fields in DEDUPE_SPEC:
        _dedupe_one(apps, model_name, key_fields)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0112_personaggioabilita_unique_together"),
    ]

    operations = [
        migrations.RunPython(dedupe_all, noop_reverse),
        migrations.AlterUniqueTogether(
            name="personaggioattivata",
            unique_together={("personaggio", "attivata")},
        ),
        migrations.AlterModelOptions(
            name="personaggioattivata",
            options={
                "verbose_name": "Personaggio - Attivata",
                "verbose_name_plural": "Personaggio - Attivate",
            },
        ),
        migrations.AlterUniqueTogether(
            name="personaggioinfusione",
            unique_together={("personaggio", "infusione")},
        ),
        migrations.AlterModelOptions(
            name="personaggioinfusione",
            options={
                "verbose_name": "Personaggio - Infusione",
                "verbose_name_plural": "Personaggio - Infusioni",
            },
        ),
        migrations.AlterUniqueTogether(
            name="personaggiocerimoniale",
            unique_together={("personaggio", "cerimoniale")},
        ),
        migrations.AlterModelOptions(
            name="personaggiocerimoniale",
            options={
                "verbose_name": "Personaggio - Cerimoniale",
                "verbose_name_plural": "Personaggio - Cerimoniali",
            },
        ),
        migrations.AlterUniqueTogether(
            name="personaggiomodelloaura",
            unique_together={("personaggio", "modello_aura")},
        ),
        migrations.AlterUniqueTogether(
            name="attivataelemento",
            unique_together={("attivata", "elemento")},
        ),
        migrations.AlterUniqueTogether(
            name="modelloaurarequisitodoppia",
            unique_together={("modello", "requisito")},
        ),
        migrations.AlterUniqueTogether(
            name="modelloaurarequisitomattone",
            unique_together={("modello", "requisito")},
        ),
        migrations.AlterUniqueTogether(
            name="modelloaurarequisitocaratt",
            unique_together={("modello", "requisito")},
        ),
        migrations.AlterUniqueTogether(
            name="abilita_tier",
            unique_together={("abilita", "tabella")},
        ),
        migrations.AlterUniqueTogether(
            name="abilita_prerequisito",
            unique_together={("abilita", "prerequisito")},
        ),
        migrations.AlterUniqueTogether(
            name="abilita_requisito",
            unique_together={("abilita", "requisito")},
        ),
        migrations.AlterUniqueTogether(
            name="abilita_sbloccata",
            unique_together={("abilita", "sbloccata")},
        ),
        migrations.AlterUniqueTogether(
            name="abilita_punteggio",
            unique_together={("abilita", "punteggio")},
        ),
    ]
