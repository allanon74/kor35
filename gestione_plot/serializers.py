from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Evento, GiornoEvento, Quest, 
    MostroTemplate, AttaccoTemplate, 
    QuestMostro, PngAssegnato, QuestVista
)
from personaggi.models import Manifesto, Inventario, QrCode
from personaggi.serializers import ManifestoSerializer, InventarioSerializer, PersonaggioSerializer

User = get_user_model()

class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

# --- MOSTRI ---
class AttaccoTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttaccoTemplate
        fields = '__all__'

class MostroTemplateSerializer(serializers.ModelSerializer):
    attacchi = AttaccoTemplateSerializer(many=True, read_only=True)
    class Meta:
        model = MostroTemplate
        fields = '__all__'

class QuestMostroSerializer(serializers.ModelSerializer):
    template_details = MostroTemplateSerializer(source='template', read_only=True)
    staffer_details = UserShortSerializer(source='staffer', read_only=True)
    
    class Meta:
        model = QuestMostro
        fields = '__all__'

# --- PNG E VISTE ---
class PngAssegnatoSerializer(serializers.ModelSerializer):
    personaggio_details = PersonaggioSerializer(source='personaggio', read_only=True)
    staffer_details = UserShortSerializer(source='staffer', read_only=True)

    class Meta:
        model = PngAssegnato
        fields = '__all__'

class QuestVistaSerializer(serializers.ModelSerializer):
    # Dettagli opzionali per Manifesto/Inventario/QR
    class Meta:
        model = QuestVista
        fields = '__all__'

# --- QUEST E EVENTI ---
class QuestSerializer(serializers.ModelSerializer):
    mostri_presenti = QuestMostroSerializer(many=True, read_only=True)
    png_richiesti = PngAssegnatoSerializer(many=True, read_only=True)
    viste_previste = QuestVistaSerializer(many=True, read_only=True)

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
    class Meta:
        model = Evento
        fields = '__all__'
        
class QuestVistaSerializer(serializers.ModelSerializer):
    # Includiamo i dettagli per l'anteprima nel setup
    manifesto_details = ManifestoSerializer(source='manifesto', read_only=True)
    inventario_details = InventarioSerializer(source='inventario', read_only=True)
    
    class Meta:
        model = QuestVista
        fields = [
            'id', 'quest', 'tipo', 'manifesto', 'inventario', 
            'qr_code', 'manifesto_details', 'inventario_details'
        ]