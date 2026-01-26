from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.conf import settings
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.db import models, transaction
from decimal import Decimal

from .models import ConfigurazioneLivelloAura, formatta_testo_generico
# Importa i modelli e le funzioni helper
from .models import (
    AbilitaStatistica, ModelloAuraRequisitoDoppia, _get_icon_color_from_bg, 
    QrCode, Abilita, PuntiCaratteristicaMovimento, Tier, Punteggio, Tabella, 
    TipologiaPersonaggio, abilita_tier, abilita_requisito, abilita_sbloccata, 
    abilita_punteggio, abilita_prerequisito, Attivata, Manifesto, A_vista, Mattone,
    AURA, 
    Infusione, Tessitura, 
    # NUOVI MODELLI INTERMEDI
    InfusioneCaratteristica, TessituraCaratteristica, PropostaTecnicaCaratteristica,
    InfusioneStatisticaBase, TessituraStatisticaBase, ModelloAura, InfusioneStatistica,
    CerimonialeCaratteristica,
    OggettoBase, OggettoBaseStatisticaBase, OggettoBaseModificatore, 
    ForgiaturaInCorso, 
    Inventario, OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    AttivataElemento, OggettoInInventario, Statistica, Personaggio, 
    CreditoMovimento, PersonaggioLog, TransazioneSospesa, PropostaTransazione,
    Gruppo, Messaggio,
    ModelloAuraRequisitoCaratt, ModelloAuraRequisitoMattone,
    PropostaTecnica, 
    STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE, 
    STATO_TRANSAZIONE_IN_ATTESA,
    LetturaMessaggio, Oggetto, ClasseOggetto,
    RichiestaAssemblaggio, OggettoCaratteristica, 
    Cerimoniale, StatoTimerAttivo, MattoneStatistica, abilita_tier as AbilitaTier,
)

# -----------------------------------------------------------------------------
# SERIALIZER DI BASE E UTENTI
# -----------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True, 'required': True}}

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
        fields = ('id', 'nome', 'sigla', 'parametro', 'valore_base_predefinito', )


class PunteggioSerializer(serializers.ModelSerializer):
    produce_mod = serializers.SerializerMethodField()
    produce_materia = serializers.SerializerMethodField()
    produce_innesti = serializers.SerializerMethodField()
    produce_mutazioni = serializers.SerializerMethodField()
    tratti_disponibili = serializers.SerializerMethodField()
    
    class Meta:
        model = Punteggio
        
        fields = (
            'id', # È sempre utile avere l'ID anche nel serializer base
            'nome', 'sigla', 'tipo', 'icona_url', 'icona_html', 
            'icona_cerchio_html', 'icona_cerchio_inverted_html', 
            'colore', 'aure_infusione_consentite', 'ordine',
            # AGGIUNTI QUESTI:
            'produce_mod', 'produce_materia', 'produce_innesti', 'produce_mutazioni',
            'produce_aumenti', 
            'produce_potenziamenti',
            'nome_tipo_aumento',
            'nome_tipo_potenziamento',
            'nome_tipo_tessitura',
            'spegne_a_zero_cariche',
            'potenziamenti_multi_slot',
            'tratti_disponibili',
            'permette_cerimoniali', 
        )
    
    def get_produce_mod(self, obj):
        # Logica: È un mod se produce potenziamenti ed è tecnologico (es. nome='Mod' o spegne a zero cariche)
        return obj.produce_potenziamenti and obj.nome_tipo_potenziamento == 'Mod'

    def get_produce_materia(self, obj):
        return obj.produce_potenziamenti and obj.nome_tipo_potenziamento == 'Materia'

    def get_produce_innesti(self, obj):
        return obj.produce_aumenti and obj.nome_tipo_aumento == 'Innesto'

    def get_produce_mutazioni(self, obj):
        return obj.produce_aumenti and obj.nome_tipo_aumento == 'Mutazione'
    
    def get_tratti_disponibili(self, obj):
        # Usa i dati precaricati dalla View se ci sono (ottimizzazione)
        if hasattr(obj, 'tratti_aura_prefetched'):
            return AbilitaSmallSerializer(obj.tratti_aura_prefetched, many=True).data
        
        # Altrimenti fai la query
        tratti = Abilita.objects.filter(is_tratto_aura=True, aura_riferimento=obj)
        return AbilitaSmallSerializer(tratti, many=True).data


class PunteggioSmallSerializer(serializers.ModelSerializer):
    """ Serializer ridotto per l'uso in liste e relazioni """
    class Meta:
        model = Punteggio
        fields = ('id', 'nome', 'sigla', 'colore', 'icona_url', 'ordine',)


# -----------------------------------------------------------------------------
# SERIALIZER ABILITÀ E DETTAGLI PUNTEGGIO
# -----------------------------------------------------------------------------

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

class ConfigurazioneLivelloAuraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurazioneLivelloAura
        fields = ('id', 'livello', 'nome_step', 'descrizione_fluff', 'is_obbligatorio')

class PunteggioDetailSerializer(serializers.ModelSerializer):
    icona_url = serializers.SerializerMethodField()
    is_primaria = serializers.SerializerMethodField()
    valore_predefinito = serializers.SerializerMethodField()
    valore_base_predefinito = serializers.SerializerMethodField()
    parametro = serializers.SerializerMethodField()
    has_models = serializers.SerializerMethodField()
    aura_id = serializers.SerializerMethodField()
    caratteristica_associata_nome = serializers.SerializerMethodField()
    produce_mod = serializers.SerializerMethodField()
    produce_materia = serializers.SerializerMethodField()
    produce_innesti = serializers.SerializerMethodField()
    produce_mutazioni = serializers.SerializerMethodField()
    configurazione_livelli = ConfigurazioneLivelloAuraSerializer(many=True, read_only=True)
    tratti_disponibili = serializers.SerializerMethodField()

    class Meta:
        model = Punteggio
        fields = (
            'id', 'nome', 'sigla', 'tipo', 'colore',
            'icona_url',
            'is_primaria', 'valore_predefinito', 'valore_base_predefinito', 'parametro', 'ordine', 'has_models',
            'permette_infusioni', 'permette_tessiture', 'permette_cerimoniali',
            'is_mattone',
            'aura_id', 'caratteristica_associata_nome',
            'aure_infusione_consentite',
            # --- NUOVI CAMPI FONDAMENTALI PER IL FRONTEND ---
            'produce_mod', 
            'produce_materia', 
            'produce_innesti', 
            'produce_mutazioni',
            'stat_costo_creazione_infusione', 'stat_costo_creazione_tessitura', 'stat_costo_creazione_cerimoniale',
            'stat_costo_acquisto_infusione', 'stat_costo_acquisto_tessitura', 'stat_costo_acquisto_cerimoniale',
            'stat_costo_invio_proposta_infusione', 'stat_costo_invio_proposta_tessitura', 'stat_costo_invio_proposta_cerimoniale',
            'stat_costo_forgiatura', 'stat_tempo_forgiatura',
            
            # --- CAMPI AGGIORNATI (Nuova struttura) ---
            'produce_aumenti', 
            'produce_potenziamenti',
            'nome_tipo_aumento',
            'nome_tipo_potenziamento',
            'nome_tipo_tessitura',
            'spegne_a_zero_cariche',
            'potenziamenti_multi_slot',
            'configurazione_livelli', 'tratti_disponibili',
        )
        
    def get_produce_mod(self, obj):
        # Logica: È un mod se produce potenziamenti ed è tecnologico (es. nome='Mod' o spegne a zero cariche)
        return obj.produce_potenziamenti and obj.nome_tipo_potenziamento == 'Mod'

    def get_produce_materia(self, obj):
        return obj.produce_potenziamenti and obj.nome_tipo_potenziamento == 'Materia'

    def get_produce_innesti(self, obj):
        return obj.produce_aumenti and obj.nome_tipo_aumento == 'Innesto'

    def get_produce_mutazioni(self, obj):
        return obj.produce_aumenti and obj.nome_tipo_aumento == 'Mutazione'
        
    def get_base_url(self):
        request = self.context.get('request')
        if request:
            return f"{request.scheme}://{request.get_host()}"
        # FALLBACK HARCODED COME RICHIESTO
        return "https://www.kor35.it"

    def get_icona_url_assoluto(self, obj):
        if not obj.icona:
            return None
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

    def get_is_primaria(self, obj):
        return True if hasattr(obj, 'statistica') and obj.statistica.is_primaria else False

    def get_valore_predefinito(self, obj):
        return obj.statistica.valore_predefinito if hasattr(obj, 'statistica') else 0
    
    def get_valore_base_predefinito(self, obj):
        return obj.statistica.valore_base_predefinito if hasattr(obj, 'statistica') else 0

    def get_parametro(self, obj):
        return obj.statistica.parametro if hasattr(obj, 'statistica') else None

    def get_has_models(self, obj):
        return obj.modelli_definiti.exists()

    def get_aura_id(self, obj):
        try:
            if hasattr(obj, 'mattone'):
                return obj.mattone.aura_id
        except Exception:
            pass
        return None

    def get_caratteristica_associata_nome(self, obj):
        try:
            if hasattr(obj, 'mattone') and obj.mattone.caratteristica_associata:
                return obj.mattone.caratteristica_associata.nome
        except Exception:
            pass
        return None

    def get_tratti_disponibili(self, obj):
        # STEP 1: Controllo Cache (Ottimizzazione per Liste)
        # Se la View ha usato prefetch_related con to_attr, usiamo la lista in memoria.
        if hasattr(obj, 'tratti_aura_prefetched'):
            return AbilitaSmallSerializer(obj.tratti_aura_prefetched, many=True).data

        # STEP 2: Query Ottimizzata (Fallback per Dettaglio Singolo)
        # Se non c'è cache, facciamo la query ma con select_related('caratteristica')
        # Questo serve perché AbilitaSmallSerializer deve leggere .caratteristica.nome/icona
        tratti = Abilita.objects.filter(
            is_tratto_aura=True, 
            aura_riferimento=obj
        ).select_related('caratteristica')
        
        return AbilitaSmallSerializer(tratti, many=True).data

