from rest_framework import serializers
from rest_framework.authtoken.models import Token


from .models import (
    Abilita, Tier, Spell, Mattone, Punteggio, Tabella,
    abilita_tier, abilita_requisito, abilita_sbloccata,
    abilita_punteggio, abilita_prerequisito,
    spell_mattone, spell_elemento
)

from django.contrib.auth.models import User

from .models import (
    Oggetto, Attivata, Manifesto, A_vista, Inventario, 
    OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    OggettoElemento, AttivataElemento,
    OggettoInInventario, 
)
from .models import (
    Statistica, Personaggio, CreditoMovimento, 
    PersonaggioLog, TransazioneSospesa, 
)



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name' )
        extra_kwargs = {'password': {'write_only': True, 'required' : True, }}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.is_active = False
        # token = Token.objects.create(user=user)
        return user

class TierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tier
        fields = '__all__'


class TabellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tabella
        fields = '__all__'


class PunteggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punteggio
        fields = '__all__'

class AbilSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSerializer(many=False)
    tiers = TierSerializer(many=True)
    requisiti = PunteggioSerializer(many=True, required=False)
    punteggio_acquisito = PunteggioSerializer(many=True, required=False)
    class Meta:
        model = Abilita
        fields = '__all__'

class AbilitaSerializer(serializers.ModelSerializer):
    # caratteristica = PunteggioSerializer(many=False)
    # tiers = TierSerializer(many=True)
    # requisiti = PunteggioSerializer(many=True, required=False)
    # punteggio_acquisito = PunteggioSerializer(many=True, required=False)
    class Meta:
        model = Abilita
        fields = '__all__'

class AbilitaSmallSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSerializer(many=False)
    class Meta:
        model = Abilita
        fields = ("id", "nome", "caratteristica", "descrizione")



class AbilitaTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_tier
        fields = ['id', 'abilita', 'tabella', 'costo', 'ordine']

class AbilitaRequisitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_requisito
        fields = ['id', 'abilita', 'requisito', 'valore']

class AbilitaSbloccataSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_sbloccata
        fields = ['id', 'abilita', 'sbloccata']

class AbilitaPunteggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_punteggio
        fields = ['id', 'abilita', 'punteggio', 'valore']

class AbilitaPrerequisitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_prerequisito
        fields = ['id', 'abilita', 'prerequisito']

class SpellMattoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = spell_mattone
        fields = ['id', 'spell', 'mattone', 'valore']

class SpellElementoSerializer(serializers.ModelSerializer):
    class Meta:
        model = spell_elemento
        fields = ['id', 'spell', 'elemento']



class MattoneSerializer(serializers.ModelSerializer):
    elemento = PunteggioSerializer()
    aura = PunteggioSerializer()

    class Meta:
        model = Mattone
        fields = '__all__'

class SpellSerializer(serializers.ModelSerializer):
    mattoni = MattoneSerializer(many=True, read_only=True)

    class Meta:
        model = Spell
        fields = '__all__'



class AbilitaUpdateSerializer(serializers.ModelSerializer):
    requisiti = AbilitaRequisitoSerializer(many=True, required=False)
    punteggio_acquisito = AbilitaPunteggioSerializer(many=True, required=False)

    class Meta:
        model = Abilita
        fields = ['id', 'nome', 'descrizione', 'caratteristica', 'requisiti', 'punteggio_acquisito']

    def update(self, instance, validated_data):
        requisiti_data = validated_data.pop('requisiti', [])
        punteggi_data = validated_data.pop('punteggio_acquisito', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if requisiti_data:
            instance.requisiti.clear()
            for item in requisiti_data:
                abilita_requisito.objects.create(abilita=instance, **item)

        if punteggi_data:
            instance.punteggio_acquisito.clear()
            for item in punteggi_data:
                abilita_punteggio.objects.create(abilita=instance, **item)

        return instance

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
    inventario_corrente = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Oggetto
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato', 
            'livello', 'aura', 
            'elementi', 'statistiche', 'statistiche_base',
            'inventario_corrente',
        )

class AttivataSerializer(serializers.ModelSerializer):
    statistiche_base = AttivataStatisticaBaseSerializer(source='attivatastatisticabase_set', many=True, read_only=True)
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
        
        
class InventarioSerializer(serializers.ModelSerializer):
    """Serializza un Inventario base."""
    # Mostra gli oggetti attualmente nell'inventario
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)

    class Meta:
        model = Inventario
        fields = ('id', 'nome', 'testo', 'oggetti')


class AbilitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abilita
        fields = ('id', 'nome', 'descrizione')

class PersonaggioLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaggioLog
        fields = ('data', 'testo_log')

class CreditoMovimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditoMovimento
        fields = ('importo', 'descrizione', 'data')

class TransazioneSospesaSerializer(serializers.ModelSerializer):
    # Mostra i nomi invece degli ID per leggibilità
    oggetto = serializers.StringRelatedField(read_only=True)
    mittente = serializers.StringRelatedField(read_only=True)
    richiedente = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = TransazioneSospesa
        fields = ('id', 'oggetto', 'mittente', 'richiedente', 'data_richiesta', 'stato')

class PersonaggioDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo per il Personaggio, da usare
    per l'utente che possiede quel personaggio.
    """
    proprietario = serializers.StringRelatedField(read_only=True)
    
    # Proprietà Read-only
    crediti = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    caratteristiche_calcolate = serializers.JSONField(read_only=True)
    modificatori_statistiche = serializers.JSONField(read_only=True)
    TestoFormattatoPersonale = serializers.JSONField(read_only=True)
    
    # M2M Posseduti
    abilita_possedute = AbilitaSerializer(many=True, read_only=True)
    attivate_possedute = AttivataSerializer(many=True, read_only=True) # Potrebbe essere pesante
    
    # Oggetti (da Inventario)
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)
    
    # Log e Crediti
    log_eventi = PersonaggioLogSerializer(many=True, read_only=True)
    movimenti_credito = CreditoMovimentoSerializer(many=True, read_only=True)
    
    # Transazioni
    transazioni_in_uscita_sospese = TransazioneSospesaSerializer(many=True, read_only=True)
    transazioni_in_entrata_sospese = TransazioneSospesaSerializer(many=True, read_only=True)

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'proprietario', 'data_nascita', 'data_morte',
            'crediti', 'caratteristiche_calcolate', 'modificatori_statistiche',
            'TestoFormattatoPersonale', 'abilita_possedute', 'attivate_possedute',
            'oggetti', 'log_eventi', 'movimenti_credito',
            'transazioni_in_uscita_sospese', 'transazioni_in_entrata_sospese'
        )

class PersonaggioPublicSerializer(serializers.ModelSerializer):
    """Serializer pubblico per un Personaggio (Inventario)."""
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)
    
    class Meta:
        model = Personaggio
        # Mostra solo i campi pubblici (come un Inventario)
        fields = ('id', 'nome', 'testo', 'oggetti')
        