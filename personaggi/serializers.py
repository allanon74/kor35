from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone

from .models import QrCode

from .models import (
    Abilita, PuntiCaratteristicaMovimento, Tier, Spell, Mattone, Punteggio, Tabella, TipologiaPersonaggio,
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
        fields = ('nome', 'sigla', 'tipo', 'icona_url', 'icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html', 'colore')

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
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True) # Serializza la @property
    aura = PunteggioSerializer(read_only=True) # Serializza il FK
    inventario_corrente = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Oggetto
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato', 
            'testo_formattato_personaggio', 
            'livello', 'aura', 
            'elementi', 'statistiche', 'statistiche_base',
            'inventario_corrente',
        )

class AttivataSerializer(serializers.ModelSerializer):
    statistiche_base = AttivataStatisticaBaseSerializer(source='attivatastatisticabase_set', many=True, read_only=True)
    elementi = AttivataElementoSerializer(source='attivataelemento_set', many=True, read_only=True) 
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)

    class Meta:
        model = Attivata
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato',
            'testo_formattato_personaggio', 
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

# --- NUOVO SERIALIZER (da aggiungere prima di PersonaggioDetailSerializer) ---
class TipologiaPersonaggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipologiaPersonaggio
        fields = ('nome', 'crediti_iniziali', 'caratteristiche_iniziali', 'giocante')


class PersonaggioDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo per il Personaggio, da usare
    per l'utente che possiede quel personaggio.
    """
    proprietario = serializers.StringRelatedField(read_only=True)
    
    # Proprietà Read-only
    crediti = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    punti_caratteristica = serializers.IntegerField(read_only=True)
    caratteristiche_base = serializers.JSONField(read_only=True) # Era 'caratteristiche_calcolate'
    modificatori_calcolati = serializers.JSONField(read_only=True) # Era 'modificatori_statistiche'
    TestoFormattatoPersonale = serializers.JSONField(read_only=True)
    tipologia = TipologiaPersonaggioSerializer(read_only=True)

    
    # M2M Posseduti
    abilita_possedute = AbilitaSerializer(many=True, read_only=True)
    attivate_possedute = AttivataSerializer(many=True, read_only=True) # Potrebbe essere pesante
    
    # Oggetti (da Inventario)
    oggetti = serializers.SerializerMethodField()
    attivate_possedute = serializers.SerializerMethodField()
    
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
            'tipologia', 
            'crediti', 
            'punti_caratteristica',
            'caratteristiche_base', # Nome aggiornato
            'modificatori_calcolati', # Nome aggiornato
            'abilita_possedute', 
            'oggetti', # Aggiornato a SerializerMethodField
            'attivate_possedute', # Aggiornato a SerializerMethodField
            'log_eventi', 'movimenti_credito',
            'transazioni_in_uscita_sospese', 'transazioni_in_entrata_sospese', 'TestoFormattatoPersonale',
        )
    
    def get_oggetti(self, personaggio):
        """
        Metodo per serializzare gli oggetti posseduti,
        iniettando il testo formattato calcolato.
        """
        # Pre-carica tutto il necessario per i calcoli in una volta
        # (La logica di get_oggetti() e get_testo_formattato_per_item 
        #  beneficerà delle cache e prefetch)
        oggetti_posseduti = personaggio.get_oggetti().prefetch_related(
            'statistiche_base__statistica', 'oggettostatistica_set__statistica',
            'oggettoelemento_set__elemento', 'aura'
        )
        
        # Ottieni i modificatori una sola volta (verranno messi in cache)
        personaggio.modificatori_calcolati
        
        risultati = []
        for obj in oggetti_posseduti:
            # Serializza l'oggetto
            dati_oggetto = OggettoSerializer(obj, context=self.context).data
            # Calcola e aggiungi il testo formattato specifico
            dati_oggetto['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(obj)
            risultati.append(dati_oggetto)
            
        return risultati

    def get_attivate_possedute(self, personaggio):
        """
        Metodo per serializzare le attivate possedute,
        iniettando il testo formattato calcolato.
        """
        attivate_possedute = personaggio.attivate_possedute.prefetch_related(
            'statistiche_base__statistica', 'attivataelemento_set__elemento'
        )
        
        # I modificatori dovrebbero essere già in cache da get_oggetti()
        personaggio.modificatori_calcolati
        
        risultati = []
        for att in attivate_possedute:
            dati_attivata = AttivataSerializer(att, context=self.context).data
            dati_attivata['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(att)
            risultati.append(dati_attivata)
            
        return risultati

class PersonaggioPublicSerializer(serializers.ModelSerializer):
    """Serializer pubblico per un Personaggio (Inventario)."""
    oggetti = OggettoSerializer(
        source='get_oggetti', 
        many=True, 
        read_only=True, 
        # source='inventario_ptr.oggetti',
        )
    
    class Meta:
        model = Personaggio
        # Mostra solo i campi pubblici (come un Inventario)
        fields = ('id', 'nome', 'testo', 'oggetti')
        


class CreditoMovimentoCreateSerializer(serializers.Serializer):
    """Serializer per validare la creazione di un movimento crediti."""
    importo = serializers.DecimalField(max_digits=10, decimal_places=2)
    descrizione = serializers.CharField(max_length=200)

    def create(self, validated_data):
        # Il personaggio viene passato dal contesto della vista
        personaggio = self.context['personaggio']
        movimento = CreditoMovimento.objects.create(
            personaggio=personaggio,
            **validated_data
        )
        return movimento

class TransazioneCreateSerializer(serializers.Serializer):
    """Serializer per validare la richiesta di una transazione."""
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    mittente_id = serializers.PrimaryKeyRelatedField(queryset=Inventario.objects.all())

    def validate(self, data):
        """
        Validazione incrociata: l'oggetto è davvero nell'inventario del mittente?
        """
        oggetto = data.get('oggetto_id')
        mittente = data.get('mittente_id')
        
        # Controlla se l'oggetto è attualmente in quell'inventario
        if oggetto.inventario_corrente != mittente:
            raise serializers.ValidationError(
                f"L'oggetto '{oggetto.nome}' non si trova nell'inventario di '{mittente.nome}'."
            )
        return data
    
    def create(self, validated_data):
        # Il richiedente (personaggio) viene passato dal contesto della vista
        richiedente_pg = self.context['richiedente']
        
        transazione = TransazioneSospesa.objects.create(
            oggetto=validated_data.get('oggetto_id'),
            mittente=validated_data.get('mittente_id'),
            richiedente=richiedente_pg
        )
        return transazione

class TransazioneConfermaSerializer(serializers.Serializer):
    """Serializer per validare l'azione di conferma/rifiuto."""
    azione = serializers.ChoiceField(choices=['accetta', 'rifiuta'])

    def save(self, **kwargs):
        # La transazione viene passata dal contesto della vista
        transazione = self.context['transazione']
        azione = self.validated_data['azione']
        
        if azione == 'accetta':
            transazione.accetta()
        elif azione == 'rifiuta':
            transazione.rifiuta()
            
        return transazione
    
