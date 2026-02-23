from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Evento, GiornoEvento, PaginaRegolamento, Quest, 
    MostroTemplate, AttaccoTemplate, 
    QuestMostro, PngAssegnato, QuestVista, StaffOffGame,
    QuestFase, QuestTask, WikiImmagine, WikiButtonWidget, WikiButton,
    ConfigurazioneSito, LinkSocial,
)
from personaggi.models import Abilita, Manifesto, Inventario, Punteggio, QrCode, Tabella, Tier
from personaggi.serializers import (
    ManifestoSerializer, InventarioSerializer, PersonaggioSerializer,
    AbilitaSerializer, PunteggioSerializer, TabellaSerializer, ModelloAuraSerializer,
    )

User = get_user_model()

class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

# --- MOSTRI ---

class AttaccoTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttaccoTemplate
        # fields = '__all__'
        exclude = ['template']

class MostroTemplateSerializer(serializers.ModelSerializer):
    attacchi = AttaccoTemplateSerializer(many=True, required=False)
    class Meta:
        model = MostroTemplate
        fields = '__all__'
    
    def create(self, validated_data):
        attacchi_data = validated_data.pop('attacchi', [])
        mostro = MostroTemplate.objects.create(**validated_data)
        
        for attacco in attacchi_data:
            if 'id' in attacco: del attacco['id']
            AttaccoTemplate.objects.create(template=mostro, **attacco)
            
        return mostro
    
    def update(self, instance, validated_data):
        attacchi_data = validated_data.pop('attacchi', None)
        
        # Aggiorna i campi standard del mostro
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Gestione Attacchi: Se forniti, sostituiamo la lista esistente
        if attacchi_data is not None:
            # Elimina i vecchi
            instance.attacchi.all().delete()
            # Crea i nuovi
            for attacco in attacchi_data:
                if 'id' in attacco: del attacco['id']
                AttaccoTemplate.objects.create(template=instance, **attacco)

        return instance

class QuestMostroSerializer(serializers.ModelSerializer):
    template_details = MostroTemplateSerializer(source='template', read_only=True)
    staffer_details = UserShortSerializer(source='staffer', read_only=True)
    
    class Meta:
        model = QuestMostro
        fields = '__all__'
        extra_kwargs = {
            'punti_vita': {'required': False, 'allow_null': True},
            'armatura': {'required': False, 'allow_null': True},
            'guscio': {'required': False, 'allow_null': True},
        }

# --- PNG E VISTE ---

class PngAssegnatoSerializer(serializers.ModelSerializer):
    personaggio_details = PersonaggioSerializer(source='personaggio', read_only=True)
    staffer_details = UserShortSerializer(source='staffer', read_only=True)

    class Meta:
        model = PngAssegnato
        fields = '__all__'

class QuestVistaSerializer(serializers.ModelSerializer):
    """
    Serializer per QuestVista con supporto completo per tutti i tipi a_vista.
    """
    manifesto_details = ManifestoSerializer(source='manifesto', read_only=True)
    inventario_details = InventarioSerializer(source='inventario', read_only=True)
    personaggio_details = serializers.SerializerMethodField()
    oggetto_details = serializers.SerializerMethodField()
    tessitura_details = serializers.SerializerMethodField()
    infusione_details = serializers.SerializerMethodField()
    cerimoniale_details = serializers.SerializerMethodField()
    
    class Meta:
        model = QuestVista
        fields = [
            'id', 'quest', 'tipo', 
            'manifesto', 'inventario', 'personaggio', 'oggetto', 
            'tessitura', 'infusione', 'cerimoniale',
            'qr_code', 
            'manifesto_details', 'inventario_details', 'personaggio_details',
            'oggetto_details', 'tessitura_details', 'infusione_details', 'cerimoniale_details'
        ]
    
    def get_personaggio_details(self, obj):
        if obj.personaggio:
            from personaggi.serializers import PersonaggioListSerializer
            return PersonaggioListSerializer(obj.personaggio).data
        return None
    
    def get_oggetto_details(self, obj):
        if obj.oggetto:
            # Import minimo per evitare cicli
            return {'id': obj.oggetto.id, 'nome': obj.oggetto.nome}
        return None
    
    def get_tessitura_details(self, obj):
        if obj.tessitura:
            return {'id': obj.tessitura.id, 'nome': obj.tessitura.nome}
        return None
    
    def get_infusione_details(self, obj):
        if obj.infusione:
            return {'id': obj.infusione.id, 'nome': obj.infusione.nome}
        return None
    
    def get_cerimoniale_details(self, obj):
        if obj.cerimoniale:
            return {'id': obj.cerimoniale.id, 'nome': obj.cerimoniale.nome}
        return None

