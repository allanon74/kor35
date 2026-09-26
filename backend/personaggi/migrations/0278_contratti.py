import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0054_missioneevento_attiva"),
        ("social", "0015_rubricaarticoloimmagine_layout"),
        ("personaggi", "0277_manifesto_audio_video"),
    ]

    operations = [
        migrations.AddField(
            model_name="carriera",
            name="sottoscrive_contratti",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, i membri possono proporre i modelli di contratto di questa Korp.",
                verbose_name="Sottoscrive contratti",
            ),
        ),
        migrations.AddField(
            model_name="carriera",
            name="slot_contratto_base",
            field=models.IntegerField(
                default=3,
                help_text="Slot del proponente all'ingresso, prima del bonus carica e della statistica SCT. Vale solo se la Korp sottoscrive.",
                verbose_name="Slot contratto di base",
            ),
        ),
        migrations.AddField(
            model_name="carica",
            name="bonus_slot_contratto",
            field=models.IntegerField(
                default=0,
                help_text="Si somma agli slot di base della Korp. 0 sul grado d'ingresso: nessun +1 automatico. Può essere negativo.",
                verbose_name="Bonus slot di contratto",
            ),
        ),
        migrations.CreateModel(
            name="ModelloContratto",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=160)),
                ("attivo", models.BooleanField(default=True)),
                ("chiave_esclusivita", models.CharField(blank=True, default="", max_length=64)),
                ("durata_modo", models.CharField(choices=[("GIORNI", "Giorni reali"), ("FINE_EVENTO", "Fine evento")], default="GIORNI", max_length=16)),
                ("durata_giorni", models.PositiveIntegerField(default=90)),
                ("testo", models.TextField(blank=True, default="")),
                ("campagna", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="modelli_contratto", to="personaggi.campagna")),
                ("korp", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="modelli_contratto", to="personaggi.carriera")),
            ],
            options={"verbose_name": "Modello contratto", "verbose_name_plural": "Modelli contratto", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="ParametroModello",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("chiave", models.SlugField(max_length=64)),
                ("etichetta", models.CharField(max_length=160)),
                ("tipo", models.CharField(choices=[("INTERO", "Intero"), ("DECIMALE", "Decimale"), ("PERCENTUALE", "Percentuale"), ("TESTO", "Testo"), ("SCELTA", "Scelta"), ("PERSONAGGIO", "Personaggio")], default="DECIMALE", max_length=16)),
                ("chi_compila", models.CharField(choices=[("STAFF", "Staff"), ("PROPONENTE", "Proponente")], default="STAFF", max_length=16)),
                ("valore", models.JSONField(blank=True, null=True)),
                ("vincoli", models.JSONField(blank=True, default=dict)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("modello", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parametri", to="personaggi.modellocontratto")),
            ],
            options={"verbose_name": "Parametro modello contratto", "verbose_name_plural": "Parametri modello contratto", "ordering": ["ordine", "chiave"], "unique_together": {("modello", "chiave")}},
        ),
        migrations.CreateModel(
            name="VoceModello",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tipo", models.CharField(choices=[("CLAUSOLA", "Clausola"), ("COMPENSO", "Compenso")], default="CLAUSOLA", max_length=16)),
                ("nome", models.CharField(max_length=160)),
                ("testo", models.TextField(blank=True, default="")),
                ("obbligatoria", models.BooleanField(default=False)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("modello", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="voci", to="personaggi.modellocontratto")),
            ],
            options={"verbose_name": "Voce modello contratto", "verbose_name_plural": "Voci modello contratto", "ordering": ["ordine", "nome"]},
        ),
        migrations.CreateModel(
            name="EffettoModello",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("codice", models.CharField(max_length=40)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("modello", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="effetti", to="personaggi.modellocontratto")),
                ("voce", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="effetti", to="personaggi.vocemodello")),
            ],
            options={"verbose_name": "Effetto modello contratto", "verbose_name_plural": "Effetti modello contratto", "ordering": ["ordine", "codice"]},
        ),
        migrations.CreateModel(
            name="Contratto",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("stato", models.CharField(choices=[("IN_ATTESA", "In attesa di firma"), ("STIPULATO", "Stipulato"), ("SCADUTO", "Scaduto"), ("RIFIUTATO", "Rifiutato"), ("RISOLTO", "Risolto"), ("ANNULLATO", "Annullato")], db_index=True, default="IN_ATTESA", max_length=16)),
                ("scadenza", models.DateTimeField()),
                ("stipulata_at", models.DateTimeField(blank=True, null=True)),
                ("snapshot", models.JSONField(blank=True, default=dict)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("campagna", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contratti", to="personaggi.campagna")),
                ("cliente", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="contratti_sottoscritti", to="personaggi.personaggio")),
                ("modello", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contratti", to="personaggi.modellocontratto")),
                ("proponente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contratti_proposti", to="personaggi.personaggio")),
                ("qr_code", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="contratto", to="personaggi.qrcode")),
            ],
            options={"verbose_name": "Contratto", "verbose_name_plural": "Contratti", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ContrattoAdempimento",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("codice_effetto", models.CharField(max_length=40)),
                ("fonte", models.CharField(max_length=180)),
                ("stato", models.CharField(choices=[("APPLICATO", "Applicato"), ("IN_ATTESA", "In attesa di conferma"), ("DEBITO", "Debito"), ("ANNULLATO", "Annullato")], default="APPLICATO", max_length=16)),
                ("dovuto", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("versato", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("importo_cliente", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("importo_proponente", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("note", models.CharField(blank=True, default="", max_length=240)),
                ("dettaglio", models.JSONField(blank=True, default=dict)),
                ("contratto", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="adempimenti", to="personaggi.contratto")),
                ("evento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="adempimenti_contratto", to="gestione_plot.evento")),
            ],
            options={"verbose_name": "Adempimento contratto", "verbose_name_plural": "Adempimenti contratto", "ordering": ["-created_at"], "unique_together": {("contratto", "fonte")}},
        ),
        migrations.CreateModel(
            name="ContrattoPost",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("contratto", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="post_associati", to="personaggi.contratto")),
                ("evento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contratti_post", to="gestione_plot.evento")),
                ("post", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="contratto_associato", to="social.socialpost")),
            ],
            options={"verbose_name": "Post associato a contratto", "verbose_name_plural": "Post associati a contratto"},
        ),
        migrations.CreateModel(
            name="ContrattoServizio",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("unita", models.CharField(max_length=8)),
                ("quantita", models.DecimalField(decimal_places=2, max_digits=8)),
                ("note", models.CharField(blank=True, default="", max_length=200)),
                ("contratto", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="servizi", to="personaggi.contratto")),
                ("evento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="servizi_contratto", to="gestione_plot.evento")),
            ],
            options={"verbose_name": "Servizio contratto", "verbose_name_plural": "Servizi contratto", "ordering": ["-created_at"]},
        ),
    ]
