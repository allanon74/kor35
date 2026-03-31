from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0126_era_abbreviazione_personaggio_prefettura_esterna"),
    ]

    operations = [
        migrations.CreateModel(
            name="Regione",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(blank=True, db_index=True, editable=False, null=True, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120, unique=True)),
                ("sigla", models.CharField(blank=True, default="", max_length=20)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attiva", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Regione",
                "verbose_name_plural": "Regioni",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.AddField(
            model_name="prefettura",
            name="regione",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="prefetture", to="personaggi.regione"),
        ),
        migrations.CreateModel(
            name="RegioneAbilita",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(blank=True, db_index=True, editable=False, null=True, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_default", models.BooleanField(default=False, help_text="Se attivo, l'abilità viene aggiunta quando il personaggio seleziona una prefettura di questa regione.", verbose_name="Assegna in automatico al personaggio")),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("abilita", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="abilita_regione", to="personaggi.abilita")),
                ("regione", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="regioni_abilita", to="personaggi.regione")),
            ],
            options={
                "verbose_name": "Abilità Regione",
                "verbose_name_plural": "Abilità Regioni",
                "ordering": ["ordine", "abilita__nome"],
                "unique_together": {("regione", "abilita")},
            },
        ),
        migrations.AddField(
            model_name="regione",
            name="abilita",
            field=models.ManyToManyField(blank=True, related_name="regioni_collegate", through="personaggi.RegioneAbilita", to="personaggi.abilita"),
        ),
    ]
