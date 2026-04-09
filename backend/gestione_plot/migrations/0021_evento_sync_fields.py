import uuid
from django.db import migrations, models
from django.utils import timezone


SYNC_MODELS = [
    "mostrotemplate", "attaccotemplate", "evento", "giornoevento", "quest", "questmostro",
    "pngassegnato", "questvista", "staffoffgame", "questfase", "questtask",
    "paginaregolamento", "wikiimmagine", "wikitierwidget", "wikimattoniwidget",
    "wikibuttonwidget", "wikibutton", "configurazionesito", "linksocial",
]


def populate_sync_fields(apps, schema_editor):
    now = timezone.now()
    for model_name in SYNC_MODELS:
        Model = apps.get_model("gestione_plot", model_name)
        for row in Model.objects.filter(sync_id__isnull=True).only("id", "sync_id", "updated_at"):
            row.sync_id = uuid.uuid4()
            if row.updated_at is None:
                row.updated_at = now
            row.save(update_fields=["sync_id", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0020_merge_0018_0019"),
    ]

    operations = [
        *[
            migrations.AddField(
                model_name=model_name,
                name="sync_id",
                field=models.UUIDField(blank=True, editable=False, null=True),
            )
            for model_name in SYNC_MODELS
        ],
        *[
            migrations.AddField(
                model_name=model_name,
                name="updated_at",
                field=models.DateTimeField(auto_now=True, null=True),
            )
            for model_name in SYNC_MODELS
        ],
        migrations.RunPython(populate_sync_fields, migrations.RunPython.noop),
        *[
            migrations.AlterField(
                model_name=model_name,
                name="sync_id",
                field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
            )
            for model_name in SYNC_MODELS
        ],
        *[
            migrations.AlterField(
                model_name=model_name,
                name="updated_at",
                field=models.DateTimeField(auto_now=True),
            )
            for model_name in SYNC_MODELS
        ],
    ]
