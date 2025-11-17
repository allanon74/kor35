from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.conf import settings
from django.utils.html import format_html

# Importa i modelli e le funzioni helper
from .models import (
    AbilitaStatistica, _get_icon_color_from_bg, QrCode, Abilita, PuntiCaratteristicaMovimento, Tier, 
    Spell, Mattone, Punteggio, Tabella, TipologiaPersonaggio, abilita_tier, 
    abilita_requisito, abilita_sbloccata, abilita_punteggio, abilita_prerequisito, 
    spell_mattone, spell_elemento, Oggetto, Attivata, Manifesto, A_vista, 
    Inventario, OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    OggettoElemento, AttivataElemento, OggettoInInventario, Statistica, Personaggio, 
    CreditoMovimento, PersonaggioLog, TransazioneSospesa
)
from django.contrib.auth.models import User

#
# --- Serializer di Base e Specifici per l'App React ---
# (Definiti prima, così possono essere usati da altri)
#

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name' )
        extra_kwargs = {'password': {'write_only': True, 'required' : True, }}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.is_active = False
        return user

class TierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tier
        fields = '__all__'

class TabellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tabella
        fields = '__all__'

class StatisticaSerializer(serializers.ModelSerializer):
    """Serializza i campi chiave di una Statistica."""
    class Meta:
        model = Statistica
        fields = ('nome', 'sigla', 'parametro')
        
class PunteggioSerializer(serializers.ModelSerializer):
    """Serializza i campi chiave di un Punteggio (per gli Elementi)."""
    class Meta:
        model = Punteggio
        fields = ('nome', 'sigla', 'tipo', 'icona_url', 'icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html', 'colore')

class PunteggioSmallSerializer(serializers.ModelSerializer):
    """Serializer leggero per Punteggio (usato nei serializer delle abilità)."""
    class Meta:
        model = Punteggio
        fields = ('id', 'nome', 'sigla', 'colore')
        
class AbilitaPunteggioSmallSerializer(serializers.ModelSerializer):
    """Serializza i punteggi dati da un'abilità (es. +1 Forza)."""
    punteggio = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = abilita_punteggio
        fields = ('punteggio', 'valore')

class AbilitaStatisticaSmallSerializer(serializers.ModelSerializer):
    """Serializza le statistiche modificate da un'abilità (es. +5 PV)."""
    statistica = PunteggioSmallSerializer(read_only=True) # La statistica È un punteggio
    class Meta:
        model = AbilitaStatistica
        fields = ('statistica', 'valore', 'tipo_modificatore')