# --- QUEST E EVENTI ---

class StaffOffGameSerializer(serializers.ModelSerializer):
    staffer_details = UserShortSerializer(source='staffer', read_only=True)

    class Meta:
        model = StaffOffGame
        fields = '__all__'

class QuestTaskSerializer(serializers.ModelSerializer):
    staffer_details = UserShortSerializer(source='staffer', read_only=True)
    personaggio_details = PersonaggioSerializer(source='personaggio', read_only=True)
    mostro_details = MostroTemplateSerializer(source='mostro_template', read_only=True)

    class Meta:
        model = QuestTask
        fields = '__all__'

class QuestFaseSerializer(serializers.ModelSerializer):
    tasks = QuestTaskSerializer(many=True, read_only=True)

    class Meta:
        model = QuestFase
        fields = '__all__'

class QuestSerializer(serializers.ModelSerializer):
    mostri_presenti = QuestMostroSerializer(many=True, read_only=True)
    png_richiesti = PngAssegnatoSerializer(many=True, read_only=True)
    viste_previste = QuestVistaSerializer(many=True, read_only=True)
    staff_offgame = StaffOffGameSerializer(many=True, read_only=True)
    # Aggiungi qui il campo fasi
    fasi = QuestFaseSerializer(many=True, read_only=True)

    class Meta:
        model = Quest
        fields = '__all__'

class GiornoEventoSerializer(serializers.ModelSerializer):
    quests = QuestSerializer(many=True, read_only=True)
    class Meta:
        model = GiornoEvento
        fields = '__all__'

class EventoSerializer(serializers.ModelSerializer):
    giorni = GiornoEventoSerializer(many=True, read_only=True)
    
    # Questi campi permettono al frontend di vedere i nomi (UserCheck e Users icone)
    staff_details = UserShortSerializer(source='staff_assegnato', many=True, read_only=True)
    partecipanti_details = PersonaggioSerializer(source='partecipanti', many=True, read_only=True)

    class Meta:
        model = Evento
        fields = [
            'id', 'titolo', 'sinossi', 'data_inizio', 'data_fine', 
            'luogo', 'pc_guadagnati', 'staff_assegnato', 'partecipanti',
            'giorni', 'staff_details', 'partecipanti_details'
        ]

class EventoPubblicoSerializer(serializers.ModelSerializer):
    """
    Serializer semplificato per gli eventi pubblici (homepage).
    Mostra solo le informazioni essenziali senza dati sensibili.
    """
    class Meta:
        model = Evento
        fields = ['id', 'titolo', 'sinossi', 'data_inizio', 'data_fine', 'luogo']
        
class PaginaRegolamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaginaRegolamento
        fields = '__all__'
        
class PaginaRegolamentoSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaginaRegolamento
        fields = [
            'id', 'titolo', 'slug', 
            'parent', 'ordine', 'public', 'visibile_solo_staff',
            ]

class AbilitaWikiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abilita
        fields = ['id', 'nome', 'descrizione', 'costo', 'tier'] # Aggiungi i campi che servono

class WikiTabellaSerializer(serializers.ModelSerializer):
    # FONDAMENTALE: Sovrascriviamo il campo per usare il serializer invece degli ID
    # Verifica il nome del campo nel model Tabella: è 'abilita' o 'abilita_selezionate'?
    # Se nel model è: abilita = ManyToManyField(...)
    abilita = AbilitaWikiSerializer(many=True, read_only=True) 

    class Meta:
        model = Tabella
        fields = ['id', 'titolo', 'descrizione', 'abilita']

class WikiAuraSerializer(ModelloAuraSerializer):
    pass
        
class PunteggioWikiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punteggio  # Il tuo modello delle Statistiche
        fields = ['id', 'nome', 'sigla', 'colore', 'icona_url', 'ordine',]
        
