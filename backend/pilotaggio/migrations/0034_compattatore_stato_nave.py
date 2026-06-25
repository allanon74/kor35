from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0033_componenti_nave_stiva"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompattatoreStatoNave",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "singleton_id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "energia_accumulata",
                    models.FloatField(
                        default=0.0,
                        help_text="Energia accumulata; un'operazione consuma 9 unità.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stato compattatore nave",
                "verbose_name_plural": "Stato compattatore nave",
            },
        ),
    ]
