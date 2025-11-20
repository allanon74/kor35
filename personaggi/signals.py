from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Messaggio
# IMPORTANTE: Aggiungi questo import per le Push Notifications
from webpush import send_user_notification 

@receiver(post_save, sender=Messaggio)
def invia_notifica_messaggio(sender, instance, created, **kwargs):
    if created: # Invia solo se è un nuovo messaggio
        
        # -------------------------------------------------------
        # 1. LIVELLO WEBSOCKET (Per popup in-app in tempo reale)
        # -------------------------------------------------------
        channel_layer = get_channel_layer()
        
        # Prepariamo i dati (Mantieni la tua versione completa con gruppo_id)
        data = {
            'id': instance.id,
            'titolo': instance.titolo,
            'testo': instance.testo,
            'tipo': instance.tipo_messaggio,
            'mittente': instance.mittente.username if instance.mittente else "Sistema",
            'destinatario_id': instance.destinatario_personaggio.id if instance.destinatario_personaggio else None,
            'gruppo_id': instance.destinatario_gruppo.id if instance.destinatario_gruppo else None,
        }

        # Invio al gruppo WebSocket 'kor35_notifications'
        async_to_sync(channel_layer.group_send)(
            'kor35_notifications',
            {
                'type': 'send_notification',
                'message': data
            }
        )

        # -------------------------------------------------------
        # 2. LIVELLO WEB PUSH (Per notifiche di sistema/background)
        # -------------------------------------------------------
        try:
            # Payload per la notifica nativa
            payload = {
                "head": instance.titolo,
                "body": "Nuovo messaggio su KOR-35", # Evitiamo HTML nel body della notifica push
                "icon": "/pwa-192x192.png",
                "url": "https://app.kor35.it" 
            }

            # A. Notifica Individuale
            if instance.tipo_messaggio == 'INDV' and instance.destinatario_personaggio:
                user = instance.destinatario_personaggio.proprietario
                if user:
                    send_user_notification(user=user, payload=payload, ttl=1000)
            
            # B. Notifica di Gruppo
            elif instance.tipo_messaggio == 'GROUP' and instance.destinatario_gruppo:
                # Itera su tutti i membri del gruppo e manda la notifica ai proprietari
                for pg in instance.destinatario_gruppo.membri.select_related('proprietario').all():
                    if pg.proprietario:
                        send_user_notification(user=pg.proprietario, payload=payload, ttl=1000)
                        
            # C. Broadcast (Opzionale - Attenzione al carico se hai tanti utenti)
            # elif instance.tipo_messaggio == 'BROAD':
            #     pass 

        except Exception as e:
            # Non bloccare il salvataggio del messaggio se le push falliscono
            print(f"Errore invio Web Push: {e}")