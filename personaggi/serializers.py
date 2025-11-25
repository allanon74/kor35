from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.conf import settings
from django.utils.html import format_html
from django.contrib.auth.models import User
from decimal import Decimal

# Importa i modelli e le funzioni helper
from .models import (
    AbilitaStatistica, ModelloAuraRequisitoDoppia, _get_icon_color_from_bg, QrCode, Abilita, PuntiCaratteristicaMovimento, Tier, 
    Punteggio, Tabella, TipologiaPersonaggio, abilita_tier, 
    abilita_requisito, abilita_sbloccata, abilita_punteggio, abilita_prerequisito, 
    Oggetto, Attivata, Manifesto, A_vista, Mattone,
    AURA, 
    # Nuovi Modelli
    Infusione, Tessitura, InfusioneMattone, TessituraMattone, 
    InfusioneStatisticaBase, TessituraStatisticaBase, ModelloAura,
    
    Inventario, OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    OggettoElemento, AttivataElemento, OggettoInInventario, Statistica, Personaggio, 
    CreditoMovimento, PersonaggioLog, TransazioneSospesa,
    Gruppo, Messaggio,
    ModelloAuraRequisitoCaratt, ModelloAuraRequisitoDoppia,
    ModelloAuraRequisitoMattone,
    PropostaTecnica, PropostaTecnicaMattone, STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE, STATO_PROPOSTA_APPROVATA, STATO_PROPOSTA_RIFIUTATA,
)

# --- Serializer di Base ---

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
    class Meta:
        model = Statistica
        fields = ('nome', 'sigla', 'parametro')
        
class PunteggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punteggio
        fields = ('nome', 'sigla', 'tipo', 'icona_url', 'icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html', 'colore')

class PunteggioSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punteggio
        fields = ('id', 'nome', 'sigla', 'colore', 'icona_url', 'ordine',)
        
class AbilitaPunteggioSmallSerializer(serializers.ModelSerializer):
    punteggio = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = abilita_punteggio
        fields = ('punteggio', 'valore')

class AbilitaStatisticaSmallSerializer(serializers.ModelSerializer):
    statistica = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = AbilitaStatistica
        fields = ('statistica', 'valore', 'tipo_modificatore')

class ModelloAuraSerializer(serializers.ModelSerializer):
    # Mostriamo i mattoni proibiti con le loro icone
    mattoni_proibiti = PunteggioSmallSerializer(many=True, read_only=True)

    class Meta:
        model = ModelloAura
        fields = ('id', 'nome', 'aura', 'mattoni_proibiti')