class PunteggioDetailSerializer(serializers.ModelSerializer):
    """
    Serializza un Punteggio includendo le property calcolate
    per le icone HTML con URL assoluti (per il PunteggioDisplay React).
    """
    icona_html = serializers.SerializerMethodField()
    icona_cerchio_html = serializers.SerializerMethodField()
    icona_cerchio_inverted_html = serializers.SerializerMethodField()
    is_primaria = serializers.SerializerMethodField()
    valore_predefinito = serializers.SerializerMethodField()
    parametro = serializers.SerializerMethodField()

    class Meta:
        model = Punteggio
        fields = (
            'id', 'nome', 'sigla', 'tipo', 'colore',
            'icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html',
            'is_primaria', 'valore_predefinito', 'parametro',
        )

    def get_base_url(self):
        """Ottiene il base URL dal contesto della request."""
        request = self.context.get('request')
        if request:
            return f"{request.scheme}://{request.get_host()}"
        return ""

    def get_icona_url_assoluto(self, obj):
        """Helper per generare l'URL assoluto dell'icona."""
        if not obj.icona:
            return None
        base_url = self.get_base_url()
        
        media_url = settings.MEDIA_URL
        if not media_url:
            media_url = "/media/"
        # Gestisce correttamente gli slash
        if media_url.startswith('/'):
            media_url = media_url[1:]
        if media_url and not media_url.endswith('/'):
             media_url = f"{media_url}/"
            
        icona_path = str(obj.icona)
        if icona_path.startswith('/'):
            icona_path = icona_path[1:]
            
        return f"{base_url}/{media_url}{icona_path}"

    def get_icona_html(self, obj):
        url = self.get_icona_url_assoluto(obj)
        if not url or not obj.colore:
            return ""
        style = (
            f"width: 24px; height: 24px; background-color: {obj.colore}; "
            f"mask-image: url({url}); -webkit-mask-image: url({url}); "
            f"mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; "
            f"mask-size: contain; -webkit-mask-size: contain; "
            f"display: inline-block; vertical-align: middle;"
        )
        return format_html('<div style="{}"></div>', style)

    def get_icona_cerchio_html(self, obj):
        return self._get_icona_cerchio(obj, inverted=False)

    def get_icona_cerchio_inverted_html(self, obj):
        return self._get_icona_cerchio(obj, inverted=True)

    def _get_icona_cerchio(self, obj, inverted=False):
        url_icona_locale = self.get_icona_url_assoluto(obj)
        if not url_icona_locale or not obj.colore:
            return ""
        colore_sfondo = obj.colore
        colore_icona_contrasto = _get_icon_color_from_bg(colore_sfondo) 
        if inverted:
            colore_icona_contrasto = obj.colore
            colore_sfondo = _get_icon_color_from_bg(colore_sfondo)
        stile_cerchio = (
            f"display: inline-block; width: 30px; height: 30px; "
            f"background-color: {colore_sfondo}; border-radius: 50%; "
            f"vertical-align: middle; text-align: center; line-height: 30px;"
        )
        stile_icona_maschera = (
            f"display: inline-block; width: 24px; height: 24px; "
            f"vertical-align: middle; background-color: {colore_icona_contrasto}; "
            f"mask-image: url({url_icona_locale}); -webkit-mask-image: url({url_icona_locale}); "
            f"mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; "
            f"mask-size: contain; -webkit-mask-size: contain;"
        )
        return format_html(
            '<div style="{}"><div style="{}"></div></div>',
            stile_cerchio,
            stile_icona_maschera
        )

    def get_is_primaria(self, obj):
        # Controlla se l'oggetto Punteggio è una Statistica e ha il flag
        if hasattr(obj, 'statistica') and obj.statistica.is_primaria:
            return True
        return False

    def get_valore_predefinito(self, obj):
        # Restituisce il valore base solo se è una Statistica
        if hasattr(obj, 'statistica'):
            return obj.statistica.valore_base_predefinito
        return 0 # Le Caratteristiche hanno base 0

    def get_parametro(self, obj):
        # Restituisce il parametro (es. "pv") solo se è una Statistica
        if hasattr(obj, 'statistica'):
            return obj.statistica.parametro
        return None
#
# --- Serializer Vecchi (Aggiornati per usare PunteggioSmallSerializer) ---
# (Questi sono usati dall'Admin o da vecchie view, li teniamo per compatibilità)
#

class AbilSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(many=False) # <-- CORRETTO
    tiers = TierSerializer(many=True)
    requisiti = PunteggioSmallSerializer(many=True, required=False) # <-- CORRETTO
    punteggio_acquisito = PunteggioSmallSerializer(many=True, required=False) # <-- CORRETTO
    class Meta:
        model = Abilita
        fields = '__all__'

class AbilitaSmallSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(many=False) # <-- CORRETTO
    class Meta:
        model = Abilita
        fields = ("id", "nome", "caratteristica", "descrizione")

class MattoneSerializer(serializers.ModelSerializer):
    elemento = PunteggioSmallSerializer() # <-- CORRETTO
    aura = PunteggioSmallSerializer() # <-- CORRETTO
    class Meta:
        model = Mattone
        fields = '__all__'

