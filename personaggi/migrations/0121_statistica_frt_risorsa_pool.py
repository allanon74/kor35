from django.db import migrations


def set_frt_pool(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    Statistica.objects.filter(sigla="FRT").update(is_risorsa_pool=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0120_risorse_statistiche_pool"),
    ]

    operations = [
        migrations.RunPython(set_frt_pool, noop),
    ]
