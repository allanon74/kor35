# Generated manually for sync tombstone propagation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0175_alter_punteggio_stat_durata_consumabili"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncTombstone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_label", models.CharField(db_index=True, max_length=120)),
                ("sync_id", models.UUIDField(db_index=True)),
                ("deleted_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "verbose_name": "Tombstone sync",
                "verbose_name_plural": "Tombstone sync",
            },
        ),
        migrations.AddConstraint(
            model_name="synctombstone",
            constraint=models.UniqueConstraint(
                fields=("model_label", "sync_id"),
                name="personaggi_synctombstone_model_sync_id_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="synctombstone",
            index=models.Index(fields=["deleted_at"], name="personaggi_synctomb_del_at_idx"),
        ),
    ]
