from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from personaggi.serializers import InventarioSerializer, ManifestoSerializer, PersonaggioListSerializer, PersonaggioAutocompleteSerializer
from .models import Evento, Quest, QuestMostro, QuestVista, GiornoEvento, MostroTemplate, PnGAssegnato
from .serializers import EventoSerializer, QuestMostroSerializer, QuestVistaSerializer, GiornoEventoSerializer, QuestSerializer, PnGAssegnatoSerializer, MostroTemplateSerializer, User, UserShortSerializer, UserShortSerializer
from personaggi.models import Inventario, Manifesto, Personaggio, QrCode

from django.contrib.auth.models import User

from .permissions import IsStaffOrMaster

class IsMasterOrReadOnly(permissions.BasePermission):
    """
    Gli Staffer leggono, i Superuser (Master) scrivono.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_staff):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser

class EventoViewSet(viewsets.ModelViewSet):
    serializer_class = EventoSerializer
    permission_classes = [IsMasterOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Evento.objects.all().prefetch_related('giorni__quests')
        return Evento.objects.filter(staff_assegnato=user).prefetch_related('giorni__quests')
    
    @action(detail=False, methods=['get'])
    def risorse_editor(self, request):
        # OTTIMIZZAZIONE: Usa .only() o serializer leggeri per evitare il timeout
        # Non caricare l'intera storia di ogni personaggio qui!
        return Response({
            'png': PersonaggioAutocompleteSerializer(
                Personaggio.objects.filter(tipologia__giocante=False), 
                many=True
            ).data,
            'templates': MostroTemplateSerializer(MostroTemplate.objects.all(), many=True).data,
            'manifesti': ManifestoSerializer(Manifesto.objects.all(), many=True).data,
            # ATTENZIONE: Caricare TUTTI gli inventari può uccidere il server. 
            # Meglio filtrare o paginare se sono molti.
            'inventari': InventarioSerializer(Inventario.objects.all()[:50], many=True).data, 
            'staff': UserShortSerializer(User.objects.filter(is_staff=True), many=True).data,
        })

class GiornoEventoViewSet(viewsets.ModelViewSet):
    queryset = GiornoEvento.objects.all()
    serializer_class = GiornoEventoSerializer
    permission_classes = [IsMasterOrReadOnly]

class QuestViewSet(viewsets.ModelViewSet):
    queryset = Quest.objects.all()
    serializer_class = QuestSerializer
    permission_classes = [IsMasterOrReadOnly]

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
        
class MostroTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MostroTemplate.objects.all()
    serializer_class = MostroTemplateSerializer
    permission_classes = [IsStaffOrMaster]

class PngAssegnatoViewSet(viewsets.ModelViewSet):
    queryset = PnGAssegnato.objects.all()
    serializer_class = PnGAssegnatoSerializer
    permission_classes = [IsMasterOrReadOnly]