from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from webpush import send_user_notification

from .models import (
    ClasseOggetto,
    Infusione,
    Messaggio,
)
from .campaigns import ensure_user_in_base_campaign


@receiver(post_save, sender=User)
def assegna_campagna_base_ai_nuovi_utenti(sender, instance, created, **kwargs):
    """
    Vincolo di default: ogni nuovo utente appartiene solo alla campagna base.
    Le campagne aggiuntive devono essere assegnate esplicitamente dallo staff.
    """
    if not created:
        return
    ensure_user_in_base_campaign(instance)

def _strip_html_preview(text, max_len=120):
    import re

    plain = re.sub(r"<[^>]+>", " ", text or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_len:
        return plain
    return plain[: max_len - 1].rstrip() + "…"


def _ws_notify_users(user_ids, data):
    """Invia notifica solo alle room per-utente (privacy: niente fan-out globale)."""
    from personaggi.ws_auth import user_notifications_group

    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    for uid in {int(u) for u in user_ids if u}:
        async_to_sync(channel_layer.group_send)(
            user_notifications_group(uid),
            {"type": "send_notification", "message": data},
        )


def _ws_notify_global(data):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {"type": "send_notification", "message": data},
    )


def _campaign_staff_user_ids(campagna):
    from personaggi.models import (
        CAMPAGNA_ROLE_HEAD_MASTER,
        CAMPAGNA_ROLE_MASTER,
        CAMPAGNA_ROLE_STAFFER,
        CampagnaUtente,
    )

    if not campagna:
        return []
    return list(
        CampagnaUtente.objects.filter(
            campagna=campagna,
            attivo=True,
            ruolo__in=(CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER),
        ).values_list("user_id", flat=True)
    )


@receiver(post_save, sender=Messaggio)
def invia_notifica_messaggio(sender, instance, created, **kwargs):
    if not created:
        return

    data = {
        "id": instance.id,
        "titolo": instance.titolo,
        "testo": instance.testo,
        "tipo": instance.tipo_messaggio,
        "mittente": instance.mittente.username if instance.mittente else "Sistema",
        "destinatario_id": (
            instance.destinatario_personaggio.id if instance.destinatario_personaggio else None
        ),
        "gruppo_id": instance.destinatario_gruppo.id if instance.destinatario_gruppo else None,
    }

    # --- 1. WebSocket (room per-utente; BROAD resta sul canale globale) ---
    if instance.tipo_messaggio == Messaggio.TIPO_BROADCAST:
        _ws_notify_global(data)
    elif instance.tipo_messaggio == Messaggio.TIPO_INDIVIDUALE and instance.destinatario_personaggio:
        dest_user = instance.destinatario_personaggio.proprietario_id
        ids = [dest_user]
        if instance.mittente_personaggio_id:
            ids.append(instance.mittente_personaggio.proprietario_id)
        _ws_notify_users(ids, data)
    elif instance.tipo_messaggio == Messaggio.TIPO_GRUPPO and instance.destinatario_gruppo:
        member_ids = instance.destinatario_gruppo.membri.values_list("proprietario_id", flat=True)
        _ws_notify_users(member_ids, data)
    elif instance.tipo_messaggio == Messaggio.TIPO_STAFF or instance.is_staff_message:
        staff_ids = _campaign_staff_user_ids(instance.campagna)
        if instance.mittente_personaggio_id:
            staff_ids = list(staff_ids) + [instance.mittente_personaggio.proprietario_id]
        _ws_notify_users(staff_ids, data)

    # --- 2. Web Push (URL relativo: funziona su edge IP / mirror / www) ---
    try:
        payload = {
            "head": instance.titolo or "Nuovo messaggio",
            "body": _strip_html_preview(instance.testo) or "Nuovo messaggio su KOR-35",
            "icon": "/pwa-192x192.png",
            "url": "/?tab=messaggi",
        }

        if instance.tipo_messaggio == Messaggio.TIPO_INDIVIDUALE and instance.destinatario_personaggio:
            user = instance.destinatario_personaggio.proprietario
            if user:
                send_user_notification(user=user, payload=payload, ttl=1000)

        elif instance.tipo_messaggio == Messaggio.TIPO_GRUPPO and instance.destinatario_gruppo:
            for pg in instance.destinatario_gruppo.membri.select_related("proprietario").all():
                if pg.proprietario:
                    send_user_notification(user=pg.proprietario, payload=payload, ttl=1000)

        elif instance.tipo_messaggio == Messaggio.TIPO_BROADCAST:
            from webpush.models import PushInformation

            # Solo utenti con PG nella stessa campagna del broadcast (meno spam cross-campagna).
            campagna = instance.campagna
            qs = User.objects.filter(pushinformation__isnull=False).distinct()
            if campagna:
                qs = qs.filter(personaggi__campagna=campagna).distinct()
            for user in qs:
                send_user_notification(user=user, payload=payload, ttl=1000)

        elif instance.tipo_messaggio == Messaggio.TIPO_STAFF or instance.is_staff_message:
            for uid in _campaign_staff_user_ids(instance.campagna):
                try:
                    user = User.objects.get(pk=uid)
                except User.DoesNotExist:
                    continue
                send_user_notification(user=user, payload=payload, ttl=1000)

    except Exception as e:
        print(f"Errore invio Web Push: {e}")

@receiver(
    m2m_changed,
    sender=ClasseOggetto.mattoni_materia_permessi.through,
)
def touch_classeoggetto_updated_at_on_materia_m2m(
    sender, instance, action, reverse, pk_set, **kwargs
):
    """
    Le modifiche solo-M2M non chiamano save() sul modello padre, quindi updated_at
    resta vecchio e l'edge sync incrementale (updated_at__gt) non esporta la riga.
    Dopo post_* aggiorniamo updated_at; su apply replica il comando sync sovrascrive
    comunque con l'updated_at remoto se presente.
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    now = timezone.now()
    if reverse:
        # Lato Punteggio: pk_set contiene gli id delle ClasseOggetto coinvolte.
        if pk_set:
            ClasseOggetto.objects.filter(pk__in=pk_set).update(updated_at=now)
        # post_clear con reverse=True: pk_set è None; caso raro dall'admin.
    elif instance.pk:
        ClasseOggetto.objects.filter(pk=instance.pk).update(updated_at=now)


def bump_mti_personaggi_parents_updated_at(sender, instance, **kwargs):
    """
    Dopo save su un modello MTI di `personaggi`, aggiorna `updated_at` su ogni
    antenato concreto nello stesso app (Tabella, A_vista, Inventario, …) così il
    delta sync (`updated_at__gt`) non perde modifiche solo-tabella-figlia.
    Ignora genitori fuori da personaggi.models (es. CMSPlugin).
    """
    if kwargs.get("raw"):
        return
    now = timezone.now()
    cls = instance.__class__
    while cls is not None and cls._meta.parents:
        parent_cls = next(iter(cls._meta.parents.keys()))
        cls = parent_cls
        if getattr(cls._meta, "abstract", False):
            continue
        if cls.__module__ != "personaggi.models":
            continue
        if not hasattr(cls, "updated_at"):
            continue
        cls.objects.filter(pk=instance.pk).update(updated_at=now)


@receiver(post_save, sender=Infusione)
def copia_dati_da_proposta(sender, instance, created, **kwargs):
    """
    Quando un'Infusione viene creata e collegata a una PropostaTecnica,
    copia automaticamente gli slot permessi se non definiti.
    """
    if created and instance.proposta_creazione and not instance.slot_corpo_permessi:
        instance.slot_corpo_permessi = instance.proposta_creazione.slot_corpo_permessi
        instance.save()