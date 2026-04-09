# Generated manually: dedupe righe duplicate (sync_id diversi, stessa coppia personaggio+abilita)
# poi vincolo UNIQUE(personaggio_id, abilita_id).

from django.db import migrations
from django.db.models import Count


def dedupe_personaggio_abilita(apps, schema_editor):
    PersonaggioAbilita = apps.get_model("personaggi", "PersonaggioAbilita")
    dup_keys = (
        PersonaggioAbilita.objects.values("personaggio_id", "abilita_id")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
    )
    for row in dup_keys:
        qs = PersonaggioAbilita.objects.filter(
            personaggio_id=row["personaggio_id"],
            abilita_id=row["abilita_id"],
        ).order_by("-updated_at", "-id")
        keep_pk = qs.values_list("id", flat=True).first()
        if keep_pk is None:
            continue
        PersonaggioAbilita.objects.filter(
            personaggio_id=row["personaggio_id"],
            abilita_id=row["abilita_id"],
        ).exclude(pk=keep_pk).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0111_personaggio_sync_fields"),
    ]

    operations = [
        migrations.RunPython(dedupe_personaggio_abilita, noop_reverse),
        migrations.AlterUniqueTogether(
            name="personaggioabilita",
            unique_together={("personaggio", "abilita")},
        ),
        migrations.AlterModelOptions(
            name="personaggioabilita",
            options={
                "verbose_name": "Personaggio - Abilità",
                "verbose_name_plural": "Personaggio - Abilità",
            },
        ),
    ]