# -----------------------------------------------------------------------------
# SERIALIZER PER LE VIEWSET DI ABILITÀ
# -----------------------------------------------------------------------------

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
    statistica_modificata = serializers.SerializerMethodField()
    

    class Meta:
        model = Abilita
        fields = (
            'id', 
            'nome', 
            'descrizione', 
            'livello_riferimento',  # <--- CRUCIALE PER IL FILTRO
            'is_tratto_aura',
            'caratteristica',
            'statistica_modificata',
        )
        
    def get_statistica_modificata(self, obj):
        # Usa il related_name corretto (abilitastatistica_set)
        mods = obj.abilitastatistica_set.all()
        
        if not mods:
            return None
            
        testi = []
        for mod in mods:
            # CORREZIONE: Aggiunto controllo 'and mod.valore != 0'
            if mod.statistica and mod.valore != 0:
                segno = "+" if mod.valore > 0 else ""
                testi.append(f"{mod.statistica.nome} {segno}{mod.valore}")
        
        # Se dopo il filtro la lista è vuota, restituisci None per non mostrare il badge vuoto
        return ", ".join(testi) if testi else None


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


# -----------------------------------------------------------------------------
# SERIALIZER PER LISTE MASTER ABILITÀ
# -----------------------------------------------------------------------------

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
            'costo_pieno', 'costo_effettivo', 'is_tratto_aura',
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


# -----------------------------------------------------------------------------
# SERIALIZER PER TECNICHE, OGGETTI E COMPONENTI
# -----------------------------------------------------------------------------

class ComponenteTecnicaSerializer(serializers.Serializer):
    """
    Serializer generico per InfusioneCaratteristica, TessituraCaratteristica, etc.
    Mostra la caratteristica associata e il valore richiesto.
    """
    caratteristica = PunteggioSmallSerializer(read_only=True)
    valore = serializers.IntegerField()

class InfusioneCaratteristicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfusioneCaratteristica
        fields = ['caratteristica', 'valore']
        validators = [] # Disabilita validazione automatica unicità per update annidato

class InfusioneStatisticaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfusioneStatistica
        # Include tutti i campi del mixin per le condizioni (aure, elementi, etc)
        fields = '__all__'
        validators = [] 
    
    def to_representation(self, instance):
        # Permette al frontend di vedere l'oggetto statistica completo ma accettare l'ID in input
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep

class InfusioneStatisticaBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfusioneStatisticaBase
        fields = ('statistica', 'valore_base')
        validators = []

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep
        
class MattoneStatisticaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MattoneStatistica
        fields =  '__all__'

class TessituraStatisticaBaseSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = TessituraStatisticaBase
        fields = ('statistica', 'valore_base')
        validators = []

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep

class TessituraCaratteristicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TessituraCaratteristica
        fields = ['caratteristica', 'valore']

class CerimonialeCaratteristicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CerimonialeCaratteristica
        fields = ['caratteristica', 'valore']



class OggettoStatisticaSerializer(serializers.ModelSerializer):

    class Meta:
        model = OggettoStatistica
        fields =   '__all__'
        validators = []
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep


class OggettoStatisticaBaseSerializer(serializers.ModelSerializer):

    class Meta:
        model = OggettoStatisticaBase
        fields = ('id', 'statistica', 'valore_base')
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep
    
class OggettoBaseStatisticaBaseSerializer(serializers.ModelSerializer):

    class Meta:
        model = OggettoBaseStatisticaBase
        fields = ('id', 'statistica', 'valore_base')
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep


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


# class OggettoElementoSerializer(serializers.ModelSerializer):
#     elemento = PunteggioSmallSerializer(read_only=True)

#     class Meta:
#         model = OggettoElemento
#         fields = ('elemento',)

class OggettoComponenteSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(read_only=True)
    
    class Meta:
        model = OggettoCaratteristica
        fields = ('caratteristica', 'valore')


