from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0124_statistica_container_dimensioni"),
    ]

    operations = [
        migrations.CreateModel(
            name="Era",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(blank=True, db_index=True, editable=False, null=True, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120, unique=True)),
                ("descrizione_breve", models.CharField(blank=True, default="", max_length=280)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attiva", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Era",
                "verbose_name_plural": "Ere",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.CreateModel(
            name="Prefettura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(blank=True, db_index=True, editable=False, null=True, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("era", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prefetture", to="personaggi.era")),
            ],
            options={
                "verbose_name": "Prefettura",
                "verbose_name_plural": "Prefetture",
                "ordering": ["era__ordine", "ordine", "nome"],
                "unique_together": {("era", "nome")},
            },
        ),
        migrations.CreateModel(
            name="EraAbilita",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(blank=True, db_index=True, editable=False, null=True, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_default", models.BooleanField(default=False, help_text="Se attivo, l'abilità viene aggiunta quando il personaggio seleziona questa era.", verbose_name="Assegna in automatico al personaggio")),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("abilita", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="abilita_era", to="personaggi.abilita")),
                ("era", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ere_abilita", to="personaggi.era")),
            ],
            options={
                "verbose_name": "Abilità Era",
                "verbose_name_plural": "Abilità Ere",
                "ordering": ["ordine", "abilita__nome"],
                "unique_together": {("era", "abilita")},
            },
        ),
        migrations.AddField(
            model_name="era",
            name="abilita",
            field=models.ManyToManyField(blank=True, related_name="ere_collegate", through="personaggi.EraAbilita", to="personaggi.abilita"),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="era",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="personaggi", to="personaggi.era"),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="prefettura",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="personaggi", to="personaggi.prefettura"),
        ),
        migrations.AddField(
            model_name="personaggioabilita",
            name="origine",
            field=models.CharField(choices=[("acquisto", "Acquisto"), ("era_default", "Era (default)")], default="acquisto", max_length=20),
        ),
    ]