class AbilitaTierSerializer(serializers.ModelSerializer):
    costo = serializers.SerializerMethodField()
    caratteristica = PunteggioWikiSerializer(read_only=True)
    class Meta:
        model = Abilita
        fields = ['id', 'nome', 'descrizione', 'costo', 'caratteristica'] 
        
    def get_costo(self, obj):
        if obj.costo_pc is not None and obj.costo_pc > 0:
            return f"{obj.costo_pc} PC"
        return f"{obj.costo_crediti} Cr"

class WikiTierSerializer(serializers.ModelSerializer):
    # FONDAMENTALE: Recuperiamo le abilità figlie di questo Tier
    # Se nel model Abilita c'è: tier = ForeignKey(Tier, related_name='abilita_set')
    # Verifica se il related_name è 'abilita_set', 'abilities' o altro.
    abilita = AbilitaTierSerializer(many=True, read_only=True)

    class Meta:
        model = Tier
        fields = ['id', 'nome', 'descrizione', 'tipo', 'abilita']

class WikiImmagineSerializer(serializers.ModelSerializer):
    """
    Serializer per le immagini wiki.
    Include l'URL dell'immagine per il frontend.
    """
    immagine_url = serializers.SerializerMethodField()
    creatore_nome = serializers.CharField(source='creatore.username', read_only=True)
    
    class Meta:
        model = WikiImmagine
        fields = [
            'id', 'titolo', 'descrizione', 'immagine', 'immagine_url',
            'data_creazione', 'data_modifica', 'creatore', 'creatore_nome',
            'larghezza_max', 'allineamento'
        ]
        read_only_fields = ['data_creazione', 'data_modifica', 'creatore']
    
    def get_immagine_url(self, obj):
        """Restituisce l'URL completo dell'immagine"""
        if obj.immagine:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.immagine.url)
            return obj.immagine.url
        return None


class WikiButtonSerializer(serializers.ModelSerializer):
    """
    Serializer per i singoli pulsanti del widget
    """
    class Meta:
        model = WikiButton
        fields = [
            'id', 'title', 'description', 'subtext', 'icon',
            'style', 'size', 'color_preset',
            'link_type', 'wiki_slug', 'app_route', 'ordine'
        ]


class WikiButtonWidgetSerializer(serializers.ModelSerializer):
    """
    Serializer per i widget pulsanti.
    Include la lista dei pulsanti annidati.
    """
    buttons = WikiButtonSerializer(many=True)
    creatore_nome = serializers.CharField(source='creatore.username', read_only=True)
    
    class Meta:
        model = WikiButtonWidget
        fields = [
            'id', 'title', 'buttons',
            'data_creazione', 'data_modifica', 'creatore', 'creatore_nome'
        ]
        read_only_fields = ['data_creazione', 'data_modifica', 'creatore']
    
    def create(self, validated_data):
        """Crea widget e pulsanti annidati"""
        buttons_data = validated_data.pop('buttons', [])
        widget = WikiButtonWidget.objects.create(**validated_data)
        
        for button_data in buttons_data:
            WikiButton.objects.create(widget=widget, **button_data)
        
        return widget
    
    def update(self, instance, validated_data):
        """Aggiorna widget e pulsanti annidati"""
        buttons_data = validated_data.pop('buttons', None)
        
        # Aggiorna campi del widget
        instance.title = validated_data.get('title', instance.title)
        instance.save()
        
        # Se ci sono pulsanti da aggiornare
        if buttons_data is not None:
            # Elimina i pulsanti esistenti e ricreali
            instance.buttons.all().delete()
            
            for button_data in buttons_data:
                WikiButton.objects.create(widget=instance, **button_data)
        
        return instance


class ConfigurazioneSitoSerializer(serializers.ModelSerializer):
    """
    Serializer per la configurazione del sito
    """
    class Meta:
        model = ConfigurazioneSito
        fields = [
            'id', 'nome_associazione', 'descrizione_breve', 'anno_fondazione',
            'indirizzo', 'citta', 'cap', 'provincia', 'nazione',
            'email', 'pec', 'telefono', 'ultima_modifica'
        ]
        read_only_fields = ['id', 'ultima_modifica']


class LinkSocialSerializer(serializers.ModelSerializer):
    """
    Serializer per i link social
    """
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = LinkSocial
        fields = ['id', 'tipo', 'tipo_display', 'nome_visualizzato', 'url', 'descrizione', 'ordine', 'attivo']
        read_only_fields = ['id']