class PunteggioDetailSerializer(serializers.ModelSerializer):
    icona_html = serializers.SerializerMethodField()
    icona_cerchio_html = serializers.SerializerMethodField()
    icona_cerchio_inverted_html = serializers.SerializerMethodField()
    icona_url = serializers.SerializerMethodField() 
    is_primaria = serializers.SerializerMethodField()
    valore_predefinito = serializers.SerializerMethodField()
    parametro = serializers.SerializerMethodField()
    has_models = serializers.SerializerMethodField()

    class Meta:
        model = Punteggio
        fields = (
            'id', 'nome', 'sigla', 'tipo', 'colore', 
            'icona_url', 'icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html', 
            'is_primaria', 'valore_predefinito', 'parametro', 'ordine', 'has_models',
            )

    def get_base_url(self):
        request = self.context.get('request')
        if request: return f"{request.scheme}://{request.get_host()}"
        return ""
    
    def get_icona_url_assoluto(self, obj):
        if not obj.icona: return None
        base_url = self.get_base_url()
        media_url = settings.MEDIA_URL
        if not media_url: media_url = "/media/"
        if media_url.startswith('/'): media_url = media_url[1:]
        if media_url and not media_url.endswith('/'): media_url = f"{media_url}/"
        icona_path = str(obj.icona)
        if icona_path.startswith('/'): icona_path = icona_path[1:]
        return f"{base_url}/{media_url}{icona_path}"
    
    def get_icona_url(self, obj): 
        return self.get_icona_url_assoluto(obj)
    
    def get_icona_html(self, obj):
        url = self.get_icona_url_assoluto(obj)
        if not url or not obj.colore: return ""
        style = (f"width: 24px; height: 24px; background-color: {obj.colore}; mask-image: url({url}); -webkit-mask-image: url({url}); mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; mask-size: contain; -webkit-mask-size: contain; display: inline-block; vertical-align: middle;")
        return format_html('<div style="{}"></div>', style)
    
    def get_icona_cerchio_html(self, obj): 
        return self._get_icona_cerchio(obj, inverted=False)
    
    def get_icona_cerchio_inverted_html(self, obj): 
        return self._get_icona_cerchio(obj, inverted=True)
    
    def _get_icona_cerchio(self, obj, inverted=False):
        url_icona_locale = self.get_icona_url_assoluto(obj)
        if not url_icona_locale or not obj.colore: return ""
        colore_sfondo = obj.colore
        
        # Calcola colore contrasto
        try:
            colore_icona_contrasto = _get_icon_color_from_bg(colore_sfondo) 
        except:
            colore_icona_contrasto = 'white'

        if inverted:
            colore_icona_contrasto = obj.colore
            try:
                colore_sfondo = _get_icon_color_from_bg(colore_sfondo)
            except:
                colore_sfondo = 'black'
                
        stile_cerchio = (f"display: inline-block; width: 30px; height: 30px; background-color: {colore_sfondo}; border-radius: 50%; vertical-align: middle; text-align: center; line-height: 30px;")
        stile_icona_maschera = (f"display: inline-block; width: 24px; height: 24px; vertical-align: middle; background-color: {colore_icona_contrasto}; mask-image: url({url_icona_locale}); -webkit-mask-image: url({url_icona_locale}); mask-repeat: no-repeat; -webkit-mask-repeat: no-repeat; mask-size: contain; -webkit-mask-size: contain;")
        
        # CORREZIONE QUI: stile_cerchio invece di style_cerchio
        return format_html('<div style="{}"><div style="{}"></div></div>', stile_cerchio, stile_icona_maschera)
    
    def get_is_primaria(self, obj): 
        return True if hasattr(obj, 'statistica') and obj.statistica.is_primaria else False
    
    def get_valore_predefinito(self, obj): 
        return obj.statistica.valore_base_predefinito if hasattr(obj, 'statistica') else 0
    
    def get_parametro(self, obj): 
        return obj.statistica.parametro if hasattr(obj, 'statistica') else None
    
    def get_has_models(self, obj):
        # Ritorna True se esistono ModelliAura collegati a questo punteggio
        return obj.modelli_definiti.exists()
    
# --- Serializer Abilità ---

class AbilSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(many=False)
    tiers = TierSerializer(many=True)
    requisiti = PunteggioSmallSerializer(many=True, required=False)
    punteggio_acquisito = PunteggioSmallSerializer(many=True, required=False)
    class Meta:
        model = Abilita
        fields = '__all__'

class AbilitaSmallSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(many=False)
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

class AbilitaUpdateSerializer(serializers.ModelSerializer):
    requisiti = AbilitaRequisitoSerializer(many=True, required=False)
    punteggio_acquisito = AbilitaPunteggioSerializer(many=True, required=False)
    class Meta:
        model = Abilita
        fields = ['id', 'nome', 'descrizione', 'caratteristica', 'requisiti', 'punteggio_acquisito']
    def update(self, instance, validated_data):
        requisiti_data = validated_data.pop('requisiti', [])
        punteggi_data = validated_data.pop('punteggio_acquisito', [])
        for attr, value in validated_data.items(): setattr(instance, attr, value)
        instance.save()
        if requisiti_data:
            instance.requisiti.clear()
            for item in requisiti_data: abilita_requisito.objects.create(abilita=instance, **item)
        if punteggi_data:
            instance.punteggio_acquisito.clear()
            for item in punteggi_data: abilita_punteggio.objects.create(abilita=instance, **item)
        return instance

# --- Serializer Master List Abilità ---

class AbilitaRequisitoSmallSerializer(serializers.ModelSerializer):
    requisito = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = abilita_requisito
        fields = ('requisito', 'valore')

class AbilitaSmallForPrereqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abilita
        fields = ('id', 'nome')

