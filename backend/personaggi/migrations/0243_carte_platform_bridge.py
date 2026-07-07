import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0242_carta_errata_publish_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CarteGiocoDefinizione",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.CharField(db_index=True, help_text="Identificatore stabile per URL/API future (es. sette-elegie).", max_length=80)),
                ("nome", models.CharField(help_text="Nome mostrato del gioco di carte.", max_length=120)),
                ("descrizione", models.TextField(blank=True, default="")),
                (
                    "platform_version",
                    models.CharField(
                        default="1.0.0",
                        help_text="Versione contratti JSON (playable_spec, duel_state, …).",
                        max_length=16,
                    ),
                ),
                (
                    "studio_abilitato",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="Card Studio attivo per questa campagna.",
                    ),
                ),
                (
                    "arena_abilitata",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="Card Arena attivo per questa campagna.",
                    ),
                ),
                (
                    "mse_game_name",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Nome package MSE game per export (opzionale).",
                        max_length=120,
                    ),
                ),
                (
                    "meta",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Metadati estensibili (licenze, autori, note bridge).",
                    ),
                ),
                (
                    "campagna",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carte_gioco_definizione",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Definizione gioco carte",
                "verbose_name_plural": "Definizioni gioco carte",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="CarteStudioTemplate",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.CharField(db_index=True, max_length=80)),
                ("nome", models.CharField(max_length=120)),
                (
                    "mse_style_riferimento",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Path o identificatore package .mse-style importato.",
                        max_length=200,
                    ),
                ),
                (
                    "layout_spec",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Dimensioni carta, DPI, layer, font (studio_layout_spec_v1).",
                    ),
                ),
                (
                    "campi_schema",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Mappatura campi MSE ↔ campi CartaCollezionabile (studio_field_map_v1).",
                    ),
                ),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="carte_studio_templates",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "gioco_definizione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="studio_templates",
                        to="personaggi.cartegiocodefinizione",
                    ),
                ),
            ],
            options={
                "verbose_name": "Template Card Studio",
                "verbose_name_plural": "Template Card Studio",
                "ordering": ["ordine", "nome"],
                "unique_together": {("gioco_definizione", "slug")},
            },
        ),
        migrations.CreateModel(
            name="CarteArenaRuleset",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ruleset_version",
                    models.CharField(
                        default="1.0.0",
                        help_text="Versione schema arena_ruleset_spec_v1.",
                        max_length=16,
                    ),
                ),
                (
                    "zones_spec",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Zone tavolo (mano, campo, reliquiario, …).",
                    ),
                ),
                (
                    "win_conditions",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Condizioni vittoria/sconfitta/pareggio.",
                    ),
                ),
                (
                    "formato_mazzo",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Limiti mazzo (es. max 15, duplicati, leader).",
                    ),
                ),
                (
                    "effect_engine_version",
                    models.CharField(
                        default="v1",
                        help_text="Versione EffectScript usata in Arena.",
                        max_length=8,
                    ),
                ),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="carte_arena_ruleset",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "gioco_definizione",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="arena_ruleset",
                        to="personaggi.cartegiocodefinizione",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ruleset Card Arena",
                "verbose_name_plural": "Ruleset Card Arena",
            },
        ),
        migrations.CreateModel(
            name="CartePlatformExchangeJob",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("import_mse_set", "Import set MSE"),
                            ("export_mse_set", "Export set MSE"),
                            ("import_mse_style", "Import style MSE"),
                            ("export_mse_style", "Export style MSE"),
                            ("export_playable", "Export playable spec Arena"),
                        ],
                        db_index=True,
                        max_length=24,
                    ),
                ),
                (
                    "stato",
                    models.CharField(
                        choices=[
                            ("pending", "In attesa"),
                            ("running", "In esecuzione"),
                            ("done", "Completato"),
                            ("failed", "Fallito"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=12,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("risultato", models.JSONField(blank=True, default=dict)),
                ("errore", models.TextField(blank=True, default="")),
                ("completato_at", models.DateTimeField(blank=True, null=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carte_platform_exchange_jobs",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "gioco_definizione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exchange_jobs",
                        to="personaggi.cartegiocodefinizione",
                    ),
                ),
                (
                    "richiesto_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="carte_platform_exchange_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Job scambio piattaforma carte",
                "verbose_name_plural": "Job scambio piattaforma carte",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CartePlatformGiocatore",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("display_name", models.CharField(blank=True, default="", max_length=80)),
                (
                    "external_player_ref",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="UUID stabile per client Arena standalone (futuro).",
                        null=True,
                    ),
                ),
                ("meta", models.JSONField(blank=True, default=dict)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carte_platform_giocatori",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "gioco_definizione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="giocatori",
                        to="personaggi.cartegiocodefinizione",
                    ),
                ),
                (
                    "personaggio",
                    models.OneToOneField(
                        blank=True,
                        help_text="Profilo KOR35: una riga per personaggio PG.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carte_platform_giocatore",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="carte_platform_giocatori",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Giocatore piattaforma carte",
                "verbose_name_plural": "Giocatori piattaforma carte",
            },
        ),
        migrations.AddConstraint(
            model_name="carteplatformgiocatore",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", False)),
                fields=("campagna", "user"),
                name="personaggi_cpg_campagna_user_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="carteplatformgiocatore",
            constraint=models.UniqueConstraint(
                condition=models.Q(("personaggio__isnull", False)),
                fields=("personaggio",),
                name="personaggi_cpg_personaggio_uniq",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="gioco_definizione",
            field=models.ForeignKey(
                blank=True,
                help_text="Definizione gioco piattaforma (Card Studio / Arena).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="espansioni",
                to="personaggi.cartegiocodefinizione",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="mse_set_riferimento",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Identificatore o path package .mse-set collegato.",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="studio_set_spec",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Metadati set Card Studio / MSE (studio_set_spec_v1).",
            ),
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="arena_playable_spec",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Snapshot normalizzato per Card Arena (playable_card_spec_v1).",
            ),
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="mse_campi",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Mappa campi raw MSE importati (round-trip export).",
            ),
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="studio_carta_spec",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Campi layout/stampa extra (studio_card_spec_v1).",
            ),
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="studio_template",
            field=models.ForeignKey(
                blank=True,
                help_text="Template Card Studio per rendering stampa.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="carte",
                to="personaggi.cartestudiotemplate",
            ),
        ),
        migrations.AddField(
            model_name="keywordcarta",
            name="mse_export_mode",
            field=models.CharField(
                choices=[
                    ("kor35", "Solo KOR35"),
                    ("mse_compat", "Compatibile MSE"),
                    ("both", "KOR35 + MSE"),
                ],
                default="kor35",
                help_text="Modalità export verso Card Studio / MSE.",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="keywordcarta",
            name="mse_match_pattern",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Pattern match MSE per export keyword (opzionale).",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="keywordcarta",
            name="mse_reminder_template",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Template reminder MSE; placeholder come nel nome.",
            ),
        ),
        migrations.AddField(
            model_name="mazzoduello",
            name="arena_deck_spec",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Metadati mazzo per Card Arena (arena_deck_spec_v1).",
            ),
        ),
        migrations.AddField(
            model_name="mazzoduello",
            name="formato_codice",
            field=models.CharField(
                db_index=True,
                default="standard_15",
                help_text="Codice formato Arena (es. standard_15, sealed).",
                max_length=40,
            ),
        ),
    ]
