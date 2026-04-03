import logging

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from webpush import send_user_notification

from .models import ClasseOggetto, Infusione, Messaggio

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Messaggio)
def invia_notifica_messaggio(sender, instance, created, **kwargs):
    if created:
        # --- 1. WebSocket (Redis/Channels: su replica o offline può non essere raggiungibile) ---
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                data = {
                    "id": instance.id,
                    "titolo": instance.titolo,
                    "testo": instance.testo,
                    "tipo": instance.tipo_messaggio,
                    "mittente": instance.mittente.username if instance.mittente else "Sistema",
                    "destinatario_id": instance.destinatario_personaggio.id
                    if instance.destinatario_personaggio
                    else None,
                    "gruppo_id": instance.destinatario_gruppo.id
                    if instance.destinatario_gruppo
                    else None,
                }
                async_to_sync(channel_layer.group_send)(
                    "kor35_notifications",
                    {"type": "send_notification", "message": data},
                )
        except Exception as exc:
            logger.debug("Notifica WS messaggio saltata (sync/replica/offline): %s", exc)

        # --- 2. Web Push (Aggiornato) ---
        try:
            payload = {
                "head": instance.titolo,
                "body": "Nuovo messaggio su KOR-35",
                "icon": "/pwa-192x192.png",
                "url": "https://app.kor35.it/?tab=messaggi"  # Puoi personalizzare l'URL di destinazione
            }

            # A. Individuale
            if instance.tipo_messaggio == 'INDV' and instance.destinatario_personaggio:
                user = instance.destinatario_personaggio.proprietario
                if user:
                    send_user_notification(user=user, payload=payload, ttl=1000)
            
            # B. Gruppo
            elif instance.tipo_messaggio == 'GROUP' and instance.destinatario_gruppo:
                for pg in instance.destinatario_gruppo.membri.select_related('proprietario').all():
                    if pg.proprietario:
                        send_user_notification(user=pg.proprietario, payload=payload, ttl=1000)
                        
            # C. Broadcast (ABILITATO)
            elif instance.tipo_messaggio == 'BROAD':
                # Recupera tutti gli utenti che hanno una sottoscrizione Push attiva
                # (È più efficiente che iterare su tutti gli User del DB)
                from webpush.models import PushInformation
                users_with_push = User.objects.filter(pushinformation__isnull=False).distinct()
                
                for user in users_with_push:
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


@receiver(post_save, sender=Infusione)
def copia_dati_da_proposta(sender, instance, created, **kwargs):
    """
    Quando un'Infusione viene creata e collegata a una PropostaTecnica,
    copia automaticamente gli slot permessi se non definiti.
    """
    if created and instance.proposta_creazione and not instance.slot_corpo_permessi:
        instance.slot_corpo_permessi = instance.proposta_creazione.slot_corpo_permessi
        instance.save()