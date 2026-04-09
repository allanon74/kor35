from django.db import migrations


def cleanup_ain_trait_slots(apps, schema_editor):
    PersonaggioAbilita = apps.get_model("personaggi", "PersonaggioAbilita")

    # Slot archetipo: livelli 0/1 -> tieni la riga più recente
    archetipo_qs = (
        PersonaggioAbilita.objects.filter(
            abilita__is_tratto_aura=True,
            abilita__aura_riferimento__sigla="AIN",
            abilita__livello_riferimento__in=(0, 1),
        )
        .values_list("personaggio_id", flat=True)
        .distinct()
    )
    for personaggio_id in archetipo_qs:
        rows = PersonaggioAbilita.objects.filter(
            personaggio_id=personaggio_id,
            abilita__is_tratto_aura=True,
            abilita__aura_riferimento__sigla="AIN",
            abilita__livello_riferimento__in=(0, 1),
        ).order_by("-updated_at", "-id")
        keep = rows.first()
        if keep:
            rows.exclude(pk=keep.pk).delete()

    # Slot forma: livello 2 -> tieni la riga più recente
    forma_qs = (
        PersonaggioAbilita.objects.filter(
            abilita__is_tratto_aura=True,
            abilita__aura_riferimento__sigla="AIN",
            abilita__livello_riferimento=2,
        )
        .values_list("personaggio_id", flat=True)
        .distinct()
    )
    for personaggio_id in forma_qs:
        rows = PersonaggioAbilita.objects.filter(
            personaggio_id=personaggio_id,
            abilita__is_tratto_aura=True,
            abilita__aura_riferimento__sigla="AIN",
            abilita__livello_riferimento=2,
        ).order_by("-updated_at", "-id")
        keep = rows.first()
        if keep:
            rows.exclude(pk=keep.pk).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("personaggi", "0113_sync_join_tables_unique"),
    ]

    operations = [
        migrations.RunPython(cleanup_ain_trait_slots, noop_reverse),
    ]