class OggettoPotenziamentoSerializer(serializers.ModelSerializer):
    """
    Serializer leggero per mostrare Mod e Materia installate dentro un oggetto padre.
    """
    infusione_nome = serializers.CharField(source='infusione_generatrice.nome', read_only=True)
    tipo_oggetto_display = serializers.CharField(source='get_tipo_oggetto_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True) # 
    descrizione = serializers.CharField(source='testo', read_only=True)
    cariche_massime = serializers.SerializerMethodField()
    durata_totale = serializers.SerializerMethodField()
    costo_ricarica = serializers.SerializerMethodField()
    testo_ricarica = serializers.SerializerMethodField()
    seconds_remaining = serializers.SerializerMethodField()
    TestoFormattato = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    spegne_a_zero_cariche = serializers.SerializerMethodField()
    attacco_base = serializers.CharField(read_only=True)
    attacco_formattato = serializers.SerializerMethodField()
    
    # Usa il serializer completo per le statistiche per avere i dettagli (condizioni, icone, ecc)
    statistiche = OggettoStatisticaSerializer(source='oggettostatistica_set', many=True, read_only=True)
    componenti = OggettoComponenteSerializer(many=True, read_only=True) # Assicurati che i componenti siano visibili
    

    class Meta:
        model = Oggetto
        fields = [
            'id',
            'nome',
            'tipo_oggetto',
            'tipo_oggetto_display',
            'cariche_attuali',
            'infusione_nome', 'descrizione',
            'is_active', 
            'TestoFormattato',
            'cariche_massime', 'durata_totale', 'costo_ricarica', 'testo_ricarica', 'seconds_remaining',
            'data_fine_attivazione',
            'is_active', 'spegne_a_zero_cariche', 
            'statistiche', 'componenti', 
            'attacco_base', 'attacco_formattato',
        ]
    
    def get_spegne_a_zero_cariche(self, obj):
        # Recupera il flag dall'aura (Punteggio) associata all'oggetto
        return obj.aura.spegne_a_zero_cariche if obj.aura else False

    def get_cariche_massime(self, obj):
        if not obj.infusione_generatrice or not obj.infusione_generatrice.statistica_cariche:
            return 0
        
        # Logica di calcolo identica a 'crea_oggetto_da_infusione'
        # Serve il proprietario per i modificatori
        proprietario = obj.inventario_corrente.personaggio_ptr if hasattr(obj.inventario_corrente, 'personaggio_ptr') else None
        
        if not proprietario and obj.inventario_corrente and hasattr(obj.inventario_corrente, 'personaggio_ptr'):
            proprietario = obj.inventario_corrente.personaggio_ptr

        stat_def = obj.infusione_generatrice.statistica_cariche
        
        # 1. Valore Base (dall'infusione o dal default della stat)
        # Cerchiamo se l'infusione ha un override specifico per questa statistica
        stat_base_link = obj.infusione_generatrice.infusionestatisticabase_set.filter(statistica=stat_def).first()
        valore_base = stat_base_link.valore_base if stat_base_link else stat_def.valore_base_predefinito

        # 2. Modificatori Personaggio (se presente)
        if proprietario:
            # Nota: modificatori_calcolati è una property cached del model Personaggio
            mods = proprietario.modificatori_calcolati.get(stat_def.parametro, {'add': 0.0, 'mol': 1.0})
            valore_finale = int(round((valore_base + mods['add']) * mods['mol']))
            return max(0, valore_finale)
        
        return valore_base
    
    def get_attacco_formattato(self, obj):
        if not obj.attacco_base: return None
        personaggio = self.context.get('personaggio')
        # Se l'oggetto è montato su un host, il proprietario è quello dell'host
        if not personaggio and obj.ospitato_su:
             # Tentativo di recuperare il proprietario risalendo la catena
             try:
                 personaggio = obj.ospitato_su.inventario_corrente.personaggio_ptr
             except: pass
             
        if personaggio:
            return formatta_testo_generico(
                None, 
                formula=obj.attacco_base, 
                personaggio=personaggio, 
                solo_formula=True
            ).replace("<strong>Formula:</strong>", "").strip()
        return obj.attacco_base

    def get_durata_totale(self, obj):
        return obj.infusione_generatrice.durata_attivazione if obj.infusione_generatrice else 0

    def get_costo_ricarica(self, obj):
        return obj.infusione_generatrice.costo_ricarica_crediti if obj.infusione_generatrice else 0

    def get_testo_ricarica(self, obj):
        return obj.infusione_generatrice.metodo_ricarica if obj.infusione_generatrice else ""

    def get_seconds_remaining(self, obj):
        if obj.data_fine_attivazione:
            now = timezone.now()
            if obj.data_fine_attivazione > now:
                return int((obj.data_fine_attivazione - now).total_seconds())
        return 0

# -----------------------------------------------------------------------------
# SERIALIZER PER OGGETTO (COMPLETO)
# -----------------------------------------------------------------------------

class OggettoSerializer(serializers.ModelSerializer):
    statistiche = OggettoStatisticaSerializer(source='oggettostatistica_set', many=True, read_only=True)
    statistiche_base = OggettoStatisticaBaseSerializer(source='oggettostatisticabase_set', many=True, read_only=True)
    # elementi = OggettoComponenteSerializer(many=True, read_only=True)
    componenti = OggettoComponenteSerializer(many=True, read_only=True)

    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    aura = PunteggioSmallSerializer(read_only=True)
    inventario_corrente = serializers.StringRelatedField(read_only=True)

    # --- NUOVI CAMPI ---
    tipo_oggetto_display = serializers.CharField(source='get_tipo_oggetto_display', read_only=True)
    classe_oggetto_nome = serializers.CharField(source='classe_oggetto.nome', read_only=True, default="")
    infusione_nome = serializers.CharField(source='infusione_generatrice.nome', read_only=True, default=None)
    potenziamenti_installati = OggettoPotenziamentoSerializer(many=True, read_only=True)
    costo_pieno = serializers.IntegerField(source='costo_acquisto', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()
    seconds_remaining = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    
    cariche_massime = serializers.SerializerMethodField()
    durata_totale = serializers.SerializerMethodField()
    costo_ricarica = serializers.SerializerMethodField()
    testo_ricarica = serializers.SerializerMethodField()
    
    attacco_formattato = serializers.SerializerMethodField()
    spegne_a_zero_cariche = serializers.SerializerMethodField()
    aura_dettagli = serializers.SerializerMethodField()

    class Meta:
        model = Oggetto
        fields = (
            'id',
            'nome',
            'testo',
            'TestoFormattato',
            'testo_formattato_personaggio',
            'livello',
            'aura',
            # 'elementi',
            'componenti',
            'statistiche',
            'statistiche_base',
            'inventario_corrente',

            # Costi
            'costo_pieno',
            'costo_effettivo',
            'in_vendita',

            # Nuovi Campi Logici
            'tipo_oggetto',
            'tipo_oggetto_display',
            'classe_oggetto',
            'classe_oggetto_nome',
            'is_tecnologico',
            'is_equipaggiato',
            'slot_corpo',
            'attacco_base',
            'attacco_formattato',

            # Gestione Cariche e Origine
            'cariche_attuali',
            'infusione_generatrice',
            'infusione_nome',

            # Socketing
            'potenziamenti_installati',
            'data_fine_attivazione', 
            'seconds_remaining',
            'is_active',
            'cariche_massime', 'durata_totale', 'testo_ricarica', 'costo_ricarica', 
            'spegne_a_zero_cariche',
            'is_pesante',
            'aura_dettagli',  
        )
    
    def get_aura_dettagli(self, obj):
        if obj.aura:
            return {"nome": obj.aura.nome, "colore": obj.aura.colore, "icona": obj.aura.icona_url}
        return None
        
    def get_spegne_a_zero_cariche(self, obj):
    # Recupera il flag dall'aura (Punteggio) associata all'oggetto
        return obj.aura.spegne_a_zero_cariche if obj.aura else False

    def get_attacco_formattato(self, obj):
        if not obj.attacco_base:
            return None
        
        personaggio = self.context.get('personaggio')
        # Passa le statistiche_base dell'oggetto per includere i valori base
        statistiche_base = obj.oggettostatisticabase_set.select_related('statistica').all()
        item_mods = obj.oggettostatistica_set.select_related('statistica').all()
        context = {'livello': obj.livello, 'aura': obj.aura, 'item_modifiers': item_mods}
        
        if personaggio:
            # Usiamo la funzione di utility del model per risolvere le graffe {}
            # Passiamo l'attacco come "formula" con statistiche_base e modificatori del personaggio
            return formatta_testo_generico(
                None, 
                formula=obj.attacco_base, 
                statistiche_base=statistiche_base,
                personaggio=personaggio,
                context=context,
                solo_formula=True
            ).replace("<strong>Formula:</strong>", "").strip()
        
        # Senza personaggio, formatta comunque con le statistiche_base
        return formatta_testo_generico(
            None, 
            formula=obj.attacco_base, 
            statistiche_base=statistiche_base,
            context=context,
            solo_formula=True
        ).replace("<strong>Formula:</strong>", "").strip()

    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return getattr(obj, 'costo_acquisto', 0)
    
    def get_seconds_remaining(self, obj):
        if obj.data_fine_attivazione:
            now = timezone.now()
            if obj.data_fine_attivazione > now:
                return int((obj.data_fine_attivazione - now).total_seconds())
        return 0

    def get_cariche_massime(self, obj):
        if not obj.infusione_generatrice or not obj.infusione_generatrice.statistica_cariche:
            return 0
        
        # Logica di calcolo identica a 'crea_oggetto_da_infusione'
        # Serve il proprietario per i modificatori
        proprietario = obj.inventario_corrente.personaggio_ptr if hasattr(obj.inventario_corrente, 'personaggio_ptr') else None
        
        if not proprietario and obj.inventario_corrente and hasattr(obj.inventario_corrente, 'personaggio_ptr'):
            proprietario = obj.inventario_corrente.personaggio_ptr

        stat_def = obj.infusione_generatrice.statistica_cariche
        
        # 1. Valore Base (dall'infusione o dal default della stat)
        # Cerchiamo se l'infusione ha un override specifico per questa statistica
        stat_base_link = obj.infusione_generatrice.infusionestatisticabase_set.filter(statistica=stat_def).first()
        valore_base = stat_base_link.valore_base if stat_base_link else stat_def.valore_base_predefinito

        # 2. Modificatori Personaggio (se presente)
        if proprietario:
            # Nota: modificatori_calcolati è una property cached del model Personaggio
            mods = proprietario.modificatori_calcolati.get(stat_def.parametro, {'add': 0.0, 'mol': 1.0})
            valore_finale = int(round((valore_base + mods['add']) * mods['mol']))
            return max(0, valore_finale)
        
        return valore_base

    def get_durata_totale(self, obj):
        return obj.infusione_generatrice.durata_attivazione if obj.infusione_generatrice else 0

    def get_costo_ricarica(self, obj):
        return obj.infusione_generatrice.costo_ricarica_crediti if obj.infusione_generatrice else 0

    def get_testo_ricarica(self, obj):
        return obj.infusione_generatrice.metodo_ricarica if obj.infusione_generatrice else ""
    
# -----------------------------------------------------------------------------
# SERIALIZER PER LE TECNICHE (INFUSIONE, TESSITURA, CERIMONIALE)
# -----------------------------------------------------------------------------

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


class InfusioneSerializer(serializers.ModelSerializer):
    statistiche_base = InfusioneStatisticaBaseSerializer(source='infusionestatisticabase_set', many=True, read_only=True)
    
    # MODIFICA: 'componenti' invece di 'mattoni'
    componenti = ComponenteTecnicaSerializer(many=True, read_only=True)

    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    aura_infusione = PunteggioSmallSerializer(read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    costo_crediti = serializers.IntegerField(read_only=True)

    # Gestione Costi
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()

    class Meta:
        model = Infusione
        fields = (
            'id', 'nome', 'testo', 'formula_attacco',
            'TestoFormattato', 'testo_formattato_personaggio',
            'livello', 'aura_richiesta', 'aura_infusione',
            'componenti', # NEW
            'statistiche_base',
            'costo_crediti', 'costo_pieno', 'costo_effettivo',
            'tipo_risultato',
        )

    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti


class TessituraSerializer(serializers.ModelSerializer):
    statistiche_base = TessituraStatisticaBaseSerializer(source='tessiturastatisticabase_set', many=True, read_only=True)
    
    # MODIFICA: 'componenti' invece di 'mattoni'
    componenti = ComponenteTecnicaSerializer(many=True, read_only=True)

    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    elemento_principale = PunteggioSmallSerializer(read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    testo_formattato_personaggio = serializers.CharField(read_only=True, default=None)
    livello = serializers.IntegerField(read_only=True)
    costo_crediti = serializers.IntegerField(read_only=True)

    # Gestione Costi
    costo_pieno = serializers.IntegerField(source='costo_crediti', read_only=True)
    costo_effettivo = serializers.SerializerMethodField()

    class Meta:
        model = Tessitura
        fields = (
            'id', 'nome', 'testo', 'formula',
            'TestoFormattato', 'testo_formattato_personaggio',
            'livello', 'aura_richiesta', 'elemento_principale',
            'componenti', # NEW
            'statistiche_base',
            'costo_crediti', 'costo_pieno', 'costo_effettivo',
        )

    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti

class CerimonialeSerializer(serializers.ModelSerializer):
    # Serializer per lista/dettaglio cerimoniali
    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    componenti = ComponenteTecnicaSerializer(many=True, read_only=True)
    TestoFormattato = serializers.CharField(read_only=True)
    costo_crediti = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cerimoniale
        fields = (
            'id', 'nome', 'liv', 'livello', 'aura_richiesta',
            'prerequisiti', 'svolgimento', 'effetto',
            'TestoFormattato', 'costo_crediti', 'componenti'
        )

class TecnicaBaseMasterMixin:
    """Mixin aggiornato per gestire M2M e update annidati"""
    def handle_nested_data(self, instance, components_data, stats_base_data, modifiers_data=None):
        # 1. Componenti
        if components_data is not None:
            instance.componenti.all().delete()
            for comp in components_data:
                instance.componenti.create(**comp)

        # 2. Statistiche Base (Pivot)
        if stats_base_data is not None:
            related_base_name = f"{instance._meta.model_name}statisticabase_set"
            if hasattr(instance, related_base_name):
                getattr(instance, related_base_name).all().delete()
                for stat in stats_base_data:
                    getattr(instance, related_base_name).create(**stat)

        # 3. Modificatori (Solo Infusioni) con gestione Many-to-Many
        if modifiers_data is not None:
            if hasattr(instance, 'infusionestatistica_set'):
                instance.infusionestatistica_set.all().delete()
                for mod in modifiers_data:
                    # Estraiamo i campi M2M prima di creare l'oggetto
                    aure = mod.pop('limit_a_aure', [])
                    elementi = mod.pop('limit_a_elementi', [])
                    new_mod = instance.infusionestatistica_set.create(**mod)
                    # Impostiamo le relazioni M2M
                    if aure: new_mod.limit_a_aure.set(aure)
                    if elementi: new_mod.limit_a_elementi.set(elementi)

# --- SERIALIZZATORI COMPLETI PER MASTER ---

class InfusioneFullEditorSerializer(serializers.ModelSerializer, TecnicaBaseMasterMixin):
    componenti = InfusioneCaratteristicaSerializer(many=True, required=False)
    statistiche_base = InfusioneStatisticaBaseSerializer(many=True, required=False, source='infusionestatisticabase_set')
    modificatori = InfusioneStatisticaSerializer(many=True, required=False, source='infusionestatistica_set')
    livello = serializers.IntegerField(read_only=True)

    class Meta:
        model = Infusione
        fields = '__all__'
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Espande l'aura per permettere al frontend di vedere l'icona
        if instance.aura_richiesta:
            rep['aura_richiesta'] = PunteggioSmallSerializer(instance.aura_richiesta).data
        if instance.aura_infusione:
            rep['aura_infusione'] = PunteggioSmallSerializer(instance.aura_infusione).data
        return rep

    @transaction.atomic
    def create(self, validated_data):
        comp = validated_data.pop('componenti', [])
        s_base = validated_data.pop('infusionestatisticabase_set', [])
        mods = validated_data.pop('infusionestatistica_set', [])
        instance = Infusione.objects.create(**validated_data)
        self.handle_nested_data(instance, comp, s_base, mods)
        return instance
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # Estraiamo i dati annidati per gestirli manualmente via Mixin
        comp = validated_data.pop('componenti', None)
        s_base = validated_data.pop('infusionestatisticabase_set', None)
        mods = validated_data.pop('infusionestatistica_set', None)
        
        # Aggiorniamo i campi base dell'infusione
        instance = super().update(instance, validated_data)
        
        # Aggiorniamo le tabelle correlate (pulizia e ricreazione)
        self.handle_nested_data(instance, comp, s_base, mods)
        return instance

class TessituraFullEditorSerializer(serializers.ModelSerializer, TecnicaBaseMasterMixin):
    componenti = TessituraCaratteristicaSerializer(many=True, required=False)
    statistiche_base = TessituraStatisticaBaseSerializer(many=True, required=False, source='tessiturastatisticabase_set')
    livello = serializers.IntegerField(read_only=True) # Campo calcolato per la lista

    class Meta:
        model = Tessitura
        fields = '__all__'
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Per la lista nel frontend servono gli oggetti completi, non solo gli ID
        rep['aura_richiesta'] = PunteggioSmallSerializer(instance.aura_richiesta).data if instance.aura_richiesta else None
        rep['elemento_principale'] = PunteggioSmallSerializer(instance.elemento_principale).data if instance.elemento_principale else None
        return rep

    @transaction.atomic
    def create(self, validated_data):
        comp = validated_data.pop('componenti', [])
        s_base = validated_data.pop('tessiturastatisticabase_set', [])
        instance = Tessitura.objects.create(**validated_data)
        self.handle_nested_data(instance, comp, s_base)
        return instance
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # Estraiamo i dati annidati per gestirli manualmente via Mixin
        comp = validated_data.pop('componenti', None)
        s_base = validated_data.pop('tessiturastatisticabase_set', None)

        # Aggiorniamo i campi base della tessitura
        instance = super().update(instance, validated_data)
        
        # Aggiorniamo le tabelle correlate (pulizia e ricreazione)
        self.handle_nested_data(instance, comp, s_base)
        return instance

class CerimonialeFullEditorSerializer(serializers.ModelSerializer, TecnicaBaseMasterMixin):
    componenti = CerimonialeCaratteristicaSerializer(many=True, required=False)

    class Meta:
        model = Cerimoniale
        fields = '__all__'
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['aura_richiesta'] = PunteggioSmallSerializer(instance.aura_richiesta).data if instance.aura_richiesta else None
        return rep

    @transaction.atomic
    def create(self, validated_data):
        comp = validated_data.pop('componenti', [])
        instance = Cerimoniale.objects.create(**validated_data)
        self.handle_nested_data(instance, comp, None)
        return instance
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # Estraiamo i dati annidati per gestirli manualmente via Mixin
        comp = validated_data.pop('componenti', None)

        # Aggiorniamo i campi base della cerimoniale
        instance = super().update(instance, validated_data)
        
        # Aggiorniamo le tabelle correlate (pulizia e ricreazione)
        self.handle_nested_data(instance, comp, None)
        return instance

# -----------------------------------------------------------------------------
# SERIALIZER PER PROPOSTA TECNICA (CREAZIONE/MODIFICA)
# -----------------------------------------------------------------------------

class PropostaTecnicaCaratteristicaSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSmallSerializer(read_only=True)
    caratteristica_id = serializers.PrimaryKeyRelatedField(
        queryset=Punteggio.objects.filter(tipo='CA'), source='caratteristica', write_only=True
    )

    class Meta:
        model = PropostaTecnicaCaratteristica
        fields = ('id', 'caratteristica', 'caratteristica_id', 'valore')


class PropostaTecnicaSerializer(serializers.ModelSerializer):
    # Output: lista dettagliata delle caratteristiche
    componenti = PropostaTecnicaCaratteristicaSerializer(many=True, read_only=True)

    # Input: lista di dizionari {id: <id_caratt>, valore: <int>}
    componenti_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    aura_details = PunteggioSmallSerializer(source='aura', read_only=True)
    aura = serializers.PrimaryKeyRelatedField(queryset=Punteggio.objects.filter(tipo='AU'))
    aura_infusione = serializers.PrimaryKeyRelatedField(queryset=Punteggio.objects.filter(tipo='AU'), required=False, allow_null=True)
    personaggio_nome = serializers.CharField(source='personaggio.nome', read_only=True)
    autore_nome = serializers.CharField(source='staff_creatore.username', read_only=True)

    class Meta:
        model = PropostaTecnica
        fields = (
            'id', 'tipo', 'stato', 'nome', 'descrizione',
            'aura', 'aura_details', 'aura_infusione',
            'componenti', 'componenti_data',
            'livello', 'livello_proposto', 'costo_invio_pagato', 'note_staff', 'data_creazione',
            'slot_corpo_permessi', 'tipo_risultato_atteso', 
            'prerequisiti', 'svolgimento', 'effetto', 'personaggio_nome', 'autore_nome',
        )
        read_only_fields = ('stato', 'costo_invio_pagato', 'note_staff', 'data_creazione')
        extra_kwargs = {
            'tipo_risultato_atteso': {'required': False, 'allow_null': True}
        }

    def create(self, validated_data):
        comp_data = validated_data.pop('componenti_data', [])
        personaggio = self.context['personaggio']

        proposta = PropostaTecnica.objects.create(personaggio=personaggio, **validated_data)

        for item in comp_data:
            c_id = item.get('caratteristica_id')
            val = item.get('valore', 1)
            if c_id:
                PropostaTecnicaCaratteristica.objects.create(
                    proposta=proposta,
                    caratteristica_id=c_id,
                    valore=val
                )
        return proposta

    def update(self, instance, validated_data):
        if instance.stato != STATO_PROPOSTA_BOZZA:
            raise serializers.ValidationError("Non puoi modificare una proposta già inviata.")

        comp_data = validated_data.pop('componenti_data', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if comp_data is not None:
            # Ricrea i componenti
            instance.componenti.all().delete()
            for item in comp_data:
                c_id = item.get('caratteristica_id')
                val = item.get('valore', 1)
                if c_id:
                    PropostaTecnicaCaratteristica.objects.create(
                        proposta=instance,
                        caratteristica_id=c_id,
                        valore=val
                    )
        return instance


# -----------------------------------------------------------------------------
# SERIALIZER PER NEGOZIO E CRAFTING
# -----------------------------------------------------------------------------

class OggettoBaseSerializer(serializers.ModelSerializer):
    """
    Serializer per il listino del negozio (oggetti 'template' non ancora istanziati)
    """
   
    classe_oggetto_nome = serializers.CharField(source='classe_oggetto.nome', read_only=True, default="")
    stats_text = serializers.SerializerMethodField()
    attacco_formattato = serializers.SerializerMethodField()
    statistiche_base = OggettoBaseStatisticaBaseSerializer(
        many=True, read_only=True, source='oggettobasestatisticabase_set'
    )

    class Meta:
        model = OggettoBase
        fields = '__all__'  # Tutti i campi del modello OggettoBase)

    def get_attacco_formattato(self, obj):
        """Formatta l'attacco_base usando le statistiche_base dell'OggettoBase"""
        if not obj.attacco_base:
            return None
        
        personaggio = self.context.get('personaggio')
        # Passa le statistiche_base dell'OggettoBase per includere i valori
        statistiche_base = obj.oggettobasestatisticabase_set.select_related('statistica').all()
        
        if personaggio:
            return formatta_testo_generico(
                None, 
                formula=obj.attacco_base, 
                statistiche_base=statistiche_base,
                personaggio=personaggio, 
                solo_formula=True
            ).replace("<strong>Formula:</strong>", "").strip()
        
        # Senza personaggio, formatta comunque con le statistiche_base
        return formatta_testo_generico(
            None, 
            formula=obj.attacco_base, 
            statistiche_base=statistiche_base,
            solo_formula=True
        ).replace("<strong>Formula:</strong>", "").strip()

    def get_stats_text(self, obj):
        parts = []
        if obj.attacco_base:
            parts.append(f"Attacco: {obj.attacco_base}")
        for s in obj.oggettobasestatisticabase_set.select_related('statistica').all():
            parts.append(f"{s.statistica.nome}: {s.valore_base}")
        for m in obj.oggettobasemodificatore_set.select_related('statistica').all():
            sign = "+" if m.valore > 0 else ""
            parts.append(f"{m.statistica.nome} {sign}{m.valore}")
        return ", ".join(parts)


# -----------------------------------------------------------------------------
# SERIALIZER UTILITY (MESSAGGI, RICERCA, TRANSAZIONI)
# -----------------------------------------------------------------------------

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
    personaggio_id = serializers.SerializerMethodField()
    is_personaggio = serializers.SerializerMethodField()
    oggetti_count = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = ('id', 'nome', 'testo', 'oggetti', 'oggetti_count', 'personaggio_id', 'is_personaggio')
    
    def get_personaggio_id(self, obj):
        # Se l'inventario è un Personaggio, restituisci il suo ID
        if hasattr(obj, 'proprietario'):
            return obj.id
        # Altrimenti, cerca se c'è un personaggio con questo inventario
        try:
            from .models import Personaggio
            personaggio = Personaggio.objects.filter(inventario_ptr_id=obj.id).first()
            return personaggio.id if personaggio else None
        except:
            return None
    
    def get_is_personaggio(self, obj):
        return hasattr(obj, 'proprietario')
    
    def get_oggetti_count(self, obj):
        return obj.get_oggetti().count()

class InventarioStaffSerializer(serializers.ModelSerializer):
    """Serializer per gestione inventari nello staff (CRUD completo)"""
    oggetti_count = serializers.SerializerMethodField()
    is_personaggio = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = ('id', 'nome', 'testo', 'oggetti_count', 'is_personaggio')
    
    def get_oggetti_count(self, obj):
        return obj.get_oggetti().count()
    
    def get_is_personaggio(self, obj):
        return hasattr(obj, 'proprietario')


class PersonaggioLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaggioLog
        fields = ('data', 'testo_log')


class CreditoMovimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditoMovimento
        fields = ('importo', 'descrizione', 'data')


class PropostaTransazioneSerializer(serializers.ModelSerializer):
    autore_nome = serializers.CharField(source='autore.nome', read_only=True)
    oggetti_da_dare = serializers.SerializerMethodField()
    oggetti_da_ricevere = serializers.SerializerMethodField()
    
    class Meta:
        model = PropostaTransazione
        fields = (
            'id', 'autore', 'autore_nome', 'crediti_da_dare', 'crediti_da_ricevere',
            'oggetti_da_dare', 'oggetti_da_ricevere', 'messaggio', 
            'data_creazione', 'is_attiva'
        )
        read_only_fields = ('id', 'data_creazione', 'is_attiva', 'oggetti_da_dare', 'oggetti_da_ricevere')
    
    def get_oggetti_da_dare(self, obj):
        return [oggetto.id for oggetto in obj.oggetti_da_dare.all()]
    
    def get_oggetti_da_ricevere(self, obj):
        return [oggetto.id for oggetto in obj.oggetti_da_ricevere.all()]

class TransazioneSospesaSerializer(serializers.ModelSerializer):
    oggetto = serializers.StringRelatedField(read_only=True)
    mittente = serializers.StringRelatedField(read_only=True)
    richiedente = serializers.StringRelatedField(read_only=True)
    iniziatore_nome = serializers.CharField(source='iniziatore.nome', read_only=True)
    destinatario_nome = serializers.CharField(source='destinatario.nome', read_only=True)
    ultima_proposta_iniziatore = PropostaTransazioneSerializer(read_only=True)
    ultima_proposta_destinatario = PropostaTransazioneSerializer(read_only=True)
    proposte = PropostaTransazioneSerializer(many=True, read_only=True)

    class Meta:
        model = TransazioneSospesa
        fields = (
            'id', 'oggetto', 'mittente', 'richiedente', 
            'iniziatore', 'iniziatore_nome', 'destinatario', 'destinatario_nome',
            'data_richiesta', 'data_creazione', 'data_ultima_modifica', 'data_chiusura',
            'stato', 'ultima_proposta_iniziatore', 'ultima_proposta_destinatario', 'proposte'
        )


class TipologiaPersonaggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipologiaPersonaggio
        fields = ('id', 'nome', 'crediti_iniziali', 'caratteristiche_iniziali', 'giocante')


class PersonaggioDetailSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    crediti = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    punti_caratteristica = serializers.IntegerField(read_only=True)
    punteggi_base = serializers.JSONField(read_only=True)
    statistiche_base_dict = serializers.JSONField(read_only=True)
    modificatori_calcolati = serializers.JSONField(read_only=True)
    TestoFormattatoPersonale = serializers.JSONField(read_only=True, required=False)
    tipologia = TipologiaPersonaggioSerializer(read_only=True)

    abilita_possedute = AbilitaMasterListSerializer(many=True, read_only=True)

    oggetti = serializers.SerializerMethodField()
    attivate_possedute = serializers.SerializerMethodField()
    infusioni_possedute = serializers.SerializerMethodField()
    tessiture_possedute = serializers.SerializerMethodField()

    movimenti_credito = CreditoMovimentoSerializer(many=True, read_only=True)
    is_staff = serializers.BooleanField(source='proprietario.is_staff', read_only=True)
    modelli_aura = ModelloAuraSerializer(many=True, read_only=True)
    
    lavori_pendenti_count = serializers.SerializerMethodField()
    messaggi_non_letti_count = serializers.SerializerMethodField()
    statistiche_primarie = serializers.SerializerMethodField()
    
    impostazioni_ui = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'proprietario', 'data_nascita', 'data_morte', 'costume',
            'tipologia', 'crediti', 'punti_caratteristica',
            'punteggi_base', 'statistiche_base_dict', 'modificatori_calcolati',
            'abilita_possedute', 'oggetti',
            'attivate_possedute', 'infusioni_possedute', 'tessiture_possedute',
            'movimenti_credito',
            'TestoFormattatoPersonale',
            'is_staff', 'modelli_aura',
            'lavori_pendenti_count', 'messaggi_non_letti_count', 'statistiche_primarie',
            'statistiche_temporanee',
            'impostazioni_ui',
        )

    def get_oggetti(self, personaggio):
        if hasattr(personaggio.inventario_ptr, 'tracciamento_oggetti_correnti'):
            oggetti_posseduti = [x.oggetto for x in personaggio.inventario_ptr.tracciamento_oggetti_correnti]
        else:
            oggetti_posseduti = personaggio.get_oggetti().prefetch_related(
                'statistiche_base__statistica', 'oggettostatistica_set__statistica',
                'componenti__caratteristica', 'aura'
            )
        personaggio.modificatori_calcolati
        risultati = []
        context_con_pg = {**self.context, 'personaggio': personaggio}
        for obj in oggetti_posseduti:
            dati_oggetto = OggettoSerializer(obj, context=context_con_pg).data
            dati_oggetto['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(obj)
            risultati.append(dati_oggetto)
        return risultati

    def get_attivate_possedute(self, personaggio):
        attivate = personaggio.attivate_possedute.all()
        risultati = []
        context_con_pg = {**self.context, 'personaggio': personaggio}
        for att in attivate:
            dati = AttivataSerializer(att, context=context_con_pg).data
            dati['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(att)
            risultati.append(dati)
        return risultati

    def get_infusioni_possedute(self, personaggio):
        infusioni = personaggio.infusioni_possedute.all()
        risultati = []
        context_con_pg = {**self.context, 'personaggio': personaggio}
        for inf in infusioni:
            dati = InfusioneSerializer(inf, context=context_con_pg).data
            dati['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(inf)
            risultati.append(dati)
        return risultati

    def get_tessiture_possedute(self, personaggio):
        tessiture = personaggio.tessiture_possedute.all()
        risultati = []
        context_con_pg = {**self.context, 'personaggio': personaggio}
        for tes in tessiture:
            dati = TessituraSerializer(tes, context=context_con_pg).data
            dati['testo_formattato_personaggio'] = personaggio.get_testo_formattato_per_item(tes)
            risultati.append(dati)
        return risultati
    
    def get_lavori_pendenti_count(self, obj):
        return obj.richieste_assemblaggio_ricevute.filter(stato='PEND').count()

    def get_messaggi_non_letti_count(self, obj):
        return obj.messaggi_ricevuti_individuali.exclude(stati_lettura__letto=True).count() # Semplificato

    def get_statistiche_primarie(self, obj):
        # Restituisce una lista strutturata delle stat primarie per il GameTab
        stats = []
        for stat in Statistica.objects.filter(is_primaria=True):
            val_max = obj.get_valore_statistica(stat.sigla)
            # Recupera il valore corrente da statistiche_temporanee o usa il max
            val_current = obj.statistiche_temporanee.get(stat.sigla, val_max)
            stats.append({
                'sigla': stat.sigla,
                'nome': stat.nome,
                'valore_max': val_max,
                'valore_corrente': val_current
            })
        return stats


class PersonaggioPublicSerializer(serializers.ModelSerializer):
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)

    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'testo', 'oggetti', 'costume', )
        
class PersonaggioSerializer(serializers.ModelSerializer):
    """ Serializer base mancante richiesto dalla gestione plot """
    giocante = serializers.BooleanField(source='tipologia.giocante', read_only=True)
    tipologia_nome = serializers.CharField(source='tipologia.nome', read_only=True)
    tipologia = serializers.PrimaryKeyRelatedField(
        queryset=TipologiaPersonaggio.objects.all(),
        required=False
    )
    proprietario = serializers.StringRelatedField(read_only=True)
    proprietario_id = serializers.PrimaryKeyRelatedField(source='proprietario', read_only=True)
    is_staff = serializers.SerializerMethodField()
    
    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'costume', 
            'tipologia', 'tipologia_nome', 
            'proprietario', 'data_nascita', 'data_morte',
            'crediti', 'punti_caratteristica',
            'giocante', 'proprietario_id', 'is_staff',
        )
        read_only_fields = ('crediti', 'punti_caratteristica') 
    
    def get_is_staff(self, obj):
        # Ritorna True se l'utente proprietario è staff o superuser
        if not obj.proprietario:
            return False
        return obj.proprietario.is_staff or obj.proprietario.is_superuser
        
# Aggiungi in personaggi/serializers.py

class PersonaggioManageSerializer(serializers.ModelSerializer):
    """
    Serializer leggero per la creazione e modifica anagrafica dei personaggi.
    Gestisce correttamente la scrittura della Tipologia tramite ID.
    """
    tipologia = serializers.PrimaryKeyRelatedField(
        queryset=TipologiaPersonaggio.objects.all(),
        required=False
    )
    # Per la visualizzazione (se serve)
    tipologia_nome = serializers.CharField(source='tipologia.nome', read_only=True)
    proprietario = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'costume', 
            'tipologia', 'tipologia_nome', 
            'proprietario', 'data_nascita', 'data_morte',
            'crediti', 'punti_caratteristica' # Read-only di default qui sotto
        )
        read_only_fields = ('crediti', 'punti_caratteristica', 'proprietario')

class CreditoMovimentoCreateSerializer(serializers.Serializer):
    importo = serializers.DecimalField(max_digits=10, decimal_places=2)
    descrizione = serializers.CharField(max_length=200)

    def create(self, validated_data):
        return CreditoMovimento.objects.create(personaggio=self.context['personaggio'], **validated_data)


class TransazioneCreateSerializer(serializers.Serializer):
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    mittente_id = serializers.PrimaryKeyRelatedField(queryset=Inventario.objects.all())

    def validate(self, data):
        if data.get('oggetto_id').inventario_corrente != data.get('mittente_id'):
            raise serializers.ValidationError(f"L'oggetto non si trova nell'inventario.")
        return data

    def create(self, validated_data):
        return TransazioneSospesa.objects.create(
            oggetto=validated_data.get('oggetto_id'),
            mittente=validated_data.get('mittente_id'),
            richiedente=self.context['richiedente']
        )


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

class TransazioneAvanzataCreateSerializer(serializers.Serializer):
    """Serializer per creare una nuova transazione avanzata con proposta iniziale"""
    destinatario_id = serializers.PrimaryKeyRelatedField(queryset=Personaggio.objects.all())
    proposta = serializers.DictField()
    
    def validate_proposta(self, value):
        required_fields = ['crediti_da_dare', 'crediti_da_ricevere']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Campo '{field}' mancante nella proposta")
        return value
    
    def create(self, validated_data):
        iniziatore = self.context['iniziatore']
        destinatario = validated_data['destinatario_id']
        proposta_data = validated_data['proposta']
        
        from django.db import transaction as db_transaction
        
        with db_transaction.atomic():
            # Crea transazione
            transazione = TransazioneSospesa.objects.create(
                iniziatore=iniziatore,
                destinatario=destinatario,
                stato=STATO_TRANSAZIONE_IN_ATTESA
            )
            
            # Crea proposta iniziale
            proposta = PropostaTransazione.objects.create(
                transazione=transazione,
                autore=iniziatore,
                crediti_da_dare=proposta_data.get('crediti_da_dare', 0),
                crediti_da_ricevere=proposta_data.get('crediti_da_ricevere', 0),
                messaggio=proposta_data.get('messaggio', ''),
                is_attiva=True
            )
            
            # Aggiungi oggetti se presenti
            if proposta_data.get('oggetti_da_dare'):
                proposta.oggetti_da_dare.set(proposta_data['oggetti_da_dare'])
            if proposta_data.get('oggetti_da_ricevere'):
                proposta.oggetti_da_ricevere.set(proposta_data['oggetti_da_ricevere'])
            
            transazione.ultima_proposta_iniziatore = proposta
            transazione.save()
            
            return transazione

class PropostaTransazioneCreateSerializer(serializers.Serializer):
    """Serializer per creare una nuova proposta (controproposta o rilancio)"""
    crediti_da_dare = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    crediti_da_ricevere = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    oggetti_da_dare = serializers.PrimaryKeyRelatedField(many=True, queryset=Oggetto.objects.all(), required=False)
    oggetti_da_ricevere = serializers.PrimaryKeyRelatedField(many=True, queryset=Oggetto.objects.all(), required=False)
    messaggio = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        transazione = self.context['transazione']
        autore = self.context['autore']
        
        oggetti_da_dare = validated_data.pop('oggetti_da_dare', [])
        oggetti_da_ricevere = validated_data.pop('oggetti_da_ricevere', [])
        
        proposta = PropostaTransazione.objects.create(
            transazione=transazione,
            autore=autore,
            is_attiva=True,
            **validated_data
        )
        
        if oggetti_da_dare:
            proposta.oggetti_da_dare.set(oggetti_da_dare)
        if oggetti_da_ricevere:
            proposta.oggetti_da_ricevere.set(oggetti_da_ricevere)
        
        return proposta


class PersonaggioListSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    tipologia = serializers.StringRelatedField(read_only=True)
    proprietario_nome = serializers.SerializerMethodField()

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'proprietario', 'tipologia', 
            'proprietario_nome', 'data_nascita', 'data_morte',
            'testo', 'costume', 'crediti', 'punti_caratteristica',
            )
        read_only_fields = ('crediti', 'punti_caratteristica') 

    def get_proprietario_nome(self, obj):
        user = obj.proprietario
        if not user:
            return "Nessun Proprietario"
        return f"{user.first_name} {user.last_name}".strip() or user.username


class PuntiCaratteristicaMovimentoCreateSerializer(serializers.Serializer):
    importo = serializers.IntegerField()
    descrizione = serializers.CharField(max_length=200)

    def create(self, validated_data):
        return PuntiCaratteristicaMovimento.objects.create(personaggio=self.context['personaggio'], **validated_data)


class RubaSerializer(serializers.Serializer):
    oggetto_id = serializers.PrimaryKeyRelatedField(queryset=Oggetto.objects.all())
    target_personaggio_id = serializers.PrimaryKeyRelatedField(queryset=Personaggio.objects.all())

    def validate(self, data):
        if not data.get('target_personaggio_id').get_oggetti().filter(id=data.get('oggetto_id').id).exists():
            raise serializers.ValidationError("L'oggetto non appartiene al personaggio target.")
        return data

    def save(self):
        obj = self.validated_data['oggetto_id']
        obj.sposta_in_inventario(self.context['richiedente'])
        self.context['richiedente'].aggiungi_log(f"Rubato {obj.nome}")
        self.validated_data['target_personaggio_id'].aggiungi_log(f"Rubato {obj.nome}")
        return obj


class AcquisisciSerializer(serializers.Serializer):
    qrcode_id = serializers.CharField(max_length=20)

    def validate(self, data):
        try:
            qr = QrCode.objects.select_related('vista').get(id=str(data.get('qrcode_id')))
            if not qr.vista:
                raise serializers.ValidationError("QrCode vuoto.")
            self.context['qr_code'] = qr
            self.context['item'] = (
                qr.vista.oggetto if hasattr(qr.vista, 'oggetto') else (
                    qr.vista.attivata if hasattr(qr.vista, 'attivata') else (
                        qr.vista.infusione if hasattr(qr.vista, 'infusione') else qr.vista.tessitura
                    )
                )
            )
        except Exception:
            raise serializers.ValidationError("QrCode non valido.")
        return data

    def save(self):
        item = self.context['item']
        pg = self.context['richiedente']
        if isinstance(item, Oggetto):
            item.sposta_in_inventario(pg)
        elif isinstance(item, Attivata):
            pg.attivate_possedute.add(item)
        elif isinstance(item, Infusione):
            pg.infusioni_possedute.add(item)
        elif isinstance(item, Tessitura):
            pg.tessiture_possedute.add(item)
        self.context['qr_code'].vista = None
        self.context['qr_code'].save()
        return item


class GruppoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gruppo
        fields = ('id', 'nome')


class MessaggioSerializer(serializers.ModelSerializer):
    mittente = serializers.StringRelatedField(read_only=True)
    mittente_nome = serializers.SerializerMethodField()
    mittente_personaggio_id = serializers.IntegerField(source='mittente_personaggio.id', read_only=True, allow_null=True)
    mittente_personaggio_nome = serializers.CharField(source='mittente_personaggio.nome', read_only=True, allow_null=True)
    destinatario_personaggio = serializers.StringRelatedField(read_only=True)
    destinatario_personaggio_id = serializers.IntegerField(source='destinatario_personaggio.id', read_only=True, allow_null=True)
    destinatario_gruppo = GruppoSerializer(read_only=True)
    letto = serializers.SerializerMethodField()
    mittente_is_staff = serializers.SerializerMethodField()
    data_creazione = serializers.DateTimeField(source='data_invio', read_only=True)
    in_risposta_a_id = serializers.IntegerField(source='in_risposta_a.id', read_only=True, allow_null=True)
    risposte_count = serializers.SerializerMethodField()

    class Meta:
        model = Messaggio
        fields = (
            'id', 'mittente', 'mittente_nome', 'mittente_personaggio_id', 'mittente_personaggio_nome',
            'mittente_is_staff', 'tipo_messaggio', 'titolo', 'testo', 
            'data_invio', 'data_creazione', 'destinatario_personaggio', 'destinatario_personaggio_id',
            'destinatario_gruppo', 'salva_in_cronologia', 'letto', 'is_staff_message',
            'in_risposta_a_id', 'risposte_count'
        )
        read_only_fields = ('mittente', 'data_invio', 'tipo_messaggio')
    
    def get_letto(self, obj):
        # Per messaggi staff, usa il campo letto_staff
        if obj.is_staff_message:
            return obj.letto_staff
        # Per altri messaggi, usa is_letto_db se disponibile
        return getattr(obj, 'is_letto_db', False)
    
    def get_mittente_nome(self, obj):
        if obj.mittente:
            return obj.mittente.username
        return None
    
    def get_mittente_is_staff(self, obj):
        if obj.mittente:
            return obj.mittente.is_staff
        return False
    
    def get_risposte_count(self, obj):
        return obj.risposte.count()


class ConversazioneSerializer(serializers.Serializer):
    """Serializer per raggruppare messaggi in conversazioni thread-style"""
    conversazione_id = serializers.IntegerField()
    partecipanti = serializers.ListField(child=serializers.DictField())
    ultimo_messaggio = serializers.DateTimeField()
    messaggi = MessaggioSerializer(many=True)
    non_letti = serializers.IntegerField()


class MessaggioBroadcastCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messaggio
        fields = ('titolo', 'testo', 'salva_in_cronologia')


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


class PersonaggioAutocompleteSerializer(serializers.ModelSerializer):
    slots_occupati = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField() # <--- NUOVO CAMPO

    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'slots_occupati', 'is_mine') # <--- AGGIUNTO QUI

    def get_slots_occupati(self, obj):
        # Recupera slot occupati (già discusso precedentemente)
        return list(Oggetto.objects.filter(
            tracciamento_inventario__inventario=obj,
            tracciamento_inventario__data_fine__isnull=True,
            slot_corpo__isnull=False
        ).exclude(slot_corpo='').values_list('slot_corpo', flat=True))

    def get_is_mine(self, obj):
        # Verifica se il personaggio appartiene all'utente che fa la richiesta
        request = self.context.get('request')
        if request and request.user:
            return obj.proprietario == request.user
        return False


class MessaggioCreateSerializer(serializers.ModelSerializer):
    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Personaggio.objects.all(), source='destinatario_personaggio', write_only=True, required=False, allow_null=True
    )
    is_staff_message = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Messaggio
        fields = ('destinatario_id', 'titolo', 'testo', 'is_staff_message')

    def create(self, validated_data):
        validated_data['mittente'] = self.context['request'].user
        
        # Se è un messaggio staff, imposta tipo_messaggio a STAFF
        if validated_data.get('is_staff_message'):
            validated_data['tipo_messaggio'] = Messaggio.TIPO_STAFF
        else:
            validated_data['tipo_messaggio'] = Messaggio.TIPO_INDIVIDUALE
            
        return super().create(validated_data)
    
