from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0196_minigioco_biblioteca_immagini"),
    ]

    operations = [
        migrations.CreateModel(
            name="MinigiocoOpenverseConfig",
            fields=[
                (
                    "singleton_id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("client_id", models.CharField(blank=True, default="", max_length=128)),
                ("client_secret", models.CharField(blank=True, default="", max_length=512)),
                ("app_name", models.CharField(blank=True, default="", max_length=120)),
                ("app_description", models.TextField(blank=True, default="")),
                ("contact_email", models.EmailField(blank=True, default="", max_length=254)),
                ("api_message", models.CharField(blank=True, default="", max_length=500)),
                ("registered_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Config Openverse minigioco",
                "verbose_name_plural": "Config Openverse minigioco",
            },
        ),
    ]
