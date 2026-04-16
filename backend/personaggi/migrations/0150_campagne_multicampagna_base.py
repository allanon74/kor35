from django.db import migrations, models
import django.db.models.deletion
import uuid
import personaggi.models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0145_arcanassoidentity_local_password_configured"),
    ]

    operations = [
        migrations.CreateModel(
            name="Campagna",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("slug", models.SlugField(db_index=True, max_length=64, unique=True)),
                ("nome", models.CharField(max_length=120, unique=True)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("is_default", models.BooleanField(db_index=True, default=False)),
                ("is_base", models.BooleanField(db_index=True, default=False)),
                ("attiva", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Campagna",
                "verbose_name_plural": "Campagne",
                "ordering": ["-is_default", "nome"],
            },
        ),
        migrations.CreateModel(
            name="CampagnaFeaturePolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("feature_key", models.CharField(choices=[("abilita", "Abilita"), ("tessiture", "Tessiture"), ("infusioni", "Infusioni"), ("oggetti_base", "Oggetti Base"), ("cerimoniali", "Cerimoniali"), ("social", "Social")], db_index=True, max_length=32)),
                ("mode", models.CharField(choices=[("SHARED", "Condivisa con Kor35"), ("EXCLUSIVE", "Esclusiva campagna")], db_index=True, default="SHARED", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campagna", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feature_policies", to="personaggi.campagna")),
            ],
            options={
                "verbose_name": "Policy Feature Campagna",
                "verbose_name_plural": "Policy Feature Campagna",
            },
        ),
        migrations.CreateModel(
            name="CampagnaUtente",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("ruolo", models.CharField(choices=[("PLAYER", "Giocatore"), ("MASTER", "Master")], db_index=True, default="PLAYER", max_length=16)),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campagna", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="membri", to="personaggi.campagna")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="campagne_associazioni", to="auth.user")),
            ],
            options={
                "verbose_name": "Assegnazione Utente Campagna",
                "verbose_name_plural": "Assegnazioni Utente Campagna",
            },
        ),
        migrations.AddField(
            model_name="abilita",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="abilita", to="personaggi.campagna"),
        ),
        migrations.AddField(
            model_name="cerimoniale",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="cerimoniali", to="personaggi.campagna"),
        ),
        migrations.AddField(
            model_name="infusione",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="infusioni", to="personaggi.campagna"),
        ),
        migrations.AddField(
            model_name="messaggio",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="messaggi", to="personaggi.campagna"),
        ),
        migrations.AddField(
            model_name="oggettobase",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="oggetti_base", to="personaggi.campagna"),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="personaggi", to="personaggi.campagna"),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="campagna",
            field=models.ForeignKey(db_index=True, default=personaggi.models.get_default_campagna_id, on_delete=django.db.models.deletion.PROTECT, related_name="tessiture", to="personaggi.campagna"),
        ),
        migrations.AddConstraint(
            model_name="campagnafeaturepolicy",
            constraint=models.UniqueConstraint(fields=("campagna", "feature_key"), name="camp_feat_unique"),
        ),
        migrations.AddConstraint(
            model_name="campagnautente",
            constraint=models.UniqueConstraint(fields=("campagna", "user"), name="camp_user_unique"),
        ),
        migrations.AddIndex(
            model_name="campagnafeaturepolicy",
            index=models.Index(fields=["campagna", "feature_key"], name="camp_feat_idx"),
        ),
        migrations.AddIndex(
            model_name="campagnafeaturepolicy",
            index=models.Index(fields=["campagna", "mode"], name="camp_mode_idx"),
        ),
        migrations.AddIndex(
            model_name="campagnautente",
            index=models.Index(fields=["campagna", "user"], name="camp_user_idx"),
        ),
        migrations.AddIndex(
            model_name="campagnautente",
            index=models.Index(fields=["user", "ruolo"], name="user_role_idx"),
        ),
        migrations.AddIndex(
            model_name="campagnautente",
            index=models.Index(fields=["campagna", "ruolo"], name="camp_role_idx"),
        ),
    ]