class AbilitaPrerequisitoSmallSerializer(serializers.ModelSerializer):
    prerequisito = AbilitaSmallForPrereqSerializer(read_only=True)
    class Meta:
        model = abilita_prerequisito
        fields = ('prerequisito',)

class AbilitaMasterListSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(read_only=True)
    requisiti = AbilitaRequisitoSmallSerializer(source='abilita_requisito_set', many=True, read_only=True)
    prerequisiti = AbilitaPrerequisitoSmallSerializer(source='abilita_prerequisiti', many=True, read_only=True)
    punteggi_assegnati = AbilitaPunteggioSmallSerializer(source='abilita_punteggio_set', many=True, read_only=True)
    statistiche_modificate = AbilitaStatisticaSmallSerializer(source='abilitastatistica_set', many=True, read_only=True)
    
    # Gestione Costi
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()
    
    class Meta:
        model = Abilita
        fields = (
            'id', 'nome', 'descrizione', 
            'costo_pc', 'costo_crediti', 
            'caratteristica', 'requisiti', 'prerequisiti', 
            'punteggi_assegnati', 'statistiche_modificate',
            'costo_pieno', 'costo_effettivo',
            )
        
    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti

class AbilitaSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(read_only=True) 
    class Meta:
        model = Abilita
        fields = ('id', 'nome', 'descrizione', 'caratteristica')


# --- Serializer Oggetti/Attivate/Tecniche ---

class OggettoStatisticaSerializer(serializers.ModelSerializer):
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = OggettoStatistica
        fields = ('statistica', 'valore')

class OggettoStatisticaBaseSerializer(serializers.ModelSerializer):
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = OggettoStatisticaBase
        fields = ('statistica', 'valore_base')

# Legacy Attivata
class AttivataStatisticaBaseSerializer(serializers.ModelSerializer):
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = AttivataStatisticaBase
        fields = ('statistica', 'valore_base')

class AttivataElementoSerializer(serializers.ModelSerializer):
    elemento = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = AttivataElemento 
        fields = ('elemento',)

# --- NUOVI SERIALIZER PER INFUSIONE E TESSITURA (CORRETTI) ---

class InfusioneStatisticaBaseSerializer(serializers.ModelSerializer):
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = InfusioneStatisticaBase
        fields = ('statistica', 'valore_base')

class TessituraStatisticaBaseSerializer(serializers.ModelSerializer):
    statistica = StatisticaSerializer(read_only=True)
    class Meta:
        model = TessituraStatisticaBase
        fields = ('statistica', 'valore_base')

class InfusioneMattoneSerializer(serializers.ModelSerializer):
    mattone = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = InfusioneMattone
        fields = ('mattone', 'ordine')

class TessituraMattoneSerializer(serializers.ModelSerializer):
    mattone = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = TessituraMattone
        fields = ('mattone', 'ordine')

class OggettoElementoSerializer(serializers.ModelSerializer):
    elemento = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = OggettoElemento
        fields = ('elemento',)

class OggettoSerializer(serializers.ModelSerializer):
    statistiche = OggettoStatisticaSerializer(source='oggettostatistica_set', many=True, read_only=True)
    statistiche_base = OggettoStatisticaBaseSerializer(source='oggettostatisticabase_set', many=True, read_only=True)
    elementi = OggettoElementoSerializer(source='oggettoelemento_set', many=True, read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    aura = PunteggioSmallSerializer(read_only=True)
    inventario_corrente = serializers.StringRelatedField(read_only=True)
    
    # Gestione Costi
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()
    
    class Meta:
        model = Oggetto
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato', 'testo_formattato_personaggio', 
            'livello', 'aura', 'elementi', 
            'statistiche', 'statistiche_base', 'inventario_corrente', 
            'costo_pieno', 'costo_effettivo',
            )
        
    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti

# Legacy
class AttivataSerializer(serializers.ModelSerializer):
    statistiche_base = AttivataStatisticaBaseSerializer(source='attivatastatisticabase_set', many=True, read_only=True)
    elementi = AttivataElementoSerializer(source='attivataelemento_set', many=True, read_only=True) 
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()
    
    class Meta:
        model = Attivata
        fields = (
            'id', 'nome', 'testo', 
            'TestoFormattato', 'testo_formattato_personaggio', 
            'livello', 'elementi', 'statistiche_base',
            'costo_pieno', 'costo_effettivo',
            )
        
    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti

