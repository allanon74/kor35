from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from django.shortcuts import get_object_or_404
import os
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from PIL import Image

from personaggi.models import (
    Inventario, Manifesto, Personaggio, QrCode, 
    Tabella, ModelloAura, Tier,
    )

from personaggi.serializers import (
    InventarioSerializer, ManifestoSerializer, 
    PersonaggioListSerializer, PersonaggioAutocompleteSerializer, PersonaggioSerializer,
    TabellaSerializer, AbilitaSerializer, ModelloAuraSerializer,
                                    )
from .models import Evento, PaginaRegolamento, Quest, QuestMostro, QuestVista, GiornoEvento, MostroTemplate, PngAssegnato, StaffOffGame, QuestFase, QuestTask, WikiImmagine
from .serializers import (
    EventoSerializer, PaginaRegolamentoSerializer, PaginaRegolamentoSmallSerializer, QuestMostroSerializer, QuestVistaSerializer, 
    GiornoEventoSerializer, QuestSerializer, PngAssegnatoSerializer, 
    MostroTemplateSerializer, User, UserShortSerializer, UserShortSerializer,
    StaffOffGameSerializer, QuestFaseSerializer, QuestTaskSerializer, WikiTierSerializer, WikiImmagineSerializer,
                          )


from django.contrib.auth.models import User

from .permissions import IsStaffOrMaster

