# personaggi/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Messaggio

@receiver(post_save, sender=Messaggio)
def invia_notifica_messaggio(sender, instance, created, **kwargs):
    if created: # Invia solo se è un nuovo messaggio
        channel_layer = get_channel_layer()
        
        # Prepariamo i dati
        data = {
            'id': instance.id,
            'titolo': instance.titolo,
            'testo': instance.testo,
            'tipo': instance.tipo_messaggio,
            'mittente': instance.mittente.username if instance.mittente else "Sistema",
            'destinatario_id': instance.destinatario_personaggio.id if instance.destinatario_personaggio else None,
            'gruppo_id': instance.destinatario_gruppo.id if instance.destinatario_gruppo else None,
        }

        # Invio al gruppo 'kor35_notifications'
        async_to_sync(channel_layer.group_send)(
            'kor35_notifications',
            {
                'type': 'send_notification', # corrisponde al metodo nel Consumer
                'message': data
            }
        )