class PersonaggioListSerializer(serializers.ModelSerializer):
    """
    Serializer leggero usato per elencare i personaggi.
    Mostra solo le informazioni chiave, non l'intero inventario o i log.
    """
    # Mostra il nome dell'utente invece del suo ID
    proprietario = serializers.StringRelatedField(read_only=True)
    tipologia = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Personaggio
        fields = (
            'id', 
            'nome', 
            'proprietario', 
            'tipologia',
            'data_nascita', 
            'data_morte'
        )
        
class PuntiCaratteristicaMovimentoCreateSerializer(serializers.Serializer):
    """Serializer per validare la creazione di un movimento PC."""
    importo = serializers.IntegerField()
    descrizione = serializers.CharField(max_length=200)

    def create(self, validated_data):
        personaggio = self.context['personaggio']
        movimento = PuntiCaratteristicaMovimento.objects.create(
            personaggio=personaggio,
            **validated_data
        )
        return movimento
    

class RubaSerializer(serializers.Serializer):
    """
    Serializer per l'azione "Ruba".
    Valida che il personaggio che ruba (richiedente) abbia i
    punteggi di caratteristica necessari per rubare l'oggetto.
    """
    # L'ID dell'oggetto che si sta tentando di rubare
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    
    # L'ID del personaggio che si sta derubando (mittente)
    target_personaggio_id = serializers.PrimaryKeyRelatedField(queryset=Personaggio.objects.all())

    def validate(self, data):
        richiedente = self.context.get('richiedente')
        if not richiedente:
            raise serializers.ValidationError("Nessun personaggio richiedente fornito.")
        
        oggetto = data.get('oggetto_id')
        target_personaggio = data.get('target_personaggio_id')

        # 1. Controlla che l'oggetto sia nell'inventario del target
        if not target_personaggio.inventario_ptr.oggetti.filter(id=oggetto.id).exists():
             raise serializers.ValidationError("L'oggetto non appartiene al personaggio target.")

        # 2. Logica di "Visibilità" (già gestita dal frontend, ma ricontrolliamo)
        # (Presumo tu abbia una funzione)
        # if not richiedente.puo_vedere_oggetto(oggetto):
        #    raise serializers.ValidationError("Non puoi vedere questo oggetto.")

        # 3. Logica Caratteristiche vs Elementi
        # (Questa è una logica di ESEMPIO, adattala ai tuoi modelli)
        
        # Presumo che Oggetto abbia una relazione ManyToMany 'elementi'
        # e che Punteggio (per le caratteristiche) abbia un campo 'elemento'
        
        elementi_oggetto = oggetto.elementi.all()
        caratteristiche_richiedente = richiedente.get_caratteristiche_finali() # Funzione da creare

        for elemento in elementi_oggetto:
            # Trova la caratteristica corrispondente
            try:
                caratteristica_associata = Punteggio.objects.get(
                    tipo='CARATTERISTICA', 
                    elemento=elemento
                )
            except Punteggio.DoesNotExist:
                raise serializers.ValidationError(f"Nessuna caratteristica associata all'elemento {elemento.nome}.")
            
            # Controlla se il PG ha punteggio in quella caratteristica
            punteggio_pg = caratteristiche_richiedente.get(caratteristica_associata.nome, 0)
            
            if punteggio_pg <= 0:
                raise serializers.ValidationError(
                    f"Punteggio insufficiente in '{caratteristica_associata.nome}' per rubare questo oggetto."
                )

        # Se tutti i controlli passano, i dati sono validi
        return data

    def save(self):
        richiedente = self.context['richiedente']
        oggetto = self.validated_data['oggetto_id']
        target_personaggio = self.validated_data['target_personaggio_id']
        
        # Esegui il furto (sposta l'oggetto)
        # Questa è la logica di trasferimento
        target_personaggio.inventario_ptr.rimuovi_oggetto(oggetto)
        richiedente.inventario_ptr.aggiungi_oggetto(oggetto)
        
        # TODO: Aggiungi log, ecc.
        
        return oggetto


