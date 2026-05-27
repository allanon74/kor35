# Migrazione: unifica KORP in Carriera, promuove Tier T3 a professioni, Carica e membership uniche.

import uuid

from django.db import migrations, models
import django.db.models.deletion


def seed_tipi_carriera(apps, schema_editor):
    TipoCarriera = apps.get_model("personaggi", "TipoCarriera")
    for codice, nome, ordine in (
        ("korp", "KORP", 0),
        ("professione", "Professione", 1),
    ):
        TipoCarriera.objects.get_or_create(
            codice=codice,
            defaults={
                "id": uuid.uuid4(),
                "nome": nome,
                "ordine": ordine,
                "attivo": True,
            },
        )


def promote_korps_and_professioni(apps, schema_editor):
    connection = schema_editor.connection
    TipoCarriera = apps.get_model("personaggi", "TipoCarriera")

    tipo_korp = TipoCarriera.objects.get(codice="korp")
    tipo_prof = TipoCarriera.objects.get(codice="professione")

    korp_table = "personaggi_korp"
    carriera_table = "personaggi_carriera"
    segno_table = "personaggi_segnozodiacale"
    tier_table = "personaggi_tier"
    tables = set(connection.introspection.table_names())

    if korp_table in tables:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {carriera_table} (tier_ptr_id, tipo_carriera_id)
                SELECT k.tier_ptr_id, %s::uuid
                FROM {korp_table} k
                WHERE NOT EXISTS (
                    SELECT 1 FROM {carriera_table} c WHERE c.tier_ptr_id = k.tier_ptr_id
                )
                """,
                [str(tipo_korp.id)],
            )

    if tier_table in tables and segno_table in tables:
        korp_clause = ""
        if korp_table in tables:
            korp_clause = f"""
                  AND NOT EXISTS (
                      SELECT 1 FROM {korp_table} k WHERE k.tier_ptr_id = t.tabella_ptr_id
                  )"""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {carriera_table} (tier_ptr_id, tipo_carriera_id)
                SELECT t.tabella_ptr_id, %s::uuid
                FROM {tier_table} t
                WHERE t.tipo = 'T3'
                  AND NOT EXISTS (
                      SELECT 1 FROM {carriera_table} c WHERE c.tier_ptr_id = t.tabella_ptr_id
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM {segno_table} s WHERE s.tier_ptr_id = t.tabella_ptr_id
                  )
                  {korp_clause}
                """,
                [str(tipo_prof.id)],
            )