class RichiestaAssemblaggioSerializer(serializers.ModelSerializer):
    committente_nome = serializers.CharField(source='committente.nome', read_only=True)
    artigiano_nome = serializers.CharField(source='artigiano.nome', read_only=True)
    
    host_nome = serializers.CharField(source='oggetto_host.nome', read_only=True)
    componente_nome = serializers.CharField(source='componente.nome', read_only=True)
    infusione_nome = serializers.CharField(source='infusione.nome', read_only=True) # Nuovo
    
    tipo_display = serializers.CharField(source='get_tipo_operazione_display', read_only=True)
    
    slot_destinazione = serializers.CharField(read_only=True)
    forgiatura_nome = serializers.CharField(source='forgiatura_target.infusione.nome', read_only=True)

    class Meta:
        model = RichiestaAssemblaggio
        fields = [
            'id', 
            'committente', 'committente_nome', 
            'artigiano', 'artigiano_nome', 
            'oggetto_host', 'host_nome',
            'componente', 'componente_nome',
            'infusione', 'infusione_nome',
            'tipo_operazione', 'tipo_display',
            'offerta_crediti', 'stato', 'data_creazione',
            'forgiatura_target', 'forgiatura_nome', 'slot_destinazione'
        ]
        
# personaggi/serializers.py