class AcquisisciSerializer(serializers.Serializer):
    """
    Serializer per l'azione "Acquisisci".
    Collega un oggetto/attivata a un personaggio e scollega il QR code.
    """
    qrcode_id = serializers.UUIDField()
    
    def validate(self, data):
        richiedente = self.context.get('richiedente')
        if not richiedente:
            raise serializers.ValidationError("Nessun personaggio richiedente fornito.")
            
        try:
            qr_code = QrCode.objects.select_related('vista').get(id=data.get('qrcode_id'))
        except QrCode.DoesNotExist:
            raise serializers.ValidationError("QrCode non valido.")
            
        if not qr_code.vista:
            raise serializers.ValidationError("Questo QrCode non è collegato a nulla.")
            
        vista_obj = qr_code.vista
        
        if not (hasattr(vista_obj, 'oggetto') or hasattr(vista_obj, 'attivata')):
            raise serializers.ValidationError("Questo QrCode non punta a un oggetto o attivata acquisibile.")
        
        # Salva l'oggetto trovato nel contesto per il .save()
        self.context['qr_code'] = qr_code
        self.context['item'] = vista_obj.oggetto if hasattr(vista_obj, 'oggetto') else vista_obj.attivata
        
        return data

    def save(self):
        richiedente = self.context['richiedente']
        qr_code = self.context['qr_code']
        item = self.context['item']
        
        # 1. Aggiungi l'item al personaggio
        if isinstance(item, Oggetto):
            richiedente.inventario_ptr.aggiungi_oggetto(item)
        elif isinstance(item, Attivata):
            richiedente.attivate_possedute.add(item)
            
        # 2. Scollega il QrCode (come da richiesta)
        qr_code.vista = None
        qr_code.save()
        
        return item
    
    
    # In personaggi/serializers.py

class PunteggioSmallSerializer(serializers.ModelSerializer):
    """Serializer leggero per Punteggio (usato in requisiti e caratteristiche)."""
    class Meta:
        model = Punteggio
        fields = ('nome', 'sigla', 'colore')

class AbilitaRequisitoSmallSerializer(serializers.ModelSerializer):
    """Serializza i requisiti di punteggio per la master list."""
    requisito = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = abilita_requisito
        fields = ('requisito', 'valore')

class AbilitaSmallForPrereqSerializer(serializers.ModelSerializer):
    """Serializer super-leggero per i prerequisiti."""
    class Meta:
        model = Abilita
        fields = ('id', 'nome')

class AbilitaPrerequisitoSmallSerializer(serializers.ModelSerializer):
    """Serializza i prerequisiti di abilità per la master list."""
    prerequisito = AbilitaSmallForPrereqSerializer(read_only=True)
    class Meta:
        model = abilita_prerequisito
        fields = ('prerequisito',)

class AbilitaMasterListSerializer(serializers.ModelSerializer):
    """
    Serializer completo per la lista "master" delle abilità.
    Fornisce al frontend tutti i dati per filtri e popup.
    """
    caratteristica = PunteggioSmallSerializer(read_only=True)
    
    # Usiamo 'source' per puntare al related_name inverso
    requisiti = AbilitaRequisitoSmallSerializer(
        source='abilita_requisito_set', 
        many=True, 
        read_only=True
    )
    prerequisiti = AbilitaPrerequisitoSmallSerializer(
        source='abilita_prerequisiti', 
        many=True, 
        read_only=True
    )

    class Meta:
        model = Abilita
        fields = (
            'id', 
            'nome', 
            'descrizione', 
            'costo_pc', 
            'costo_crediti', 
            'caratteristica', 
            'requisiti', 
            'prerequisiti'
        )
        
class PunteggioDetailSerializer(serializers.ModelSerializer):
    """
    Serializza un Punteggio includendo le property calcolate
    per le icone HTML.
    """
    icona_html = serializers.CharField(read_only=True)
    icona_cerchio_html = serializers.CharField(read_only=True)
    icona_cerchio_inverted_html = serializers.CharField(read_only=True)

    class Meta:
        model = Punteggio
        fields = (
            'id', 
            'nome', 
            'sigla', 
            'tipo',
            'colore',
            'icona_html',
            'icona_cerchio_html',
            'icona_cerchio_inverted_html'
        )