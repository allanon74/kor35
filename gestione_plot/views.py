from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError

from django.shortcuts import get_object_or_404
import os
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from PIL import Image

from personaggi.models import (
    Inventario, Manifesto, Personaggio, QrCode, 
    Tabella, ModelloAura, Tier,
    Tessitura, Infusione, Cerimoniale, Oggetto,
    )

from personaggi.serializers import (
    InventarioSerializer, ManifestoSerializer, 
    PersonaggioListSerializer, PersonaggioAutocompleteSerializer, PersonaggioSerializer,
    TabellaSerializer, AbilitaSerializer, ModelloAuraSerializer,
    TessituraSerializer, InfusioneSerializer, CerimonialeSerializer, OggettoSerializer,
                                    )
from .models import Evento, PaginaRegolamento, Quest, QuestMostro, QuestVista, GiornoEvento, MostroTemplate, PngAssegnato, StaffOffGame, QuestFase, QuestTask, WikiImmagine, WikiButtonWidget, WikiButton, ConfigurazioneSito, LinkSocial
from .serializers import (
    EventoSerializer, EventoPubblicoSerializer, PaginaRegolamentoSerializer, PaginaRegolamentoSmallSerializer, QuestMostroSerializer, QuestVistaSerializer, 
    GiornoEventoSerializer, QuestSerializer, PngAssegnatoSerializer, 
    MostroTemplateSerializer, StaffOffGameSerializer, QuestFaseSerializer, QuestTaskSerializer, WikiImmagineSerializer, WikiButtonWidgetSerializer,
    ConfigurazioneSitoSerializer, LinkSocialSerializer, WikiTierSerializer
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
        
        base_queryset = Evento.objects.all().prefetch_related(
            'giorni__quests__mostri_presenti',
            'giorni__quests__png_richiesti',
            'giorni__quests__viste_previste__manifesto',
            'giorni__quests__viste_previste__inventario',
            'giorni__quests__viste_previste__personaggio',
            'giorni__quests__viste_previste__oggetto',
            'giorni__quests__viste_previste__tessitura',
            'giorni__quests__viste_previste__infusione',
            'giorni__quests__viste_previste__cerimoniale',
            'giorni__quests__staff_offgame',
            'giorni__quests__fasi__tasks'
        )
        
        if user.is_superuser:
            return base_queryset
        return base_queryset.filter(staff_assegnato=user)
    
    @action(detail=False, methods=['get'])
    def a_vista_disponibili(self, request):
        """
        Restituisce TUTTI gli oggetti A_vista con tipo calcolato.
        """
        from personaggi.models import (
            A_vista, Personaggio, Inventario, Manifesto, 
            Oggetto, Tessitura, Infusione, Cerimoniale
        )
        
        risultati = []
        tipo_mapping = {
            'PG': 'Personaggio (PG)',
            'PNG': 'Personaggio Non Giocante (PNG)',
            'INV': 'Inventario',
            'OGG': 'Oggetto',
            'TES': 'Tessitura',
            'INF': 'Infusione',
            'CER': 'Cerimoniale',
            'MAN': 'Manifesto'
        }
        
        # Carica Personaggi con tipologia
        for p in Personaggio.objects.select_related('tipologia').all():
            tipo = 'PG' if (p.tipologia and p.tipologia.giocante) else 'PNG'
            risultati.append({
                'id': p.id,
                'nome': p.nome,
                'tipo': tipo,
                'tipo_display': tipo_mapping[tipo]
            })
        
        # Inventari NON personaggi (filtra usando personaggio__isnull=True)
        for inv in Inventario.objects.filter(personaggio__isnull=True):
            risultati.append({
                'id': inv.id,
                'nome': inv.nome,
                'tipo': 'INV',
                'tipo_display': tipo_mapping['INV']
            })
        
        # Manifesti
        for m in Manifesto.objects.all():
            risultati.append({
                'id': m.id,
                'nome': m.nome,
                'tipo': 'MAN',
                'tipo_display': tipo_mapping['MAN']
            })
        
        # Oggetti
        for o in Oggetto.objects.all():
            risultati.append({
                'id': o.id,
                'nome': o.nome,
                'tipo': 'OGG',
                'tipo_display': tipo_mapping['OGG']
            })
        
        # Tessiture
        for t in Tessitura.objects.all():
            risultati.append({
                'id': t.id,
                'nome': t.nome,
                'tipo': 'TES',
                'tipo_display': tipo_mapping['TES']
            })
        
        # Infusioni
        for i in Infusione.objects.all():
            risultati.append({
                'id': i.id,
                'nome': i.nome,
                'tipo': 'INF',
                'tipo_display': tipo_mapping['INF']
            })
        
        # Cerimoniali
        for c in Cerimoniale.objects.all():
            risultati.append({
                'id': c.id,
                'nome': c.nome,
                'tipo': 'CER',
                'tipo_display': tipo_mapping['CER']
            })
        
        return Response({'a_vista': risultati})
    
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
        
        # Filtra inventari per escludere personaggi (che ereditano da Inventario)
        inventari_non_personaggi = Inventario.objects.filter(
            personaggio__isnull=True
        ).only('id', 'nome')
        
        # Oggetti: serializza solo id e nome per performance
        oggetti_data = [{'id': o.id, 'nome': o.nome} for o in Oggetto.objects.only('id', 'nome')]
        
        return Response({
            'png': PersonaggioSerializer(png_queryset, many=True).data,
            'templates': MostroTemplateSerializer(MostroTemplate.objects.all(), many=True).data,
            'manifesti': ManifestoSerializer(Manifesto.objects.all(), many=True).data,
            'inventari': InventarioSerializer(inventari_non_personaggi, many=True).data,
            'tessiture': TessituraSerializer(Tessitura.objects.all().select_related('aura_richiesta', 'elemento_principale'), many=True).data,
            'infusioni': InfusioneSerializer(Infusione.objects.all().select_related('aura_richiesta', 'aura_infusione'), many=True).data,
            'cerimoniali': CerimonialeSerializer(Cerimoniale.objects.all(), many=True).data,
            'oggetti': oggetti_data,
            'staff': UserShortSerializer(User.objects.filter(is_staff=True).only('id', 'username', 'first_name', 'last_name'), many=True).data,
        })

class GiornoEventoViewSet(viewsets.ModelViewSet):
    queryset = GiornoEvento.objects.all()
    serializer_class = GiornoEventoSerializer
    permission_classes = [IsMasterOrReadOnly]

class QuestViewSet(viewsets.ModelViewSet):
    serializer_class = QuestSerializer
    permission_classes = [IsMasterOrReadOnly]
    
    def get_queryset(self):
        return Quest.objects.all().prefetch_related(
            'mostri_presenti',
            'png_richiesti',
            'viste_previste__manifesto',
            'viste_previste__inventario',
            'viste_previste__personaggio',
            'viste_previste__oggetto',
            'viste_previste__tessitura',
            'viste_previste__infusione',
            'viste_previste__cerimoniale',
            'staff_offgame',
            'fasi__tasks'
        )

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
    
    def perform_create(self, serializer):
        """
        Gestisce la creazione intelligente: riceve a_vista_id e tipo,
        e assegna al campo FK corretto cercando nel modello specifico.
        """
        from personaggi.models import (
            Personaggio, Inventario, Manifesto, 
            Oggetto, Tessitura, Infusione, Cerimoniale
        )
        
        a_vista_id = self.request.data.get('a_vista_id') or self.request.data.get('contentId')
        tipo = self.request.data.get('tipo')
        
        if not a_vista_id:
            raise ValidationError({'error': 'a_vista_id o contentId richiesto'})
        
        # Mappa tipo -> (modello, campo FK)
        type_mapping = {
            'PG': (Personaggio, 'personaggio'),
            'PNG': (Personaggio, 'personaggio'),
            'INV': (Inventario, 'inventario'),
            'OGG': (Oggetto, 'oggetto'),
            'TES': (Tessitura, 'tessitura'),
            'INF': (Infusione, 'infusione'),
            'CER': (Cerimoniale, 'cerimoniale'),
            'MAN': (Manifesto, 'manifesto')
        }
        
        if tipo not in type_mapping:
            raise ValidationError({'error': f'Tipo non valido: {tipo}'})
        
        model_class, field_name = type_mapping[tipo]
        
        try:
            vista_obj = model_class.objects.get(id=a_vista_id)
        except model_class.DoesNotExist:
            raise ValidationError({'error': f'{tipo} con id {a_vista_id} non trovato'})
        
        # Salva con il campo FK appropriato
        serializer.save(**{field_name: vista_obj})

    @action(detail=True, methods=['post'])
    def associa_qr(self, request, pk=None):
        """
        FUNZIONE CRUCIALE: Associa un QR fisico scansionato a questa vista prevista.
        Se force=true, disassocia il QR dall'elemento precedente.
        """
        vista_quest = self.get_object()
        qr_id = request.data.get('qr_id')
        force = request.data.get('force', False)
        
        try:
            qr = QrCode.objects.get(id=qr_id)
            
            # CONTROLLO: Se il QR è già associato ad un'altra vista, avvisa l'utente
            if qr.vista and not force:
                return Response({
                    'error': 'QR già associato',
                    'already_associated': True,
                    'current_vista': {
                        'id': qr.vista.id,
                        'nome': qr.vista.nome,
                        'tipo': qr.vista.__class__.__name__
                    },
                    'message': f'Questo QR è già associato a: {qr.vista.nome} ({qr.vista.__class__.__name__}). Confermare per disassociarlo?'
                }, status=409)  # 409 Conflict
            
            # Colleghiamo il QR alla "Vista" appropriata in base al tipo
            target_vista = (vista_quest.manifesto or vista_quest.inventario or 
                          vista_quest.personaggio or vista_quest.oggetto or
                          vista_quest.tessitura or vista_quest.infusione or 
                          vista_quest.cerimoniale)
            
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

class PublicEventiViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone gli eventi pubblici per la homepage.
    Mostra solo gli eventi futuri o recenti (ultimi 30 giorni).
    """
    serializer_class = EventoPubblicoSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        from django.utils import timezone
        from datetime import timedelta
        
        # Data di oggi e data limite per eventi passati (30 giorni fa)
        oggi = timezone.now()
        trenta_giorni_fa = oggi - timedelta(days=30)
        
        # Restituisce eventi che:
        # - Sono nel futuro (data_inizio >= oggi), O
        # - Sono finiti da meno di 30 giorni (data_fine >= 30 giorni fa)
        return Evento.objects.filter(
            data_fine__gte=trenta_giorni_fa
        ).order_by('data_inizio')

class PublicConfigurazioneSitoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone la configurazione del sito (info associazione per widget Chi Siamo).
    Singleton - restituisce sempre il record con pk=1.
    """
    serializer_class = ConfigurazioneSitoSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Assicura che il record esista
        ConfigurazioneSito.get_config()
        return ConfigurazioneSito.objects.all()


class PublicLinkSocialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone i link social attivi per il widget Social.
    """
    serializer_class = LinkSocialSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Restituisce solo i link attivi, ordinati per 'ordine'
        return LinkSocial.objects.filter(attivo=True).order_by('ordine', 'tipo')


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
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Supporta upload file con FormData
    
    def get_serializer_context(self):
        """Aggiunge il request al contesto per generare URL assoluti"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        """Imposta automaticamente il creatore quando viene creata un'immagine"""
        serializer.save(creatore=self.request.user)
    

class PublicWikiButtonWidgetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Espone i widget pulsanti per l'uso nelle pagine wiki.
    Accesso pubblico in lettura.
    """
    queryset = WikiButtonWidget.objects.all().prefetch_related('buttons')
    serializer_class = WikiButtonWidgetSerializer
    permission_classes = [permissions.AllowAny]


class StaffWikiButtonWidgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet per la gestione CRUD dei widget pulsanti (solo staff).
    Permette di creare, modificare ed eliminare widget pulsanti.
    """
    queryset = WikiButtonWidget.objects.all().prefetch_related('buttons')
    serializer_class = WikiButtonWidgetSerializer
    permission_classes = [IsMasterOrReadOnly]
    
    def perform_create(self, serializer):
        """Imposta il creatore al momento della creazione"""
        serializer.save(creatore=self.request.user)
    
    def perform_update(self, serializer):
        """Mantiene il creatore originale durante l'aggiornamento"""
        # Il creatore non viene modificato, viene mantenuto quello originale
        serializer.save()
    
    
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