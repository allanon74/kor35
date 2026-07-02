import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gestione_plot", "0045_evento_logistiche_coordinate"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventoVocePortare",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("descrizione", models.CharField(max_length=255)),
                ("ordine", models.PositiveIntegerField(default=0)),
                (
                    "a_posto",
                    models.BooleanField(
                        default=False,
                        help_text="Segna quando la voce è pronta / portata.",
                        verbose_name="A posto",
                    ),
                ),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_portare",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "portatore",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="eventi_voci_portare",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Master incaricato",
                    ),
                ),
            ],
            options={
                "verbose_name": "Voce da portare (evento)",
                "verbose_name_plural": "Voci da portare (evento)",
                "ordering": ["ordine", "descrizione"],
            },
        ),
    ]
