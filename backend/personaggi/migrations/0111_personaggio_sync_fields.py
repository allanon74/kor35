import uuid
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


SYNC_MODELS = [
    "a_vista", "tabella", "mattonestatistica", "modelloaurarequisitodoppia",
    "modelloaurarequisitomattone", "modelloaurarequisitocaratt", "modelloaura",
    "caratteristicamodificatore", "abilitastatistica", "configurazionelivelloaura",
    "abilita", "abilita_tier", "abilita_prerequisito", "abilita_requisito",
    "abilita_sbloccata", "abilita_punteggio", "attivataelemento", "attivatastatisticabase",
    "infusionestatistica", "cerimonialecaratteristica", "infusionecaratteristica",
    "tessituracaratteristica", "infusionestatisticabase", "tessiturastatisticabase",
    "oggettoininventario", "tipologiapersonaggio", "punticaratteristicamovimento",
    "creditomovimento", "personaggiolog", "oggettocaratteristica", "oggettostatistica",
    "oggettostatisticabase", "personaggiostatisticabase", "qrcode", "tipologiatimer",
    "timerqrcode", "statotimerattivo", "classeoggetto", "classeoggettolimitemod",
    "oggettobase", "oggettobasestatisticabase", "oggettobasemodificatore",
    "personaggioabilita", "personaggioattivata", "personaggioinfusione",
    "personaggiotessitura", "personaggiocerimoniale", "personaggiomodelloaura",
    "transazionesospesa", "propostatransazione", "gruppo", "messaggio", "letturamessaggio",
    "abilitapluginmodel", "oggettopluginmodel", "attivatapluginmodel",
    "infusionepluginmodel", "tessiturapluginmodel", "tabellapluginmodel",
    "tierpluginmodel", "cerimonialepluginmodel", "propostatecnica",
    "propostatecnicacaratteristica", "propostatecnicamattone", "forgiaturaincorso",
    "richiestaassemblaggio", "dichiarazione", "tipologiaeffetto", "effettocasuale",
    "consumabilepersonaggio", "creazioneconsumabileincorso",
]


def populate_sync_fields(apps, schema_editor):
    now = timezone.now()
    for model_name in SYNC_MODELS:
        Model = apps.get_model("personaggi", model_name)
        for row in Model.objects.filter(sync_id__isnull=True).only("id", "sync_id", "updated_at"):
            row.sync_id = uuid.uuid4()
            if row.updated_at is None:
                row.updated_at = now
            row.save(update_fields=["sync_id", "updated_at"])
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    AuthUserSyncState = apps.get_model("personaggi", "AuthUserSyncState")
    AuthGroupSyncState = apps.get_model("personaggi", "AuthGroupSyncState")
    for user in User.objects.all().only("id"):
        AuthUserSyncState.objects.get_or_create(user=user)
    for group in Group.objects.all().only("id"):
        AuthGroupSyncState.objects.get_or_create(group=group)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0110_merge_0109_abilita_caratteristica_2_caratteristica_3_0109_punteggio_icona_nome_originale"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthGroupSyncState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("group", models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="sync_state", to="auth.group")),
            ],
        ),
        migrations.CreateModel(
            name="AuthUserSyncState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="sync_state", to="auth.user")),
            ],
        ),
        migrations.AddField(model_name="a_vista", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="a_vista", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tabella", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tabella", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="mattonestatistica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="mattonestatistica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="modelloaurarequisitodoppia", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="modelloaurarequisitodoppia", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="modelloaurarequisitomattone", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="modelloaurarequisitomattone", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="modelloaurarequisitocaratt", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="modelloaurarequisitocaratt", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="modelloaura", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="modelloaura", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="caratteristicamodificatore", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="caratteristicamodificatore", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilitastatistica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilitastatistica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="configurazionelivelloaura", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="configurazionelivelloaura", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilita", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilita", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilita_tier", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilita_tier", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilita_prerequisito", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilita_prerequisito", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilita_requisito", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilita_requisito", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilita_sbloccata", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilita_sbloccata", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilita_punteggio", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilita_punteggio", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="attivataelemento", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="attivataelemento", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="attivatastatisticabase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="attivatastatisticabase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="infusionestatistica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="infusionestatistica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="cerimonialecaratteristica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="cerimonialecaratteristica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="infusionecaratteristica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="infusionecaratteristica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tessituracaratteristica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tessituracaratteristica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="infusionestatisticabase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="infusionestatisticabase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tessiturastatisticabase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tessiturastatisticabase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettoininventario", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettoininventario", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tipologiapersonaggio", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tipologiapersonaggio", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="punticaratteristicamovimento", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="punticaratteristicamovimento", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="creditomovimento", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="creditomovimento", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggiolog", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggiolog", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettocaratteristica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettocaratteristica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettostatistica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettostatistica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettostatisticabase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettostatisticabase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggiostatisticabase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggiostatisticabase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="qrcode", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="qrcode", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tipologiatimer", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tipologiatimer", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="timerqrcode", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="timerqrcode", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="statotimerattivo", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="statotimerattivo", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="classeoggetto", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="classeoggetto", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="classeoggettolimitemod", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="classeoggettolimitemod", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettobase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettobase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettobasestatisticabase", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettobasestatisticabase", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettobasemodificatore", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettobasemodificatore", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggioabilita", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggioabilita", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggioattivata", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggioattivata", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggioinfusione", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggioinfusione", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggiotessitura", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggiotessitura", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggiocerimoniale", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggiocerimoniale", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="personaggiomodelloaura", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="personaggiomodelloaura", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="transazionesospesa", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="transazionesospesa", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="propostatransazione", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="propostatransazione", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="gruppo", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="gruppo", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="messaggio", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="messaggio", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="letturamessaggio", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="letturamessaggio", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="abilitapluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="abilitapluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="oggettopluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="oggettopluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="attivatapluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="attivatapluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="infusionepluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="infusionepluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tessiturapluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tessiturapluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tabellapluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tabellapluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tierpluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tierpluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="cerimonialepluginmodel", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="cerimonialepluginmodel", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="propostatecnica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="propostatecnica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="propostatecnicacaratteristica", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="propostatecnicacaratteristica", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="propostatecnicamattone", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="propostatecnicamattone", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="forgiaturaincorso", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="forgiaturaincorso", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="richiestaassemblaggio", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="richiestaassemblaggio", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="dichiarazione", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="dichiarazione", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="tipologiaeffetto", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="tipologiaeffetto", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="effettocasuale", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="effettocasuale", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="consumabilepersonaggio", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="consumabilepersonaggio", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
        migrations.AddField(model_name="creazioneconsumabileincorso", name="sync_id", field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="creazioneconsumabileincorso", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
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
