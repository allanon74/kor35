# Mercante come effetto pool, pesi difficoltà minigioco, archivio documenti, manifesto.non_salvabile

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0288_random_qr_pool_cooldown"),
    ]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="non_salvabile",
            field=models.BooleanField(
                default=False,
                help_text="Se True, il giocatore non può salvare questo manifesto nell'archivio Serie e testi.",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpool",
            name="minigioco_pesi_difficolta",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Pesi relativi per difficoltà 1–4 del minigioco a monte, es. '
                    '{"1":20,"2":20,"3":50,"4":10} oppure {"1":2,"2":2,"3":5,"4":1}. '
                    "Vuoto/tutti zero = usa minigioco_difficolta."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="randomqrpool",
            name="minigioco_difficolta",
            field=models.PositiveSmallIntegerField(
                default=4,
                help_text="Fallback legacy se i pesi difficoltà sono tutti zero.",
            ),
        ),
        migrations.AlterField(
            model_name="randomqrpooleffect",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("testo", "Testo"),
                    ("nodo", "Nodo"),
                    ("trappola", "Trappola"),
                    ("serie", "Serie"),
                    ("manifesto", "Manifesto"),
                    ("oggetto_base", "Oggetto (listino)"),
                    ("da_infusione", "Materia/Mod (da Infusione)"),
                    ("tessitura", "Tessitura"),
                    ("infusione", "Infusione (ricetta)"),
                    ("cerimoniale", "Cerimoniale"),
                    ("attivata", "Attivata"),
                    ("negozio_mercante", "Negozio mercante"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="randomqrpooleffect",
            name="negozio_mercante",
            field=models.ForeignKey(
                blank=True,
                help_text="Effetto: apre il listino del negozio mercante scelto.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_effetti",
                to="personaggi.negoziomercante",
            ),
        ),
        migrations.CreateModel(
            name="DocumentoArchiviato",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tipo",
                    models.CharField(
                        choices=[("manifesto", "Manifesto"), ("testo", "Testo")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("titolo", models.CharField(max_length=200)),
                ("testo", models.TextField(blank=True, default="")),
                (
                    "testo_condizionato",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Snapshot del testo condizionale visibile al momento del salvataggio.",
                    ),
                ),
                ("immagine_path", models.CharField(blank=True, default="", max_length=500)),
                ("audio_path", models.CharField(blank=True, default="", max_length=500)),
                ("video_path", models.CharField(blank=True, default="", max_length=500)),
                ("salvato_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "manifesto",
                    models.ForeignKey(
                        blank=True,
                        help_text="Riferimento opzionale al manifesto originale (il contenuto è comunque in snapshot).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="documenti_archiviati",
                        to="personaggi.manifesto",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documenti_archiviati",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Documento archiviato",
                "verbose_name_plural": "Documenti archiviati",
                "ordering": ["-salvato_at", "-created_at"],
                "indexes": [
                    models.Index(
                        fields=["personaggio", "tipo"],
                        name="personaggi__persona_docarch_idx",
                    ),
                ],
            },
        ),
    ]