class ClasseOggettoSerializer(serializers.ModelSerializer):
    # Restituisce la lista di ID delle caratteristiche permesse per le MOD
    mod_allowed_ids = serializers.SerializerMethodField()
    
    # Restituisce la lista di ID delle caratteristiche permesse per le MATERIE
    materia_allowed_ids = serializers.SerializerMethodField()

    class Meta:
        model = ClasseOggetto
        fields = ['id', 'nome', 'max_mod_totali', 'limitazioni_mod', 'mattoni_materia_permessi', 'mod_allowed_ids', 'materia_allowed_ids']

    def get_mod_allowed_ids(self, obj):
        # Recupera gli ID delle caratteristiche dalla relazione ManyToMany 'limitazioni_mod'
        return list(obj.limitazioni_mod.values_list('id', flat=True))

    def get_materia_allowed_ids(self, obj):
        # Recupera gli ID delle caratteristiche dalla relazione 'mattoni_materia_permessi'
        return list(obj.mattoni_materia_permessi.values_list('id', flat=True))
    
    
# personaggi/serializers.py (Aggiungi in fondo)

class StatoTimerSerializer(serializers.ModelSerializer):
    """Serializza lo stato attivo includendo i dati della tipologia"""
    nome = serializers.CharField(source='tipologia.nome', read_only=True)
    alert_suono = serializers.BooleanField(source='tipologia.alert_suono', read_only=True)
    notifica_push = serializers.BooleanField(source='tipologia.notifica_push', read_only=True)
    messaggio_in_app = serializers.BooleanField(source='tipologia.messaggio_in_app', read_only=True)

    class Meta:
        model = StatoTimerAttivo
        fields = ['id', 'nome', 'data_fine', 'alert_suono', 'notifica_push', 'messaggio_in_app']


class OggettoBaseStatisticaBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OggettoBaseStatisticaBase
        fields = ['statistica', 'valore_base']
        validators = []
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep

class OggettoBaseModificatoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = OggettoBaseModificatore
        fields = ['statistica', 'valore', 'tipo_modificatore']
        validators = []
        
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['statistica'] = StatisticaSerializer(instance.statistica).data
        return rep

        
class MasterOggettoMixin:
    """Mixin per gestire i dati nidificati di Oggetti e Oggetti Base"""
    
    def handle_nested_data(self, instance, components=None, stats_base=None, stats_mod=None):
        # 1. Gestione Componenti (Caratteristiche) - solo per Oggetto istanza
        if components is not None:
            instance.componenti.all().delete()
            for comp in components:
                instance.componenti.create(**comp)

        # 2. Gestione Statistiche Base
        if stats_base is not None:
            # Determina il set corretto in base al modello (Oggetto o OggettoBase)
            related_name = 'oggettostatisticabase_set' if hasattr(instance, 'oggettostatisticabase_set') else 'oggettobasestatisticabase_set'
            getattr(instance, related_name).all().delete()
            for s in stats_base:
                getattr(instance, related_name).create(**s)

        # 3. Gestione Modificatori/Statistiche
        if stats_mod is not None:
            related_name = 'oggettostatistica_set' if hasattr(instance, 'oggettostatistica_set') else 'oggettobasemodificatore_set'
            getattr(instance, related_name).all().delete()
            for m in stats_mod:
                # Estraiamo i campi M2M se presenti (solo su Oggetto istanza)
                aure = m.pop('limit_a_aure', [])
                elementi = m.pop('limit_a_elementi', [])
                
                new_mod = getattr(instance, related_name).create(**m)
                
                # Applica relazioni Many-to-Many se l'oggetto le supporta
                if hasattr(new_mod, 'limit_a_aure') and aure:
                    new_mod.limit_a_aure.set(aure)
                if hasattr(new_mod, 'limit_a_elementi') and elementi:
                    new_mod.limit_a_elementi.set(elementi)

