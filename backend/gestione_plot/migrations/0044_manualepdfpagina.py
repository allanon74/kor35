import uuid

from django.db import migrations, models
import django.db.models.deletion


def migra_m2m_verso_through(apps, schema_editor):
    ManualePdf = apps.get_model("gestione_plot", "ManualePdf")
    PaginaRegolamento = apps.get_model("gestione_plot", "PaginaRegolamento")
    ManualePdfPagina = apps.get_model("gestione_plot", "ManualePdfPagina")

    through_old = "gestione_plot_paginaregolamento_manuali_pdf"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT paginaregolamento_id, manualepdf_id
            FROM {through_old}
            ORDER BY manualepdf_id, paginaregolamento_id
            """
        )
        rows = cursor.fetchall()

    ordine_per_manuale: dict[int, int] = {}
    manuali = {m.pk: m for m in ManualePdf.objects.all()}
    pagine = {p.pk: p for p in PaginaRegolamento.objects.all()}

    for pagina_id, manuale_id in rows:
        if manuale_id not in manuali or pagina_id not in pagine:
            continue
        ordine_per_manuale[manuale_id] = ordine_per_manuale.get(manuale_id, 0) + 10
        ManualePdfPagina.objects.create(
            id=uuid.uuid4(),
            sync_id=uuid.uuid4(),
            manuale_id=manuale_id,
            pagina_id=pagina_id,
            ordine=ordine_per_manuale[manuale_id],
            inizio_capitolo=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0043_questvista_negozio_mercante"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualePdfPagina",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0, verbose_name="Ordine nel manuale")),
                (
                    "inizio_capitolo",
                    models.BooleanField(
                        default=True,
                        help_text="Se attivo apre un capitolo numerato; altrimenti sottosezione con intestazione minore.",
                        verbose_name="Inizio capitolo PDF",
                    ),
                ),
                (
                    "manuale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pagine_manuale",
                        to="gestione_plot.manualepdf",
                    ),
                ),
                (
                    "pagina",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="manuali_manuale",
                        to="gestione_plot.paginaregolamento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pagina in manuale PDF",
                "verbose_name_plural": "Pagine in manuali PDF",
                "ordering": ["ordine", "pagina__titolo"],
            },
        ),
        migrations.AddConstraint(
            model_name="manualepdfpagina",
            constraint=models.UniqueConstraint(
                fields=("manuale", "pagina"),
                name="uniq_manuale_pagina",
            ),
        ),
        migrations.RunPython(migra_m2m_verso_through, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="paginaregolamento",
            name="manuali_pdf",
        ),
        migrations.AddField(
            model_name="paginaregolamento",
            name="manuali_pdf",
            field=models.ManyToManyField(
                blank=True,
                related_name="pagine",
                through="gestione_plot.ManualePdfPagina",
                to="gestione_plot.manualepdf",
                verbose_name="Manuali PDF",
            ),
        ),
    ]
