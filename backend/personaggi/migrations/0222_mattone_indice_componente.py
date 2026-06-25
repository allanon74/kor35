from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0221_statisticacontaineritem_nascondi_se_due"),
    ]

    operations = [
        migrations.AddField(
            model_name="mattone",
            name="indice_componente",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Indice 0-9 per mattoni-componente nave (aura Componenti). Null per mattoni tessitura.",
                null=True,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="mattone",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="mattone",
            constraint=models.UniqueConstraint(
                condition=models.Q(("indice_componente__isnull", True)),
                fields=("aura", "caratteristica_associata"),
                name="uniq_mattone_aura_caratt_standard",
            ),
        ),
        migrations.AddConstraint(
            model_name="mattone",
            constraint=models.UniqueConstraint(
                condition=models.Q(("indice_componente__isnull", False)),
                fields=("aura", "caratteristica_associata", "indice_componente"),
                name="uniq_mattone_componente_nave",
            ),
        ),
    ]
