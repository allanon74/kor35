import django.db.models.deletion
import personaggi.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("personaggi", "0156_rename_avista_ptr_innescotimer_a_vista_ptr_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="era",
            name="difetto_interpretativo_testo",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="era",
            name="difetto_interpretativo_titolo",
            field=models.CharField(blank=True, default="", max_length=140),
        ),
        migrations.CreateModel(
            name="Nodo",
            fields=[
                (
                    "a_vista_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.a_vista",
                    ),
                ),
                ("tipo_nodo", models.CharField(choices=[("MIN", "Nodo minore"), ("MAG", "Nodo maggiore")], db_index=True, default="MIN", max_length=3)),
                ("disponibile_dal", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("ultima_scansione_at", models.DateTimeField(blank=True, null=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="nodi",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            bases=("personaggi.a_vista",),
            options={
                "verbose_name": "Nodo (QR)",
                "verbose_name_plural": "Nodi (QR)",
            },
        ),
    ]
