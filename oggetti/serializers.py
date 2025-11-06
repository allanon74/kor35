from rest_framework import serializers
from .models import (
    Oggetto, Attivata, Manifesto, A_vista,
    OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    OggettoElemento, AttivataElemento # Vedi NOTA IMPORTANTE
)
from personaggi.models import Statistica, Punteggio

# --- Serializers per i dati annidati (le pivot) ---

class StatisticaSerializer(serializers.ModelSerializer):
    """Serializza i campi chiave di una Statistica."""
    class Meta:
        model = Statistica
        # Mostra i campi utili per l'app React
        fields = ('nome', 'sigla', 'parametro')

class PunteggioSerializer(serializers.ModelSerializer):
    """Serializza i campi chiave di un Punteggio (per gli Elementi)."""
    class Meta:
        model = Punteggio
        fields = ('nome', 'sigla')

class OggettoStatisticaSerializer(serializers.ModelSerializer):
    """Serializza la pivot Modificatori di Oggetto."""
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = OggettoStatistica
        fields = ('statistica', 'valore')

class OggettoStatisticaBaseSerializer(serializers.ModelSerializer):
    """Serializza la pivot Valori Base di Oggetto."""
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = OggettoStatisticaBase
        fields = ('statistica', 'valore_base')

class AttivataStatisticaBaseSerializer(serializers.ModelSerializer):
    """Serializza la pivot Valori Base di Attivata."""
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = AttivataStatisticaBase
        fields = ('statistica', 'valore_base')

class OggettoElementoSerializer(serializers.ModelSerializer):
    """Serializza la pivot Elementi di Oggetto."""
    elemento = PunteggioSerializer(read_only=True)
    class Meta:
        model = OggettoElemento
        fields = ('elemento',)

class AttivataElementoSerializer(serializers.ModelSerializer):
    """
    Serializza la pivot Elementi di Attivata.
    (Vedi NOTA IMPORTANTE sul modello AttivataElemento)
    """
    elemento = PunteggioSerializer(read_only=True)
    class Meta:
        model = AttivataElemento # Presuppone che questo modello esista
        fields = ('elemento',)


# --- Serializers Principali ---

class OggettoSerializer(serializers.ModelSerializer):
    # Usa 'source' per puntare al related_name inverso del modello through
    statistiche = OggettoStatisticaSerializer(source='oggettostatistica_set', many=True, read_only=True)
    statistiche_base = OggettoStatisticaBaseSerializer(source='oggettostatisticabase_set', many=True, read_only=True)
    elementi = OggettoElementoSerializer(source='oggettoelemento_set', many=True, read_only=True)
    
    # Serializza la @property
    TestoFormattato = serializers.CharField(read_only=True) 
    livello = serializers.IntegerField(read_only=True) # Serializza la @property
    aura = PunteggioSerializer(read_only=True) # Serializza il FK

    class Meta:
        model = Oggetto
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato', 
            'livello', 'aura', 
            'elementi', 'statistiche', 'statistiche_base'
        )

class AttivataSerializer(serializers.ModelSerializer):
    statistiche_base = AttivataStatisticaBaseSerializer(source='attivatastatisticabase_set', many=True, read_only=True)
    # Vedi NOTA IMPORTANTE
    elementi = AttivataElementoSerializer(source='attivataelemento_set', many=True, read_only=True) 
    TestoFormattato = serializers.CharField(read_only=True)
    livello = serializers.IntegerField(read_only=True)

    class Meta:
        model = Attivata
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato',
            'livello', 'elementi', 'statistiche_base'
        )

class ManifestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manifesto
        fields = ('id', 'nome', 'testo')

class A_vistaSerializer(serializers.ModelSerializer):
    """Serializer di fallback se non è nessuna delle sottoclassi."""
    class Meta:
        model = A_vista
        fields = ('id', 'nome', 'testo')