# SERIALIZZATORE COMPLETO PER EDIT OGGETTO (ISTANZA)

class OggettoComponenteEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = OggettoCaratteristica
        fields = ['caratteristica', 'valore']

class OggettoFullEditorSerializer(serializers.ModelSerializer, MasterOggettoMixin):
    componenti = OggettoComponenteEditorSerializer(many=True, required=False)
    statistiche_base = OggettoStatisticaBaseSerializer(many=True, required=False, source='oggettostatisticabase_set')
    statistiche = OggettoStatisticaSerializer(many=True, required=False, source='oggettostatistica_set')

    class Meta:
        model = Oggetto
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        comp = validated_data.pop('componenti', [])
        s_base = validated_data.pop('oggettostatisticabase_set', [])
        s_mod = validated_data.pop('oggettostatistica_set', [])
        
        instance = Oggetto.objects.create(**validated_data)
        self.handle_nested_data(instance, components=comp, stats_base=s_base, stats_mod=s_mod)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        comp = validated_data.pop('componenti', None)
        s_base = validated_data.pop('oggettostatisticabase_set', None)
        s_mod = validated_data.pop('oggettostatistica_set', None)
        
        instance = super().update(instance, validated_data)
        self.handle_nested_data(instance, components=comp, stats_base=s_base, stats_mod=s_mod)
        return instance

