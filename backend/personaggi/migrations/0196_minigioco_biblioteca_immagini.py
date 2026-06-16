from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0195_minigioco_regole_condizionali"),
    ]

    operations = [
        migrations.CreateModel(
            name="MinigiocoBibliotecaImmagine",
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
                ("immagine", models.ImageField(upload_to="minigioco_biblioteca/%Y/%m/")),
                ("titolo", models.CharField(blank=True, default="", max_length=200)),
                ("autore", models.CharField(blank=True, default="", max_length=200)),
                ("licenza", models.CharField(blank=True, default="", max_length=32)),
                ("fonte", models.CharField(default="openverse", max_length=32)),
                ("source_id", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("source_page_url", models.URLField(blank=True, default="", max_length=500)),
                ("search_query", models.CharField(blank=True, default="", max_length=120)),
                ("aggiunta_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Immagine biblioteca minigioco",
                "verbose_name_plural": "Immagini biblioteca minigioco",
                "ordering": ["-aggiunta_at"],
            },
        ),
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="usa_biblioteca_se_vuota",
            field=models.BooleanField(
                default=True,
                help_text="Se non c'è immagine dedicata sul QR, usa un'estrazione casuale dalla libreria staff.",
            ),
        ),
        migrations.AddField(
            model_name="minigiocoqrsession",
            name="biblioteca_immagine",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="sessioni",
                to="personaggi.minigiocobibliotecaimmagine",
            ),
        ),
    ]
