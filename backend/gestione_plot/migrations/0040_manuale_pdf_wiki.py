import uuid

from django.db import migrations, models
from django.utils import timezone


def crea_manuali_default(apps, schema_editor):
    ManualePdf = apps.get_model("gestione_plot", "ManualePdf")
    PaginaRegolamento = apps.get_model("gestione_plot", "PaginaRegolamento")
    now = timezone.now()

    defaults = [
        {
            "slug": "completo",
            "titolo": "Manuale Completo",
            "sottotitolo": "Tutte le regole pubblicate",
            "ordine": 0,
        },
        {
            "slug": "giocatore",
            "titolo": "Manuale del Giocatore",
            "sottotitolo": "Regole essenziali per chi gioca",
            "ordine": 10,
        },
        {
            "slug": "master",
            "titolo": "Manuale Master",
            "sottotitolo": "Regole e strumenti per narratori",
            "ordine": 20,
        },
    ]
    manuali = {}
    for spec in defaults:
        manuale, _ = ManualePdf.objects.get_or_create(
            slug=spec["slug"],
            defaults={
                "sync_id": uuid.uuid4(),
                "updated_at": now,
                "titolo": spec["titolo"],
                "sottotitolo": spec["sottotitolo"],
                "ordine": spec["ordine"],
                "attivo": True,
            },
        )
        manuali[spec["slug"]] = manuale

    pagine_pubbliche = PaginaRegolamento.objects.filter(
        public=True,
        visibile_solo_staff=False,
    ).exclude(contenuto="")
    for pagina in pagine_pubbliche.iterator():
        pagina.includi_in_pdf = True
        pagina.save(update_fields=["includi_in_pdf"])
        pagina.manuali_pdf.add(manuali["completo"])


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0039_evento_start_end_crediti_base"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualePdf",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("titolo", models.CharField(max_length=200)),
                ("sottotitolo", models.CharField(blank=True, max_length=300)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(default=True)),
                ("copertina", models.ImageField(blank=True, null=True, upload_to="wiki_manual_covers/")),
                ("ultimo_generato_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Manuale PDF wiki",
                "verbose_name_plural": "Manuali PDF wiki",
                "ordering": ["ordine", "titolo"],
            },
        ),
        migrations.AddField(
            model_name="paginaregolamento",
            name="includi_in_pdf",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la pagina può comparire nei manuali PDF selezionati (solo contenuto pubblico).",
                verbose_name="Includi nei manuali PDF",
            ),
        ),
        migrations.AddField(
            model_name="paginaregolamento",
            name="pdf_forza_nuova_pagina",
            field=models.BooleanField(
                default=False,
                help_text="Inizia sempre su una pagina nuova nel PDF.",
                verbose_name="PDF: forza nuova pagina",
            ),
        ),
        migrations.AddField(
            model_name="paginaregolamento",
            name="pdf_solo_indice",
            field=models.BooleanField(
                default=False,
                help_text="Compare nell'indice ma senza corpo capitolo (utile per hub di navigazione).",
                verbose_name="PDF: solo voce indice",
            ),
        ),
        migrations.AddField(
            model_name="paginaregolamento",
            name="pdf_titolo_capitolo",
            field=models.CharField(
                blank=True,
                help_text="Titolo alternativo nel manuale; vuoto = titolo pagina.",
                max_length=200,
                verbose_name="PDF: titolo capitolo",
            ),
        ),
        migrations.AddField(
            model_name="paginaregolamento",
            name="manuali_pdf",
            field=models.ManyToManyField(
                blank=True,
                related_name="pagine",
                to="gestione_plot.manualepdf",
                verbose_name="Manuali PDF",
            ),
        ),
        migrations.RunPython(crea_manuali_default, migrations.RunPython.noop),
    ]
