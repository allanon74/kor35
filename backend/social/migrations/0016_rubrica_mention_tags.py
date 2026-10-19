import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0261_notifica_preferenze"),
        ("social", "0015_rubricaarticoloimmagine_layout"),
    ]

    operations = [
        migrations.CreateModel(
            name="RubricaArticoloTag",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "articolo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tags",
                        to="social.rubricaarticolo",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tagged_in_rubrica_articoli",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tag articolo rubrica",
                "verbose_name_plural": "Tag articoli rubrica",
                "unique_together": {("articolo", "personaggio")},
            },
        ),
        migrations.CreateModel(
            name="RubricaArticoloCommentTag",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tags",
                        to="social.rubricaarticolocomment",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tagged_in_rubrica_commenti",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tag commento articolo rubrica",
                "verbose_name_plural": "Tag commenti articoli rubrica",
                "unique_together": {("comment", "personaggio")},
            },
        ),
    ]
