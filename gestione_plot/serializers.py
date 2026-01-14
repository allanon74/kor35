from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Evento, GiornoEvento, PaginaRegolamento, Quest, 
    MostroTemplate, AttaccoTemplate, 
    QuestMostro, PngAssegnato, QuestVista, StaffOffGame,
    QuestFase, QuestTask,
)
from personaggi.models import Abilita, Manifesto, Inventario, QrCode, Tabella, Tier
from personaggi.serializers import (
    ManifestoSerializer, InventarioSerializer, PersonaggioSerializer,
    AbilitaSerializer, TabellaSerializer, ModelloAuraSerializer,
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
    Spostato sopra QuestSerializer per permettere l'inclusione corretta dei dettagli.
    Risolve il problema del nome 'Manifesto' mancante.
    """
    manifesto_details = ManifestoSerializer(source='manifesto', read_only=True)
    inventario_details = InventarioSerializer(source='inventario', read_only=True)
    
    class Meta:
        model = QuestVista
        fields = [
            'id', 'quest', 'tipo', 'manifesto', 'inventario', 
            'qr_code', 'manifesto_details', 'inventario_details'
        ]

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
        
class PaginaRegolamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaginaRegolamento
        fields = '__all__'
        
class PaginaRegolamentoSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaginaRegolamento
        fields = [
            'id', 'titolo', 'slug', 
            'parent', 'ordine'
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
        
class AbilitaTierSerializer(serializers.ModelSerializer):
    costo = serializers.SerializerMethodField()
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