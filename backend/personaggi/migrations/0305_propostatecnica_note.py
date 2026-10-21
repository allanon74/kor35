"""Note datate sulle proposte tecniche, con storico degli invii già presenti."""

import uuid
from datetime import timedelta

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def _copia_note_esistenti(apps, schema_editor):
    PropostaTecnica = apps.get_model("personaggi", "PropostaTecnica")
    Nota = apps.get_model("personaggi", "PropostaTecnicaNota")
    adesso = timezone.now()
    for proposta in PropostaTecnica.objects.all().iterator():
        righe = []
        if proposta.data_invio:
            righe.append(
                Nota(
                    id=uuid.uuid4(),
                    sync_id=uuid.uuid4(),
                    proposta_id=proposta.pk,
                    testo="Inviata per approvazione",
                    origine="INVIO",
                    creata_il=proposta.data_invio,
                    created_at=adesso,
                    updated_at=adesso,
                )
            )
        staff = (proposta.note_staff or "").strip()
        if staff:
            quando = proposta.updated_at or proposta.data_creazione or adesso
            if proposta.data_invio and quando <= proposta.data_invio:
                quando = proposta.data_invio + timedelta(seconds=1)
            righe.append(
                Nota(
                    id=uuid.uuid4(),
                    sync_id=uuid.uuid4(),
                    proposta_id=proposta.pk,
                    testo=staff,
                    origine="STAFF",
                    creata_il=quando,
                    created_at=adesso,
                    updated_at=adesso,
                )
            )
        if righe:
            Nota.objects.bulk_create(righe)


def _svuota_note(apps, schema_editor):
    apps.get_model("personaggi", "PropostaTecnicaNota").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0304_bonus_ca_contestuale"),
    ]

    operations = [
        migrations.CreateModel(
            name="PropostaTecnicaNota",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("testo", models.TextField()),
                (
                    "origine",
                    models.CharField(
                        choices=[("INVIO", "Invio giocatore"), ("STAFF", "Nota master")],
                        default="STAFF",
                        max_length=8,
                    ),
                ),
                ("creata_il", models.DateTimeField(db_index=True, default=timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "proposta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="note_log",
                        to="personaggi.propostatecnica",
                    ),
                ),
            ],
            options={
                "verbose_name": "Nota proposta tecnica",
                "verbose_name_plural": "Note proposte tecniche",
                "ordering": ["creata_il", "created_at"],
            },
        ),
        migrations.RunPython(_copia_note_esistenti, _svuota_note),
    ]
