from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.conf import settings
from django.utils.html import format_html
from django.contrib.auth.models import User
from decimal import Decimal

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
    InfusioneStatisticaBase, TessituraStatisticaBase, ModelloAura,
    OggettoBase, OggettoBaseStatisticaBase, OggettoBaseModificatore, 
    ForgiaturaInCorso, 
    Inventario, OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    AttivataElemento, OggettoInInventario, Statistica, Personaggio, 
    CreditoMovimento, PersonaggioLog, TransazioneSospesa,
    Gruppo, Messaggio,
    ModelloAuraRequisitoCaratt, ModelloAuraRequisitoMattone,
    PropostaTecnica, 
    STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE, 
    LetturaMessaggio, Oggetto, ClasseOggetto,
    RichiestaAssemblaggio, OggettoCaratteristica, 
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
        fields = ('nome', 'sigla', 'parametro')


class PunteggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punteggio
        fields = (
            'id', # È sempre utile avere l'ID anche nel serializer base
            'nome', 'sigla', 'tipo', 'icona_url', 'icona_html', 
            'icona_cerchio_html', 'icona_cerchio_inverted_html', 
            'colore', 'aure_infusione_consentite', 'ordine',
            # AGGIUNTI QUESTI:
            'produce_mod', 'produce_materia', 'produce_innesti', 'produce_mutazioni'
        )


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


class PunteggioDetailSerializer(serializers.ModelSerializer):
    icona_url = serializers.SerializerMethodField()
    is_primaria = serializers.SerializerMethodField()
    valore_predefinito = serializers.SerializerMethodField()
    parametro = serializers.SerializerMethodField()
    has_models = serializers.SerializerMethodField()
    aura_id = serializers.SerializerMethodField()
    caratteristica_associata_nome = serializers.SerializerMethodField()

    class Meta:
        model = Punteggio
        fields = (
            'id', 'nome', 'sigla', 'tipo', 'colore',
            'icona_url',
            'is_primaria', 'valore_predefinito', 'parametro', 'ordine', 'has_models',
            'permette_infusioni', 'permette_tessiture',
            'is_mattone',
            'aura_id', 'caratteristica_associata_nome',
            'aure_infusione_consentite',
            # --- NUOVI CAMPI FONDAMENTALI PER IL FRONTEND ---
            'produce_mod', 
            'produce_materia', 
            'produce_innesti', 
            'produce_mutazioni',
        )
        
    def get_base_url(self):
        request = self.context.get('request')
        if request:
            return f"{request.scheme}://{request.get_host()}"
        return ""

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

    class Meta:
        model = Oggetto
        fields = [
            'id',
            'nome',
            'tipo_oggetto',
            'tipo_oggetto_display',
            'cariche_attuali',
            'infusione_nome'
        ]


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

            # Gestione Cariche e Origine
            'cariche_attuali',
            'infusione_generatrice',
            'infusione_nome',

            # Socketing
            'potenziamenti_installati'
        )

    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return getattr(obj, 'costo_acquisto', 0)


# -----------------------------------------------------------------------------
# SERIALIZER PER LE TECNICHE (INFUSIONE, TESSITURA, ATTIVATA)
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

    class Meta:
        model = PropostaTecnica
        fields = (
            'id', 'tipo', 'stato', 'nome', 'descrizione',
            'aura', 'aura_details', 'aura_infusione',
            'componenti', 'componenti_data',
            'livello', 'costo_invio_pagato', 'note_staff', 'data_creazione'
        )
        read_only_fields = ('stato', 'costo_invio_pagato', 'note_staff', 'data_creazione')

    def create(self, validated_data):
        comp_data = validated_data.pop('componenti_data', [])
        personaggio = self.context['personaggio']

        proposta = PropostaTecnica.objects.create(personaggio=personaggio, **validated_data)

        for item in comp_data:
            c_id = item.get('id')
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
                c_id = item.get('id')
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

    class Meta:
        model = OggettoBase
        fields = ('id', 'nome', 'descrizione', 'costo', 'tipo_oggetto', 'classe_oggetto_nome', 'is_tecnologico', 'attacco_base', 'stats_text')

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
    infusioni_possedute = serializers.SerializerMethodField()
    tessiture_possedute = serializers.SerializerMethodField()

    movimenti_credito = CreditoMovimentoSerializer(many=True, read_only=True)
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
            'movimenti_credito',
            'TestoFormattatoPersonale',
            'is_staff', 'modelli_aura',
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


class PersonaggioPublicSerializer(serializers.ModelSerializer):
    oggetti = OggettoSerializer(source='get_oggetti', many=True, read_only=True)

    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'testo', 'oggetti')


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


class PersonaggioListSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    tipologia = serializers.StringRelatedField(read_only=True)
    proprietario_nome = serializers.SerializerMethodField()

    class Meta:
        model = Personaggio
        fields = ('id', 'nome', 'proprietario', 'tipologia', 'proprietario_nome', 'data_nascita', 'data_morte')

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
    destinatario_personaggio = serializers.StringRelatedField(read_only=True)
    destinatario_gruppo = GruppoSerializer(read_only=True)
    is_letto = serializers.BooleanField(source='is_letto_db', read_only=True)

    class Meta:
        model = Messaggio
        fields = (
            'id', 'mittente', 'tipo_messaggio', 'titolo', 'testo', 'data_invio',
            'destinatario_personaggio', 'destinatario_gruppo', 'salva_in_cronologia', 'is_letto'
        )
        read_only_fields = ('mittente', 'data_invio', 'tipo_messaggio')


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
    class Meta:
        model = Personaggio
        fields = ('id', 'nome')


class MessaggioCreateSerializer(serializers.ModelSerializer):
    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Personaggio.objects.all(), source='destinatario_personaggio', write_only=True
    )

    class Meta:
        model = Messaggio
        fields = ('destinatario_id', 'titolo', 'testo')

    def create(self, validated_data):
        validated_data['mittente'] = self.context['request'].user
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
        fields = ['id', 'nome', 'mod_allowed_ids', 'materia_allowed_ids']

    def get_mod_allowed_ids(self, obj):
        # Recupera gli ID delle caratteristiche dalla relazione ManyToMany 'limitazioni_mod'
        return list(obj.limitazioni_mod.values_list('id', flat=True))

    def get_materia_allowed_ids(self, obj):
        # Recupera gli ID delle caratteristiche dalla relazione 'mattoni_materia_permessi'
        return list(obj.mattoni_materia_permessi.values_list('id', flat=True))