# SERIALIZZATORE COMPLETO PER EDIT OGGETTO BASE (TEMPLATE)
class OggettoBaseFullEditorSerializer(serializers.ModelSerializer, MasterOggettoMixin):
    statistiche_base = OggettoBaseStatisticaBaseSerializer(many=True, required=False, source='oggettobasestatisticabase_set')
    statistiche_modificatori = OggettoBaseModificatoreSerializer(many=True, required=False, source='oggettobasemodificatore_set')

    class Meta:
        model = OggettoBase
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        s_base = validated_data.pop('oggettobasestatisticabase_set', [])
        s_mod = validated_data.pop('oggettobasemodificatore_set', [])
        
        instance = OggettoBase.objects.create(**validated_data)
        self.handle_nested_data(instance, stats_base=s_base, stats_mod=s_mod)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        s_base = validated_data.pop('oggettobasestatisticabase_set', None)
        s_mod = validated_data.pop('oggettobasemodificatore_set', None)
        
        instance = super().update(instance, validated_data)
        self.handle_nested_data(instance, stats_base=s_base, stats_mod=s_mod)
        return instance
    
# --- SERIALIZERS PER EDITOR STAFF ABILITÀ ---

class AbilitaTierEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_tier
        fields = ['tabella', 'ordine'] 
        read_only_fields = ['abilita'] # Fondamentale per la creazione

class AbilitaRequisitoEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_requisito
        fields = ['requisito', 'valore']
        read_only_fields = ['abilita'] # Fondamentale

class AbilitaPunteggioEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_punteggio
        fields = ['punteggio', 'valore']
        read_only_fields = ['abilita'] # Fondamentale

class AbilitaPrerequisitoEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_prerequisito
        fields = ['prerequisito']
        read_only_fields = ['abilita'] # Fondamentale

class AbilitaStatisticaEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbilitaStatistica
        fields = '__all__'
        read_only_fields = ['abilita'] # FIX ERRORE "Campo obbligatorio"
        validators = [] 

class AbilitaFullEditorSerializer(serializers.ModelSerializer):
    """
    Serializer completo per CRUD Abilità lato Staff.
    Gestisce salvataggio atomico di tutte le inlines.
    """
    tiers = AbilitaTierEditorSerializer(source='abilita_tier_set', many=True, required=False)
    requisiti = AbilitaRequisitoEditorSerializer(source='abilita_requisito_set', many=True, required=False)
    punteggi_assegnati = AbilitaPunteggioEditorSerializer(source='abilita_punteggio_set', many=True, required=False)
    prerequisiti = AbilitaPrerequisitoEditorSerializer(source='abilita_prerequisiti', many=True, required=False)
    statistiche = AbilitaStatisticaEditorSerializer(source='abilitastatistica_set', many=True, required=False)

    class Meta:
        model = Abilita
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        tiers_data = validated_data.pop('abilita_tier_set', [])
        req_data = validated_data.pop('abilita_requisito_set', [])
        punt_data = validated_data.pop('abilita_punteggio_set', [])
        pre_data = validated_data.pop('abilita_prerequisiti', [])
        stat_data = validated_data.pop('abilitastatistica_set', [])

        abilita = Abilita.objects.create(**validated_data)
        self._save_inlines(abilita, tiers_data, req_data, punt_data, pre_data, stat_data)
        return abilita

    @transaction.atomic
    def update(self, instance, validated_data):
        tiers_data = validated_data.pop('abilita_tier_set', None)
        req_data = validated_data.pop('abilita_requisito_set', None)
        punt_data = validated_data.pop('abilita_punteggio_set', None)
        pre_data = validated_data.pop('abilita_prerequisiti', None)
        stat_data = validated_data.pop('abilitastatistica_set', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._save_inlines(instance, tiers_data, req_data, punt_data, pre_data, stat_data)
        return instance

    def _save_inlines(self, instance, tiers, reqs, punts, pres, stats):
        # 1. Tiers
        if tiers is not None:
            instance.abilita_tier_set.all().delete()
            for item in tiers:
                abilita_tier.objects.create(abilita=instance, **item)

        # 2. Requisiti
        if reqs is not None:
            instance.abilita_requisito_set.all().delete()
            for item in reqs:
                abilita_requisito.objects.create(abilita=instance, **item)

        # 3. Punteggi Assegnati
        if punts is not None:
            instance.abilita_punteggio_set.all().delete()
            for item in punts:
                abilita_punteggio.objects.create(abilita=instance, **item)

        # 4. Prerequisiti
        if pres is not None:
            instance.abilita_prerequisiti.all().delete()
            for item in pres:
                abilita_prerequisito.objects.create(abilita=instance, **item)

        # 5. Statistiche
        if stats is not None:
            instance.abilitastatistica_set.all().delete()
            for item in stats:
                aure = item.pop('limit_a_aure', [])
                elementi = item.pop('limit_a_elementi', [])
                new_stat = AbilitaStatistica.objects.create(abilita=instance, **item)
                if aure: new_stat.limit_a_aure.set(aure)
                if elementi: new_stat.limit_a_elementi.set(elementi)
                
# SSO per OSSN 

class SSOUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        
        
# Serializers per tabelle

class AbilitaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abilita
        fields = ['id', 'nome']

class AbilitaTierSerializer(serializers.ModelSerializer):
    """Gestisce la relazione intermedia (abilita_tier)"""
    abilita_id = serializers.IntegerField(source='abilita.id')
    abilita_nome = serializers.CharField(source='abilita.nome', read_only=True)

    class Meta:
        model = abilita_tier
        fields = ['id', 'abilita_id', 'abilita_nome', 'ordine']

class TierStaffSerializer(serializers.ModelSerializer):
    abilita_collegate = serializers.SerializerMethodField()
    abilita_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tier
        fields = ['id', 'nome', 'tipo', 'descrizione', 'abilita_collegate', 'abilita_count']

    def get_abilita_collegate(self, obj):
        # CORRETTO: Filtra su 'tabella' (il nome del campo FK in abilita_tier)
        qs = abilita_tier.objects.filter(tabella=obj).order_by('ordine')
        return AbilitaTierSerializer(qs, many=True).data

    def create(self, validated_data):
        # Gestione custom per salvare le relazioni se passate, 
        # ma spesso è più facile gestire le relazioni in un secondo step o con logica separata.
        # Qui salvo solo il tier base, le abilità le gestiremo separatamente o nel frontend
        # inviando una lista. Per semplicità, qui creo il Tier.
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La vecchia password non è corretta.")
        return value

    def validate_new_password(self, value):
        # Qui puoi aggiungere validatori di complessità se vuoi
        if len(value) < 8:
            raise serializers.ValidationError("La password deve essere di almeno 8 caratteri.")
        return value