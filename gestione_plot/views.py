from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Evento, Quest, QuestMostro, QuestVista
from .serializers import EventoSerializer, QuestMostroSerializer, QuestVistaSerializer
from personaggi.models import QrCode

from .permissions import IsStaffOrMaster

class EventoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lettura degli eventi. 
    Gli Admin vedono tutto, gli Staffer solo dove sono assegnati.
    """
    serializer_class = EventoSerializer
    permission_classes = [IsStaffOrMaster]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Evento.objects.all().prefetch_related('giorni__quests')
        return Evento.objects.filter(staff_assegnato=user).prefetch_related('giorni__quests')

class QuestMostroViewSet(viewsets.ModelViewSet):
    """
    Gestione istanze mostri. Permette di aggiornare PV/Armatura in tempo reale.
    """
    queryset = QuestMostro.objects.all()
    serializer_class = QuestMostroSerializer
    permission_classes = [IsStaffOrMaster]

    @action(detail=True, methods=['post'])
    def modifica_hp(self, request, pk=None):
        mostro = self.get_object()
        delta = request.data.get('delta', 0) # Es: +1 o -1
        mostro.punti_vita = max(0, mostro.punti_vita + int(delta))
        mostro.save()
        return Response({'status': 'ok', 'punti_vita': mostro.punti_vita})

class QuestVistaViewSet(viewsets.ModelViewSet):
    queryset = QuestVista.objects.all()
    serializer_class = QuestVistaSerializer
    permission_classes = [IsStaffOrMaster]

    @action(detail=True, methods=['post'])
    def associa_qr(self, request, pk=None):
        """
        FUNZIONE CRUCIALE: Associa un QR fisico scansionato a questa vista prevista.
        """
        vista_quest = self.get_object()
        qr_id = request.data.get('qr_id')
        
        try:
            qr = QrCode.objects.get(id=qr_id)
            # Colleghiamo il QR alla "Vista" (Manifesto o Inventario) definita
            target_vista = vista_quest.manifesto or vista_quest.inventario
            
            if not target_vista:
                return Response({'error': 'Nessun contenuto definito per questa vista'}, status=400)
            
            # Aggiorniamo il QR Code reale nel database dei personaggi
            qr.vista = target_vista
            qr.save()
            
            # Salviamo il riferimento anche nel plot per tracciamento
            vista_quest.qr_code = qr
            vista_quest.save()
            
            return Response({'status': 'success', 'content': str(target_vista)})
        except QrCode.DoesNotExist:
            return Response({'error': 'QR Code non trovato'}, status=404)