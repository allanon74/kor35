from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0117_abilita_camaleontica"),
    ]

    operations = [
        migrations.CreateModel(
            name="abilita_punteggio_dipendente",
            fields=[
                (
                    "id",
                    models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo"),
                ),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("incremento", models.IntegerField(default=1)),
                ("ogni_x", models.IntegerField(default=1)),
                (
                    "abilita",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="punteggi_dipendenti",
                        to="personaggi.abilita",
                    ),
                ),
                (
                    "punteggio_sorgente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abilita_punteggio_sorgente_rel",
                        to="personaggi.punteggio",
                    ),
                ),
                (
                    "punteggio_target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abilita_punteggio_target_rel",
                        to="personaggi.punteggio",
                    ),
                ),
            ],
            options={
                "unique_together": {("abilita", "punteggio_target", "punteggio_sorgente")},
            },
        ),
    ]