# New
class InfusioneSerializer(serializers.ModelSerializer):
    statistiche_base = InfusioneStatisticaBaseSerializer(source='infusionestatisticabase_set', many=True, read_only=True)
    mattoni = InfusioneMattoneSerializer(source='infusionemattone_set', many=True, read_only=True)
    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    aura_infusione = PunteggioSmallSerializer(read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    costo_crediti = serializers.IntegerField(read_only=True) # <-- AGGIUNTO
    
    # Gestione Costi
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()

    class Meta:
        model = Infusione
        fields = (
            'id', 'nome', 'testo', 'TestoFormattato', 'testo_formattato_personaggio', 
            'livello', 'aura_richiesta', 'aura_infusione', 'mattoni', 'statistiche_base', 
            'costo_crediti', 'costo_pieno', 'costo_effettivo',
        )
    
    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti

class TessituraSerializer(serializers.ModelSerializer):
    statistiche_base = TessituraStatisticaBaseSerializer(source='tessiturastatisticabase_set', many=True, read_only=True)
    mattoni = TessituraMattoneSerializer(source='tessituramattone_set', many=True, read_only=True)
    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    elemento_principale = PunteggioSmallSerializer(read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    costo_crediti = serializers.IntegerField(read_only=True) # <-- AGGIUNTO
    
    # Gestione Costi
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()

    class Meta:
        model = Tessitura
        fields = (
            'id', 'nome', 'testo', 'formula', 'TestoFormattato', 'testo_formattato_personaggio', 
            'livello', 'aura_richiesta', 'elemento_principale', 'mattoni', 'statistiche_base',
            'costo_crediti', 'costo_pieno', 'costo_effettivo',
        )
    
    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti


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
    punteggi_base = serializers.JSONField(read_only=True) 
    modificatori_calcolati = serializers.JSONField(read_only=True) 
    TestoFormattatoPersonale = serializers.JSONField(read_only=True, required=False)
    tipologia = TipologiaPersonaggioSerializer(read_only=True)
    
    abilita_possedute = AbilitaMasterListSerializer(many=True, read_only=True)
    
    oggetti = serializers.SerializerMethodField()
    attivate_possedute = serializers.SerializerMethodField()
    infusioni_possedute = serializers.SerializerMethodField() # Nuovo
    tessiture_possedute = serializers.SerializerMethodField() # Nuovo
    
    log_eventi = PersonaggioLogSerializer(many=True, read_only=True)
    movimenti_credito = CreditoMovimentoSerializer(many=True, read_only=True)
    transazioni_in_uscita_sospese = TransazioneSospesaSerializer(many=True, read_only=True)
    transazioni_in_entrata_sospese = TransazioneSospesaSerializer(many=True, read_only=True)
    is_staff = serializers.BooleanField(source='proprietario.is_staff', read_only=True)
    modelli_aura = ModelloAuraSerializer(many=True, read_only=True)

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'proprietario', 'data_nascita', 'data_morte',
            'tipologia', 'crediti', 'punti_caratteristica',
            'punteggi_base', 'modificatori_calcolati', 
            'abilita_possedute', 'oggetti', 
            'attivate_possedute', 'infusioni_possedute', 'tessiture_possedute',
            'log_eventi', 'movimenti_credito',
            'transazioni_in_uscita_sospese', 'transazioni_in_entrata_sospese', 
            'TestoFormattatoPersonale',
            'is_staff', 'modelli_aura',
        )
    
    def get_oggetti(self, personaggio):
        oggetti_posseduti = personaggio.get_oggetti().prefetch_related(
            'statistiche_base__statistica', 'oggettostatistica_set__statistica',
            'oggettoelemento_set__elemento', 'aura'
        )
        # Trigger calcolo modificatori prima della serializzazione
        personaggio.modificatori_calcolati 
        
        risultati = []
        # FONDAMENTALE: Creiamo il contesto con il personaggio
        context_con_pg = {**self.context, 'personaggio': personaggio}
        
        for obj in oggetti_posseduti:
            # Usiamo context_con_pg invece di self.context
            dati_oggetto = OggettoSerializer(obj, context=context_con_pg).data 
            dati_oggetto['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(obj)
            risultati.append(dati_oggetto)
        return risultati

    def get_attivate_possedute(self, personaggio):
        attivate = personaggio.attivate_possedute.prefetch_related(
            'statistiche_base__statistica', 'attivataelemento_set__elemento'
        )
        risultati = []
        # FONDAMENTALE: Creiamo il contesto con il personaggio
        context_con_pg = {**self.context, 'personaggio': personaggio}
        
        for att in attivate:
            dati = AttivataSerializer(att, context=context_con_pg).data 
            dati['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(att)
            risultati.append(dati)
        return risultati

    def get_infusioni_possedute(self, personaggio):
        infusioni = personaggio.infusioni_possedute.prefetch_related(
            'statistiche_base__statistica', 'infusionemattone_set__mattone', 
            'aura_richiesta', 'aura_infusione'
        )
        risultati = []
        # FONDAMENTALE: Creiamo il contesto con il personaggio
        context_con_pg = {**self.context, 'personaggio': personaggio}
        
        for inf in infusioni:
            dati = InfusioneSerializer(inf, context=context_con_pg).data
            dati['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(inf)
            risultati.append(dati)
        return risultati

    def get_tessiture_possedute(self, personaggio):
        tessiture = personaggio.tessiture_possedute.prefetch_related(
            'statistiche_base__statistica', 'tessituramattone_set__mattone', 
            'aura_richiesta', 'elemento_principale'
        )
        risultati = []
        # FONDAMENTALE: Creiamo il contesto con il personaggio
        context_con_pg = {**self.context, 'personaggio': personaggio}
        
        for tes in tessiture:
            dati = TessituraSerializer(tes, context=context_con_pg).data
            dati['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(tes)
            risultati.append(dati)
        return risultati

class PersonaggioPublicSerializer(serializers.ModelSerializer):
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)
    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'testo', 'oggetti')

# --- Serializer per Azioni (POST/PUT) ---

class CreditoMovimentoCreateSerializer(serializers.Serializer):
    importo = serializers.DecimalField(max_digits=10, decimal_places=2)
    descrizione = serializers.CharField(max_length=200)
    def create(self, validated_data):
        personaggio = self.context['personaggio']
        movimento = CreditoMovimento.objects.create(personaggio=personaggio, **validated_data)
        return movimento

class TransazioneCreateSerializer(serializers.Serializer):
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    mittente_id = serializers.PrimaryKeyRelatedField(queryset=Inventario.objects.all())
    def validate(self, data):
        oggetto = data.get('oggetto_id')
        mittente = data.get('mittente_id')
        if oggetto.inventario_corrente != mittente:
            raise serializers.ValidationError(f"L'oggetto '{oggetto.nome}' non si trova nell'inventario di '{mittente.nome}'.")
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
        if azione == 'accetta': transazione.accetta()
        elif azione == 'rifiuta': transazione.rifiuta()
        return transazione
    
class PersonaggioListSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    tipologia = serializers.StringRelatedField(read_only=True)
    proprietario_nome = serializers.SerializerMethodField()
    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'proprietario', 'tipologia', 'proprietario_nome', 'data_nascita', 'data_morte')
    def get_proprietario_nome(self, obj):
        user = obj.proprietario
        if not user: return "Nessun Proprietario"
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else user.username
        
class PuntiCaratteristicaMovimentoCreateSerializer(serializers.Serializer):
    importo = serializers.IntegerField()
    descrizione = serializers.CharField(max_length=200)
    def create(self, validated_data):
        personaggio = self.context['personaggio']
        movimento = PuntiCaratteristicaMovimento.objects.create(personaggio=personaggio, **validated_data)
        return movimento
    
class RubaSerializer(serializers.Serializer):
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    target_personaggio_id = serializers.PrimaryKeyRelatedField(queryset=Personaggio.objects.all())
    def validate(self, data):
        richiedente = self.context.get('richiedente')
        if not richiedente: raise serializers.ValidationError("Nessun personaggio richiedente fornito.")
        oggetto = data.get('oggetto_id')
        target_personaggio = data.get('target_personaggio_id')
        if not target_personaggio.get_oggetti().filter(id=oggetto.id).exists():
             raise serializers.ValidationError("L'oggetto non appartiene al personaggio target.")
        return data
    def save(self):
        richiedente = self.context['richiedente']
        oggetto = self.validated_data['oggetto_id']
        target_personaggio = self.validated_data['target_personaggio_id']
        oggetto.sposta_in_inventario(richiedente) 
        richiedente.aggiungi_log(f"Oggetto '{oggetto.nome}' rubato da {target_personaggio.nome}.")
        target_personaggio.aggiungi_log(f"Oggetto '{oggetto.nome}' rubato da {richiedente.nome}.")
        return oggetto

class AcquisisciSerializer(serializers.Serializer):
    qrcode_id = serializers.CharField(max_length=20) 
    def validate(self, data):
        richiedente = self.context.get('richiedente')
        if not richiedente: raise serializers.ValidationError("Nessun personaggio richiedente fornito.")
        try:
            qr_code_id_str = str(data.get('qrcode_id'))
            qr_code = QrCode.objects.select_related('vista').get(id=qr_code_id_str)
        except (QrCode.DoesNotExist, ValueError, TypeError): raise serializers.ValidationError("QrCode non valido.")
        if not qr_code.vista: raise serializers.ValidationError("Questo QrCode non è collegato a nulla.")
        
        vista_obj = qr_code.vista
        item = None
        
        if hasattr(vista_obj, 'oggetto'): item = vista_obj.oggetto
        elif hasattr(vista_obj, 'attivata'): item = vista_obj.attivata
        elif hasattr(vista_obj, 'infusione'): item = vista_obj.infusione # Nuovo
        elif hasattr(vista_obj, 'tessitura'): item = vista_obj.tessitura # Nuovo
        else: raise serializers.ValidationError("Questo QrCode non punta a un oggetto o tecnica acquisibile.")

        self.context['qr_code'] = qr_code
        self.context['item'] = item
        return data

    def save(self):
        richiedente = self.context['richiedente']
        qr_code = self.context['qr_code']
        item = self.context['item']
        
        if isinstance(item, Oggetto):
            item.sposta_in_inventario(richiedente)
            richiedente.aggiungi_log(f"Acquisito oggetto: {item.nome}.")
        elif isinstance(item, Attivata):
            richiedente.attivate_possedute.add(item)
            richiedente.aggiungi_log(f"Acquisita attivata: {item.nome}.")
        elif isinstance(item, Infusione):
            richiedente.infusioni_possedute.add(item)
            richiedente.aggiungi_log(f"Acquisita infusione: {item.nome}.")
        elif isinstance(item, Tessitura):
            richiedente.tessiture_possedute.add(item)
            richiedente.aggiungi_log(f"Acquisita tessitura: {item.nome}.")
            
        qr_code.vista = None
        qr_code.save()
        return item

class GruppoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gruppo
        fields = ('id', 'nome')

class MessaggioSerializer(serializers.ModelSerializer):
    mittente = serializers.StringRelatedField(read_only=True)
    destinatario_personaggio = serializers.StringRelatedField(read_only=True)
    destinatario_gruppo = GruppoSerializer(read_only=True)
    class Meta:
        model = Messaggio
        fields = ('id', 'mittente', 'tipo_messaggio', 'titolo', 'testo', 'data_invio', 'destinatario_personaggio', 'destinatario_gruppo', 'salva_in_cronologia')
        read_only_fields = ('mittente', 'data_invio', 'tipo_messaggio')

class MessaggioBroadcastCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messaggio
        fields = ('titolo', 'testo', 'salva_in_cronologia')
        

# Serializer per i requisiti condizionali
class ModelloAuraRequisitoDoppiaSerializer(serializers.ModelSerializer):
    requisito = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = ModelloAuraRequisitoDoppia
        fields = ('requisito', 'valore')

class ModelloAuraRequisitoCarattSerializer(serializers.ModelSerializer):
    requisito = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = ModelloAuraRequisitoCaratt
        fields = ('requisito', 'valore')

class ModelloAuraRequisitoMattoneSerializer(serializers.ModelSerializer):
    requisito = PunteggioSmallSerializer(read_only=True)
    class Meta:
        model = ModelloAuraRequisitoMattone
        fields = ('requisito', 'valore')

class ModelloAuraSerializer(serializers.ModelSerializer):
    mattoni_proibiti = PunteggioSmallSerializer(many=True, read_only=True)
    mattoni_obbligatori = PunteggioSmallSerializer(many=True, read_only=True) 
    elemento_secondario = PunteggioSmallSerializer(read_only=True)
    elemento_secondario = PunteggioSmallSerializer(read_only=True)
    
    # Campi nidificati per i requisiti
    requisiti_doppia = ModelloAuraRequisitoDoppiaSerializer(source='req_doppia_rel', many=True, read_only=True)
    requisiti_caratt = ModelloAuraRequisitoCarattSerializer(source='req_caratt_rel', many=True, read_only=True)
    requisiti_mattone = ModelloAuraRequisitoMattoneSerializer(source='req_mattone_rel', many=True, read_only=True)

    class Meta:
        model = ModelloAura
        fields = (
            'id', 'nome', 'aura', 
            'mattoni_proibiti', 'mattoni_obbligatori',
            # Doppia Formula
            'usa_doppia_formula', 'elemento_secondario', 
            'usa_condizione_doppia', 'requisiti_doppia',
            # Formula Caratteristica
            'usa_formula_per_caratteristica', 
            'usa_condizione_caratt', 'requisiti_caratt',
            'usa_formula_per_mattone',
            'usa_condizione_mattone', 
            'requisiti_mattone',
        )
        
class PropostaTecnicaMattoneSerializer(serializers.ModelSerializer):
    mattone = PunteggioSmallSerializer(read_only=True)
    mattone_id = serializers.PrimaryKeyRelatedField(
        queryset=Mattone.objects.all(), source='mattone', write_only=True
    )
    
    class Meta:
        model = PropostaTecnicaMattone
        fields = ('id', 'mattone', 'mattone_id', 'ordine')

class PropostaTecnicaSerializer(serializers.ModelSerializer):
    mattoni = PropostaTecnicaMattoneSerializer(source='propostatecnicamattone_set', many=True, read_only=True)
    mattoni_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    aura_details = PunteggioSmallSerializer(source='aura', read_only=True)
    aura = serializers.PrimaryKeyRelatedField(queryset=Punteggio.objects.filter(tipo=AURA))
    
    class Meta:
        model = PropostaTecnica
        fields = (
            'id', 'tipo', 'stato', 'nome', 'descrizione', 
            'aura', 'aura_details', 'mattoni', 'mattoni_ids', 
            'livello', 'costo_invio_pagato', 'note_staff', 'data_creazione'
        )
        read_only_fields = ('stato', 'costo_invio_pagato', 'note_staff', 'data_creazione')

    def create(self, validated_data):
        mattoni_ids = validated_data.pop('mattoni_ids', [])
        personaggio = self.context['personaggio']
        
        proposta = PropostaTecnica.objects.create(personaggio=personaggio, **validated_data)
        
        for idx, m_id in enumerate(mattoni_ids):
            try:
                m = Mattone.objects.get(pk=m_id)
                PropostaTecnicaMattone.objects.create(proposta=proposta, mattone=m, ordine=idx)
            except Mattone.DoesNotExist:
                pass
        return proposta

    def update(self, instance, validated_data):
        if instance.stato != STATO_PROPOSTA_BOZZA:
            raise serializers.ValidationError("Non puoi modificare una proposta già inviata.")
            
        mattoni_ids = validated_data.pop('mattoni_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if mattoni_ids is not None:
            # Ricrea i mattoni
            instance.propostatecnicamattone_set.all().delete()
            for idx, m_id in enumerate(mattoni_ids):
                try:
                    m = Mattone.objects.get(pk=m_id)
                    PropostaTecnicaMattone.objects.create(proposta=instance, mattone=m, ordine=idx)
                except Mattone.DoesNotExist:
                    pass
        return instance