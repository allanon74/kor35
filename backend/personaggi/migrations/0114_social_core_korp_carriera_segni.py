import random
import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def seed_segni_e_backfill_personaggi(apps, schema_editor):
    Tier = apps.get_model("personaggi", "Tier")
    SegnoZodiacale = apps.get_model("personaggi", "SegnoZodiacale")
    Personaggio = apps.get_model("personaggi", "Personaggio")

    segni = []
    for numero in range(1, 11):
        tier = Tier.objects.create(
            nome=f"Segno {numero}",
            descrizione=f"Segno zodiacale numero {numero}",
            tipo="G0",
        )
        segno = SegnoZodiacale.objects.create(
            tier_ptr=tier,
            numero=numero,
            testo_pubblico=f"Testo pubblico del segno {numero}",
            testo_privato=f"Testo privato del segno {numero}",
        )
        segni.append(segno.id)

    if not segni:
        return

    personaggi_senza_segno = Personaggio.objects.filter(segno_zodiacale__isnull=True).values_list("id", flat=True)
    for personaggio_id in personaggi_senza_segno:
        Personaggio.objects.filter(id=personaggio_id, segno_zodiacale__isnull=True).update(
            segno_zodiacale_id=random.choice(segni)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0113_sync_join_tables_unique"),
    ]

    operations = [
        migrations.CreateModel(
            name="Carriera",
            fields=[
                (
                    "tier_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.tier",
                    ),
                ),
            ],
            options={
                "verbose_name": "Carriera",
                "verbose_name_plural": "Carriere",
            },
            bases=("personaggi.tier",),
        ),
        migrations.CreateModel(
            name="Korp",
            fields=[
                (
                    "tier_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.tier",
                    ),
                ),
            ],
            options={
                "verbose_name": "KORP",
                "verbose_name_plural": "KORP",
            },
            bases=("personaggi.tier",),
        ),
        migrations.CreateModel(
            name="SegnoZodiacale",
            fields=[
                (
                    "tier_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.tier",
                    ),
                ),
                ("numero", models.PositiveSmallIntegerField(unique=True)),
                ("testo_pubblico", models.TextField(blank=True, null=True)),
                ("testo_privato", models.TextField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Segno Zodiacale",
                "verbose_name_plural": "Segni Zodiacali",
                "ordering": ["numero", "nome"],
            },
            bases=("personaggi.tier",),
        ),
        migrations.CreateModel(
            name="CaricaKorp",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120)),
                ("bonus_stipendio_evento", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attiva", models.BooleanField(default=True)),
                ("korp", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cariche", to="personaggi.korp")),
            ],
            options={
                "verbose_name": "Carica KORP",
                "verbose_name_plural": "Cariche KORP",
                "ordering": ["korp__nome", "ordine", "nome"],
                "unique_together": {("korp", "nome")},
            },
        ),
        migrations.CreateModel(
            name="CaricaCarriera",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120)),
                ("bonus_stipendio_evento", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attiva", models.BooleanField(default=True)),
                ("carriera", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cariche", to="personaggi.carriera")),
            ],
            options={
                "verbose_name": "Carica Carriera",
                "verbose_name_plural": "Cariche Carriera",
                "ordering": ["carriera__nome", "ordine", "nome"],
                "unique_together": {("carriera", "nome")},
            },
        ),
        migrations.AddField(
            model_name="personaggio",
            name="segno_zodiacale",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="personaggi", to="personaggi.segnozodiacale"),
        ),
        migrations.CreateModel(
            name="PersonaggioKorpMembership",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("data_da", models.DateTimeField(default=django.utils.timezone.now)),
                ("data_a", models.DateTimeField(blank=True, null=True)),
                ("carica", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="membership", to="personaggi.caricakorp")),
                ("korp", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="membership", to="personaggi.korp")),
                ("personaggio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="korp_membership", to="personaggi.personaggio")),
            ],
            options={
                "verbose_name": "Membership KORP",
                "verbose_name_plural": "Membership KORP",
                "ordering": ["-data_da", "-id"],
            },
        ),
        migrations.CreateModel(
            name="PersonaggioCarrieraMembership",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("data_da", models.DateTimeField(default=django.utils.timezone.now)),
                ("data_a", models.DateTimeField(blank=True, null=True)),
                ("carica", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="membership", to="personaggi.caricacarriera")),
                ("carriera", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="membership", to="personaggi.carriera")),
                ("personaggio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="carriera_membership", to="personaggi.personaggio")),
            ],
            options={
                "verbose_name": "Membership Carriera",
                "verbose_name_plural": "Membership Carriera",
                "ordering": ["-data_da", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="personaggiokorpmembership",
            constraint=models.UniqueConstraint(condition=models.Q(("data_a__isnull", True)), fields=("personaggio",), name="uniq_personaggio_korp_attiva"),
        ),
        migrations.AddConstraint(
            model_name="personaggiocarrieramembership",
            constraint=models.UniqueConstraint(condition=models.Q(("data_a__isnull", True)), fields=("personaggio",), name="uniq_personaggio_carriera_attiva"),
        ),
        migrations.RunPython(seed_segni_e_backfill_personaggi, migrations.RunPython.noop),
    ]