class IsMasterOrReadOnly(permissions.BasePermission):
    """
    Gli Staffer leggono e scrivono, gli utenti non staff non vedono nulla.
    """
    def has_permission(self, request, view):
        # Deve essere almeno staff per accedere
        if not (request.user and request.user.is_authenticated and request.user.is_staff):
            return False
        # Permetti GET/HEAD/OPTIONS a tutto lo staff
        if request.method in permissions.SAFE_METHODS:
            return True
        # CORREZIONE: Permetti POST/PUT/DELETE sia a Superuser che a Staff
        return request.user.is_staff or request.user.is_superuser

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
        """
        Versione ottimizzata e filtrata.
        Esclude inventari di Personaggi/PnG e carica solo i dati minimi.
        Ottimizzato con select_related e only() per ridurre le query.
        """
        # Ottimizzazione: select_related per evitare N+1 queries
        # NOTA: 'crediti' e 'punti_caratteristica' sono @property, non vanno in only()
        png_queryset = Personaggio.objects.select_related(
            'tipologia', 'proprietario'
        ).only(
            'id', 'nome', 'testo', 'costume', 'data_nascita', 'data_morte',
            'tipologia', 'proprietario'
        )
        
        return Response({
            'png': PersonaggioSerializer(png_queryset, many=True).data,
            'templates': MostroTemplateSerializer(MostroTemplate.objects.all(), many=True).data,
            'manifesti': ManifestoSerializer(Manifesto.objects.all(), many=True).data,
            'inventari': InventarioSerializer(Inventario.objects.all(), many=True).data,
            'staff': UserShortSerializer(User.objects.filter(is_staff=True).only('id', 'username', 'first_name', 'last_name'), many=True).data,
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
        
class MostroTemplateViewSet(viewsets.ModelViewSet): # Cambiato da ReadOnlyModelViewSet a ModelViewSet
    queryset = MostroTemplate.objects.all().prefetch_related('attacchi')
    serializer_class = MostroTemplateSerializer
    permission_classes = [IsStaffOrMaster]

class PngAssegnatoViewSet(viewsets.ModelViewSet):
    queryset = PngAssegnato.objects.all()
    serializer_class = PngAssegnatoSerializer
    permission_classes = [IsMasterOrReadOnly]
    
class StaffOffGameViewSet(viewsets.ModelViewSet):
    queryset = StaffOffGame.objects.all()
    serializer_class = StaffOffGameSerializer
    
class QuestFaseViewSet(viewsets.ModelViewSet):
    queryset = QuestFase.objects.all()
    serializer_class = QuestFaseSerializer
    permission_classes = [permissions.IsAuthenticated]

class QuestTaskViewSet(viewsets.ModelViewSet):
    queryset = QuestTask.objects.all()
    serializer_class = QuestTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Logica automatica per mostri: le stats vengono già gestite nel model.save()
        serializer.save()

class PaginaRegolamentoViewSet(viewsets.ModelViewSet):
    queryset = PaginaRegolamento.objects.all()
    serializer_class = PaginaRegolamentoSerializer
    permission_classes = [IsMasterOrReadOnly]
    
class PaginaRegolamentoSmallViewSet(viewsets.ModelViewSet):
    queryset = PaginaRegolamento.objects.all()
    serializer_class = PaginaRegolamentoSmallSerializer
    permission_classes = [permissions.IsAuthenticated]
    

# ViewSet per il Menu (solo titoli e struttura) - PUBBLICO
class PublicPaginaRegolamentoMenu(viewsets.ReadOnlyModelViewSet):
    queryset = PaginaRegolamento.objects.filter(public=True).order_by('ordine', 'titolo')
    serializer_class = PaginaRegolamentoSmallSerializer
    permission_classes = [permissions.AllowAny] # Aperto a tutti
    pagination_class = None # Il menu lo vogliamo tutto in una volta

# ViewSet per il Contenuto Pagina - PUBBLICO
class PublicPaginaRegolamentoDetail(viewsets.ReadOnlyModelViewSet):
    queryset = PaginaRegolamento.objects.filter(public=True)
    serializer_class = PaginaRegolamentoSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug' # Importante: cerchiamo per slug, non per ID
    
class PublicTabellaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone le Tabelle (es. Liste Abilità) per il regolamento pubblico.
    """
    queryset = Tabella.objects.all()
    serializer_class = TabellaSerializer
    permission_classes = [permissions.AllowAny] # <--- FONDAMENTALE: Accesso pubblico!

class PublicAuraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone le Aure per il regolamento pubblico.
    """
    queryset = ModelloAura.objects.all()
    serializer_class = ModelloAuraSerializer
    permission_classes = [permissions.AllowAny]
    
class PublicTierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone i Tier (es. Livello 1, Livello 2...) con le relative abilità.
    """
    queryset = Tier.objects.all().prefetch_related('abilita') # Ottimizza la query
    serializer_class = WikiTierSerializer
    permission_classes = [permissions.AllowAny] # Accesso pubblic

class PublicWikiImmagineViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone le immagini wiki per l'uso nei widget.
    Accesso pubblico in lettura.
    """
    queryset = WikiImmagine.objects.all()
    serializer_class = WikiImmagineSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_context(self):
        """Aggiunge il request al contesto per generare URL assoluti"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class StaffWikiImmagineViewSet(viewsets.ModelViewSet):
    """
    ViewSet per la gestione CRUD delle immagini wiki (solo staff).
    Permette di creare, modificare ed eliminare immagini.
    """
    queryset = WikiImmagine.objects.all()
    serializer_class = WikiImmagineSerializer
    permission_classes = [IsMasterOrReadOnly]
    
    def get_serializer_context(self):
        """Aggiunge il request al contesto per generare URL assoluti"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        """Imposta automaticamente il creatore quando viene creata un'immagine"""
        serializer.save(creatore=self.request.user)
    
    
def is_staff_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@api_view(['GET'])
@permission_classes([AllowAny]) # Aperto a tutti, filtriamo dentro
def get_wiki_menu(request):
    # Base: prendi tutto
    queryset = PaginaRegolamento.objects.all().order_by('parent', 'ordine', 'titolo')
    
    # Se NON è staff, nascondi bozze e pagine riservate
    if not is_staff_user(request.user):
        queryset = queryset.filter(public=True, visibile_solo_staff=False)
    
    serializer = PaginaRegolamentoSmallSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_wiki_page(request, slug):
    queryset = PaginaRegolamento.objects.all()
    
    # Stesso filtro: se non sei staff, non puoi vedere cose private anche se indovini lo slug
    if not is_staff_user(request.user):
        queryset = queryset.filter(public=True, visibile_solo_staff=False)
        
    page = get_object_or_404(queryset, slug=slug)
    serializer = PaginaRegolamentoSerializer(page)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def serve_wiki_image(request, slug):
    """
    Restituisce l'immagine della pagina wiki ridimensionata.
    Query params:
    - w: larghezza desiderata (es. 1024)
    - q: qualità (default 80)
    """
    page = get_object_or_404(PaginaRegolamento, slug=slug)
    
    if not page.immagine:
        raise Http404("Nessuna immagine associata")

    # Parametri richiesti
    try:
        width = int(request.GET.get('w', 0))
    except ValueError:
        width = 0
        
    original_path = page.immagine.path
    
    # Se non è richiesta una larghezza specifica o è troppo grande, ritorna l'originale
    if width <= 0 or width > 2500:
        return FileResponse(open(original_path, 'rb'), content_type='image/jpeg')

    # Logica di Caching: nomefile_W.ext
    base, ext = os.path.splitext(original_path)
    cache_filename = f"{base}_{width}{ext}"
    
    # 1. Se esiste il file cachato, restituiscilo
    if os.path.exists(cache_filename):
        return FileResponse(open(cache_filename, 'rb'), content_type='image/jpeg')

    # 2. Se non esiste, generalo
    try:
        img = Image.open(original_path)
        
        # Calcola altezza mantenendo aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(width * aspect_ratio)
        
        # Ridimensiona
        img = img.resize((width, new_height), Image.Resampling.LANCZOS)
        
        # Salva copia ottimizzata
        img.save(cache_filename, quality=85, optimize=True)
        
        # Riapri per servire il file (per evitare lock)
        return FileResponse(open(cache_filename, 'rb'), content_type='image/jpeg')
        
    except Exception as e:
        print(f"Errore resize immagine: {e}")
        # Fallback sull'originale in caso di errore
        return FileResponse(open(original_path, 'rb'), content_type='image/jpeg')