def migrate_cariche_from_legacy(apps, schema_editor):
    connection = schema_editor.connection
    carica = "personaggi_carica"
    tables = set(connection.introspection.table_names())
    for legacy, fk_col in (
        ("personaggi_caricakorp", "korp_id"),
        ("personaggi_caricacarriera", "carriera_id"),
    ):
        if legacy not in tables:
            continue
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {carica} (id, sync_id, updated_at, nome, bonus_stipendio_evento, ordine, attiva, carriera_id)
                SELECT id, sync_id, updated_at, nome, bonus_stipendio_evento, ordine, attiva, {fk_col}
                FROM {legacy} src
                WHERE NOT EXISTS (SELECT 1 FROM {carica} c WHERE c.id = src.id)
                """
            )


def migrate_korp_memberships(apps, schema_editor):
    TipoCarriera = apps.get_model("personaggi", "TipoCarriera")
    PersonaggioKorpMembership = apps.get_model("personaggi", "PersonaggioKorpMembership")
    PersonaggioCarrieraMembership = apps.get_model("personaggi", "PersonaggioCarrieraMembership")
    Carica = apps.get_model("personaggi", "Carica")

    tipo_korp = TipoCarriera.objects.get(codice="korp")
    carica_ids = set(Carica.objects.values_list("id", flat=True))

    for m in PersonaggioKorpMembership.objects.all().iterator():
        if PersonaggioCarrieraMembership.objects.filter(sync_id=m.sync_id).exists():
            continue
        carica_id = m.carica_id if m.carica_id in carica_ids else None
        PersonaggioCarrieraMembership.objects.create(
            sync_id=m.sync_id,
            updated_at=m.updated_at,
            personaggio_id=m.personaggio_id,
            carriera_id=m.korp_id,
            tipo_carriera_id=tipo_korp.id,
            carica_id=carica_id,
            data_da=m.data_da,
            data_a=m.data_a,
        )


def backfill_membership_tipo_carriera(apps, schema_editor):
    PersonaggioCarrieraMembership = apps.get_model("personaggi", "PersonaggioCarrieraMembership")
    Carriera = apps.get_model("personaggi", "Carriera")
    for m in PersonaggioCarrieraMembership.objects.filter(tipo_carriera__isnull=True).iterator():
        try:
            carriera = Carriera.objects.get(pk=m.carriera_id)
        except Carriera.DoesNotExist:
            continue
        m.tipo_carriera_id = carriera.tipo_carriera_id
        m.save(update_fields=["tipo_carriera_id", "updated_at"])


def repoint_korp_foreign_keys(apps, schema_editor):
    """Ripunta FK/M2M da personaggi_korp a personaggi_carriera (stessi tier_ptr_id)."""
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    repoints = [
        (
            "social_socialpost",
            "korp_visibilita_id",
            "social_socialpost_korp_visibilita_id_fkey",
        ),
        (
            "social_socialstory",
            "korp_visibilita_id",
            "social_socialstory_korp_visibilita_id_fkey",
        ),
    ]
    m2m_table = "personaggi_innescotimer_target_korps"
    tables = set(connection.introspection.table_names())

    with connection.cursor() as cursor:
        for table, column, constraint in repoints:
            if table not in tables:
                continue
            cursor.execute(
                f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"'
            )
            cursor.execute(
                f"""
                ALTER TABLE "{table}"
                ADD CONSTRAINT "{constraint}"
                FOREIGN KEY ("{column}")
                REFERENCES personaggi_carriera (tier_ptr_id)
                DEFERRABLE INITIALLY DEFERRED
                """
            )

        if m2m_table in tables:
            cursor.execute(
                f'ALTER TABLE "{m2m_table}" DROP CONSTRAINT IF EXISTS '
                f'"{m2m_table}_korp_id_fkey"'
            )
            cursor.execute(
                f"""
                ALTER TABLE "{m2m_table}"
                ADD CONSTRAINT "{m2m_table}_korp_id_fkey"
                FOREIGN KEY (korp_id)
                REFERENCES personaggi_carriera (tier_ptr_id)
                DEFERRABLE INITIALLY DEFERRED
                """
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("personaggi", "0180_scommesse_potenza_post_incontro"),
        ("social", "0004_social_stories"),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoCarriera",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("codice", models.SlugField(max_length=40, unique=True)),
                ("nome", models.CharField(max_length=120)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Tipo Carriera",
                "verbose_name_plural": "Tipi Carriera",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.AddField(
            model_name="carriera",
            name="tipo_carriera",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="carriere",
                to="personaggi.tipocarriera",
            ),
        ),
        migrations.RunPython(seed_tipi_carriera, noop_reverse),
        migrations.RunPython(promote_korps_and_professioni, noop_reverse),
        migrations.CreateModel(
            name="Carica",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120)),
                ("bonus_stipendio_evento", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attiva", models.BooleanField(default=True)),
                (
                    "carriera",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cariche",
                        to="personaggi.carriera",
                    ),
                ),
            ],
            options={
                "verbose_name": "Carica",
                "verbose_name_plural": "Cariche",
                "ordering": ["carriera__nome", "ordine", "nome"],
                "unique_together": {("carriera", "nome")},
            },
        ),
        migrations.RunPython(migrate_cariche_from_legacy, noop_reverse),
        migrations.AddField(
            model_name="personaggiocarrieramembership",
            name="tipo_carriera",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="membership",
                to="personaggi.tipocarriera",
            ),
        ),
        migrations.RunPython(migrate_korp_memberships, noop_reverse),
        migrations.RunPython(backfill_membership_tipo_carriera, noop_reverse),
        migrations.AlterField(
            model_name="personaggiocarrieramembership",
            name="carica",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="membership",
                to="personaggi.carica",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="personaggiocarrieramembership",
            name="uniq_personaggio_carriera_attiva",
        ),
        migrations.RemoveConstraint(
            model_name="personaggiokorpmembership",
            name="uniq_personaggio_korp_attiva",
        ),
        migrations.AlterField(
            model_name="carriera",
            name="tipo_carriera",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="carriere",
                to="personaggi.tipocarriera",
            ),
        ),
        migrations.AlterField(
            model_name="personaggiocarrieramembership",
            name="tipo_carriera",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="membership",
                to="personaggi.tipocarriera",
            ),
        ),
        migrations.AlterField(
            model_name="personaggiocarrieramembership",
            name="personaggio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="carriere_membership",
                to="personaggi.personaggio",
            ),
        ),
        migrations.RunPython(repoint_korp_foreign_keys, noop_reverse),
        migrations.DeleteModel(
            name="PersonaggioKorpMembership",
        ),
        migrations.DeleteModel(
            name="CaricaKorp",
        ),
        migrations.DeleteModel(
            name="CaricaCarriera",
        ),
        migrations.DeleteModel(
            name="Korp",
        ),
        migrations.CreateModel(
            name="Korp",
            fields=[],
            options={
                "verbose_name": "KORP",
                "verbose_name_plural": "KORPS",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("personaggi.carriera",),
        ),
    ]
