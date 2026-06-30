import uuid

import django.db.models.deletion
from django.db import migrations, models


def backfill_espansioni_da_set_collezione(apps, schema_editor):
    EspansioneCarte = apps.get_model("personaggi", "EspansioneCarte")
    BustinaCarte = apps.get_model("personaggi", "BustinaCarte")
    CartaCollezionabile = apps.get_model("personaggi", "CartaCollezionabile")

    cache: dict[tuple, uuid.UUID] = {}

    def get_or_create_espansione(campagna_id, slug: str, nome: str | None = None):
        slug = (slug or "generica").strip()[:80]
        key = (campagna_id, slug)
        if key in cache:
            return cache[key]
        label = nome or slug.replace("-", " ").title()
        esp, _ = EspansioneCarte.objects.get_or_create(
            campagna_id=campagna_id,
            slug=slug,
            defaults={"nome": label, "ordine": 0, "attiva": True},
        )
        cache[key] = esp.id
        return esp.id

    for bustina in BustinaCarte.objects.exclude(set_collezione=""):
        esp_id = get_or_create_espansione(
            bustina.campagna_id,
            bustina.set_collezione,
            bustina.set_collezione,
        )
        BustinaCarte.objects.filter(pk=bustina.pk).update(espansione_id=esp_id)

    for carta in CartaCollezionabile.objects.exclude(set_collezione=""):
        esp_id = get_or_create_espansione(
            carta.campagna_id,
            carta.set_collezione,
            carta.set_collezione,
        )
        CartaCollezionabile.objects.filter(pk=carta.pk).update(espansione_id=esp_id)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0226_carte_accesso_modo_bustina_qr"),
    ]

    operations = [
        migrations.CreateModel(
            name="EspansioneCarte",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                (
                    "slug",
                    models.CharField(
                        db_index=True,
                        help_text="Identificatore univoco per campagna, es. caduta-del-consiglio",
                        max_length=80,
                    ),
                ),
                ("descrizione", models.TextField(blank=True, default="")),
                ("immagine", models.ImageField(blank=True, null=True, upload_to="carte_collezionabili/espansioni/")),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                ("attiva", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="espansioni_carte",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Espansione carte",
                "verbose_name_plural": "Espansioni carte",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="espansione",
            field=models.ForeignKey(
                blank=True,
                help_text="Espansione di appartenenza.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="carte",
                to="personaggi.espansionecarte",
            ),
        ),
        migrations.AddField(
            model_name="bustinacarte",
            name="espansione",
            field=models.ForeignKey(
                blank=True,
                help_text="Espansione di appartenenza (bustine raggruppate per collezione).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bustine",
                to="personaggi.espansionecarte",
            ),
        ),
        migrations.AlterField(
            model_name="cartacollezionabile",
            name="set_collezione",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Deprecato: usare espansione. Slug set narrativo legacy.",
                max_length=80,
            ),
        ),
        migrations.AlterField(
            model_name="bustinacarte",
            name="set_collezione",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Deprecato: usare espansione. Se valorizzato, limita il pool legacy.",
                max_length=80,
            ),
        ),
        migrations.AlterModelOptions(
            name="bustinacarte",
            options={"ordering": ["espansione__ordine", "ordine", "nome"], "verbose_name": "Bustina carte", "verbose_name_plural": "Bustine carte"},
        ),
        migrations.AlterModelOptions(
            name="cartacollezionabile",
            options={
                "ordering": ["espansione__ordine", "espansione__nome", "ordine_set", "nome"],
                "verbose_name": "Carta collezionabile",
                "verbose_name_plural": "Carte collezionabili",
            },
        ),
        migrations.AddIndex(
            model_name="cartacollezionabile",
            index=models.Index(fields=["campagna", "espansione"], name="personaggi__campagn_esp_idx"),
        ),
        migrations.AddIndex(
            model_name="espansionecarte",
            index=models.Index(fields=["campagna", "attiva"], name="personaggi__campagn_esp_att_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="espansionecarte",
            unique_together={("campagna", "slug")},
        ),
        migrations.RunPython(backfill_espansioni_da_set_collezione, migrations.RunPython.noop),
    ]
