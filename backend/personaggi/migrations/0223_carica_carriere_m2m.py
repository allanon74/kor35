# Carica: un rank può appartenere a più carriere/KORP (dipartimenti).

from django.db import migrations, models


def copy_carriera_fk_to_m2m(apps, schema_editor):
    Carica = apps.get_model("personaggi", "Carica")
    for carica in Carica.objects.exclude(carriera_id__isnull=True).iterator():
        carica.carriere.add(carica.carriera_id)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0222_mattone_indice_componente"),
    ]

    operations = [
        migrations.AddField(
            model_name="carica",
            name="carriere",
            field=models.ManyToManyField(
                blank=True,
                help_text="Dipartimenti (carriere/KORP) in cui esiste questa carica militare.",
                related_name="cariche",
                to="personaggi.carriera",
            ),
        ),
        migrations.RunPython(copy_carriera_fk_to_m2m, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="carica",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="carica",
            name="carriera",
        ),
        migrations.AlterModelOptions(
            name="carica",
            options={
                "ordering": ["nome", "ordine", "id"],
                "verbose_name": "Carica",
                "verbose_name_plural": "Cariche",
            },
        ),
    ]