class SpellSerializer(serializers.ModelSerializer):
    mattoni = MattoneSerializer(many=True, read_only=True)
    class Meta:
        model = Spell
        fields = '__all__'

#
# --- Serializer "Through" (per admin/debug) ---
#

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

#
# --- Serializer Specifici per App React (continuazione) ---
#

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
    Serializer completo per la lista "master" delle abilità (usato dalla view).
    """
    caratteristica = PunteggioSmallSerializer(read_only=True)
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
    
    punteggi_assegnati = AbilitaPunteggioSmallSerializer(
        source='abilita_punteggio_set', 
        many=True, 
        read_only=True
    )
    statistiche_modificate = AbilitaStatisticaSmallSerializer(
        source='abilitastatistica_set', 
        many=True, 
        read_only=True
    )
    
    class Meta:
        model = Abilita
        fields = (
            'id', 'nome', 'descrizione', 'costo_pc', 'costo_crediti', 
            'caratteristica', 'requisiti', 'prerequisiti',
            'punteggi_assegnati', 'statistiche_modificate',
        )

# --- QUESTA È LA CLASSE CORRETTA PER LE ABILITÀ POSSEDUTE ---
# (La vecchia 'AbilitaSerializer' generica è stata rimossa)
class AbilitaSerializer(serializers.ModelSerializer):
    """
    Serializer per le 'abilita_possedute' del personaggio (usato in PersonaggioDetailSerializer).
    """
    caratteristica = PunteggioSmallSerializer(read_only=True) 
    class Meta:
        model = Abilita
        # Aggiungi 'caratteristica' alla lista dei campi
        fields = ('id', 'nome', 'descrizione', 'caratteristica')


# --- Serializer Oggetti/Attivate (Pannello QR) ---

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
    elemento = PunteggioSmallSerializer(read_only=True) # <-- CORRETTO
    class Meta:
        model = OggettoElemento
        fields = ('elemento',)

class AttivataElementoSerializer(serializers.ModelSerializer):
    """Serializza la pivot Elementi di Attivata."""
    elemento = PunteggioSmallSerializer(read_only=True) # <-- CORRETTO
    class Meta:
        model = AttivataElemento 
        fields = ('elemento',)

class OggettoSerializer(serializers.ModelSerializer):
    statistiche = OggettoStatisticaSerializer(source='oggettostatistica_set', many=True, read_only=True)
    statistiche_base = OggettoStatisticaBaseSerializer(source='oggettostatisticabase_set', many=True, read_only=True)
    elementi = OggettoElementoSerializer(source='oggettoelemento_set', many=True, read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    aura = PunteggioSmallSerializer(read_only=True) # <-- CORRETTO
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
    class Meta:
        model = A_vista
        fields = ('id', 'nome', 'testo')
        
class InventarioSerializer(serializers.ModelSerializer):
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)
    class Meta:
        model = Inventario
        fields = ('id', 'nome', 'testo', 'oggetti')

class PersonaggioLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaggioLog
        fields = ('data', 'testo_log')

class CreditoMovimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditoMovimento
        fields = ('importo', 'descrizione', 'data')

class TransazioneSospesaSerializer(serializers.ModelSerializer):
    oggetto = serializers.StringRelatedField(read_only=True)
    mittente = serializers.StringRelatedField(read_only=True)
    richiedente = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = TransazioneSospesa
        fields = ('id', 'oggetto', 'mittente', 'richiedente', 'data_richiesta', 'stato')

class TipologiaPersonaggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipologiaPersonaggio
        fields = ('nome', 'crediti_iniziali', 'caratteristiche_iniziali', 'giocante')

class PersonaggioDetailSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    crediti = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    punti_caratteristica = serializers.IntegerField(read_only=True)
    caratteristiche_base = serializers.JSONField(read_only=True) 
    modificatori_calcolati = serializers.JSONField(read_only=True) 
    TestoFormattatoPersonale = serializers.JSONField(read_only=True)
    tipologia = TipologiaPersonaggioSerializer(read_only=True)
    
    # --- CAMPI CHIAVE ---
    # Ora usa l'UNICA E CORRETTA AbilitaSerializer (definita sopra)
    abilita_possedute = AbilitaSerializer(many=True, read_only=True) 
    
    oggetti = serializers.SerializerMethodField()
    attivate_possedute = serializers.SerializerMethodField()
    # ---
    
    log_eventi = PersonaggioLogSerializer(many=True, read_only=True)
    movimenti_credito = CreditoMovimentoSerializer(many=True, read_only=True)
    transazioni_in_uscita_sospese = TransazioneSospesaSerializer(many=True, read_only=True)
    transazioni_in_entrata_sospese = TransazioneSospesaSerializer(many=True, read_only=True)

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'proprietario', 'data_nascita', 'data_morte',
            'tipologia', 'crediti', 'punti_caratteristica',
            'caratteristiche_base', 'modificatori_calcolati', 
            'abilita_possedute', 'oggetti', 'attivate_possedute', 
            'log_eventi', 'movimenti_credito',
            'transazioni_in_uscita_sospese', 'transazioni_in_entrata_sospese', 
            'TestoFormattatoPersonale',
        )
    
    def get_oggetti(self, personaggio):
        oggetti_posseduti = personaggio.get_oggetti().prefetch_related(
            'statistiche_base__statistica', 'oggettostatistica_set__statistica',
            'oggettoelemento_set__elemento', 'aura'
        )
        personaggio.modificatori_calcolati # Assicura che la cache sia piena
        risultati = []
        for obj in oggetti_posseduti:
            dati_oggetto = OggettoSerializer(obj, context=self.context).data 
            dati_oggetto['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(obj)
            risultati.append(dati_oggetto)
        return risultati

    def get_attivate_possedute(self, personaggio):
        attivate_possedute = personaggio.attivate_possedute.prefetch_related(
            'statistiche_base__statistica', 'attivataelemento_set__elemento'
        )
        personaggio.modificatori_calcolati # La cache dovrebbe essere già piena
        risultati = []
        for att in attivate_possedute:
            dati_attivata = AttivataSerializer(att, context=self.context).data 
            dati_attivata['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(att)
            risultati.append(dati_attivata)
        return risultati

class PersonaggioPublicSerializer(serializers.ModelSerializer):
    oggetti = OggettoSerializer(
        source='get_oggetti', 
        many=True, 
        read_only=True,
        )
    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'testo', 'oggetti')

#
# --- Serializer per Azioni (POST/PUT) ---
#

class CreditoMovimentoCreateSerializer(serializers.Serializer):
    importo = serializers.DecimalField(max_digits=10, decimal_places=2)
    descrizione = serializers.CharField(max_length=200)
    def create(self, validated_data):
        personaggio = self.context['personaggio']
        movimento = CreditoMovimento.objects.create(
            personaggio=personaggio, **validated_data
        )
        return movimento

class TransazioneCreateSerializer(serializers.Serializer):
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    mittente_id = serializers.PrimaryKeyRelatedField(queryset=Inventario.objects.all())
    def validate(self, data):
        oggetto = data.get('oggetto_id')
        mittente = data.get('mittente_id')
        if oggetto.inventario_corrente != mittente:
            raise serializers.ValidationError(
                f"L'oggetto '{oggetto.nome}' non si trova nell'inventario di '{mittente.nome}'."
            )
        return data
    def create(self, validated_data):
        richiedente_pg = self.context['richiedente']
        transazione = TransazioneSospesa.objects.create(
            oggetto=validated_data.get('oggetto_id'),
            mittente=validated_data.get('mittente_id'),
            richiedente=richiedente_pg
        )
        return transazione

class TransazioneConfermaSerializer(serializers.Serializer):
    azione = serializers.ChoiceField(choices=['accetta', 'rifiuta'])
    def save(self, **kwargs):
        transazione = self.context['transazione']
        azione = self.validated_data['azione']
        if azione == 'accetta':
            transazione.accetta()
        elif azione == 'rifiuta':
            transazione.rifiuta()
        return transazione
    
class PersonaggioListSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    tipologia = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'proprietario', 'tipologia',
            'data_nascita', 'data_morte'
        )
        
class PuntiCaratteristicaMovimentoCreateSerializer(serializers.Serializer):
    importo = serializers.IntegerField()
    descrizione = serializers.CharField(max_length=200)
    def create(self, validated_data):
        personaggio = self.context['personaggio']
        movimento = PuntiCaratteristicaMovimento.objects.create(
            personaggio=personaggio, **validated_data
        )
        return movimento
    
class RubaSerializer(serializers.Serializer):
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    target_personaggio_id = serializers.PrimaryKeyRelatedField(queryset=Personaggio.objects.all())
    
    def validate(self, data):
        richiedente = self.context.get('richiedente')
        if not richiedente:
            raise serializers.ValidationError("Nessun personaggio richiedente fornito.")
        
        oggetto = data.get('oggetto_id')
        target_personaggio = data.get('target_personaggio_id')

        # Correzione: get_oggetti() è un metodo, non un related manager
        if not target_personaggio.get_oggetti().filter(id=oggetto.id).exists():
             raise serializers.ValidationError("L'oggetto non appartiene al personaggio target.")
        
        # Esempio di logica di validazione (da adattare)
        # ...
        
        return data

    def save(self):
        richiedente = self.context['richiedente']
        oggetto = self.validated_data['oggetto_id']
        target_personaggio = self.validated_data['target_personaggio_id']
        
        # Usa il metodo corretto del modello per spostare l'oggetto
        oggetto.sposta_in_inventario(richiedente) 
        
        # Aggiungi log
        richiedente.aggiungi_log(f"Oggetto '{oggetto.nome}' rubato da {target_personaggio.nome}.")
        target_personaggio.aggiungi_log(f"Oggetto '{oggetto.nome}' rubato da {richiedente.nome}.")
        
        return oggetto


class AcquisisciSerializer(serializers.Serializer):
    # NOTA: QrCode.id è un CharField, non UUIDField
    qrcode_id = serializers.CharField(max_length=20) 
    
    def validate(self, data):
        richiedente = self.context.get('richiedente')
        if not richiedente:
            raise serializers.ValidationError("Nessun personaggio richiedente fornito.")
            
        try:
            # Convalida come stringa
            qr_code_id_str = str(data.get('qrcode_id'))
            qr_code = QrCode.objects.select_related('vista').get(id=qr_code_id_str)
        except (QrCode.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError("QrCode non valido.")
            
        if not qr_code.vista:
            raise serializers.ValidationError("Questo QrCode non è collegato a nulla.")
            
        vista_obj = qr_code.vista
        
        item = None
        if hasattr(vista_obj, 'oggetto'):
             item = vista_obj.oggetto
        elif hasattr(vista_obj, 'attivata'):
             item = vista_obj.attivata
        else:
             raise serializers.ValidationError("Questo QrCode non punta a un oggetto o attivata acquisibile.")

        self.context['qr_code'] = qr_code
        self.context['item'] = item
        
        return data

    def save(self):
        richiedente = self.context['richiedente']
        qr_code = self.context['qr_code']
        item = self.context['item']
        
        if isinstance(item, Oggetto):
            item.sposta_in_inventario(richiedente) # Usa il metodo corretto
            richiedente.aggiungi_log(f"Acquisito oggetto: {item.nome}.")
        elif isinstance(item, Attivata):
            richiedente.attivate_possedute.add(item)
            richiedente.aggiungi_log(f"Acquisita attivata: {item.nome}.")
            
        qr_code.vista = None
        qr_code.save()
        
        return item