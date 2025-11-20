from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Messaggio
from django.contrib.auth.models import User 
from webpush import send_user_notification 

@receiver(post_save, sender=Messaggio)
def invia_notifica_messaggio(sender, instance, created, **kwargs):
    if created: 
        # --- 1. WebSocket (Invariato) ---
        channel_layer = get_channel_layer()
        data = {
            'id': instance.id,
            'titolo': instance.titolo,
            'testo': instance.testo,
            'tipo': instance.tipo_messaggio,
            'mittente': instance.mittente.username if instance.mittente else "Sistema",
            'destinatario_id': instance.destinatario_personaggio.id if instance.destinatario_personaggio else None,
            'gruppo_id': instance.destinatario_gruppo.id if instance.destinatario_gruppo else None,
        }

        async_to_sync(channel_layer.group_send)(
            'kor35_notifications',
            {'type': 'send_notification', 'message': data}
        )

        # --- 2. Web Push (Aggiornato) ---
        try:
            payload = {
                "head": instance.titolo,
                "body": "Nuovo messaggio su KOR-35",
                "icon": "/pwa-192x192.png",
                "url": "https://app.kor35.it" 
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