from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.conf import settings
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.db import models, transaction
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal


def _personaggio_avatar_url(personaggio, request):
    """URL assoluto della foto profilo InstaFame (SocialProfile.foto_principale), se presente."""
    try:
        sp = personaggio.social_profile
    except ObjectDoesNotExist:
        return None
    if sp.foto_principale:
        url = sp.foto_principale.url
        if request:
            return request.build_absolute_uri(url)
        return url
    return None

from .models import ConfigurazioneLivelloAura, formatta_testo_generico, ConsumabilePersonaggio
from . import qr_logic
# Importa i modelli e le funzioni helper
from .models import (
    AbilitaStatistica, AbilitaFormulaRule, ModelloAuraRequisitoDoppia, _get_icon_color_from_bg, 
    QrCode, Abilita, PuntiCaratteristicaMovimento, Tier, Punteggio, Tabella, 
    TipologiaPersonaggio, abilita_tier, abilita_requisito, abilita_sbloccata, 
    abilita_punteggio, abilita_punteggio_dipendente, abilita_prerequisito, Attivata, Manifesto, Nodo, NodoRewardConfig, A_vista, Mattone, InnescoTimer,
    AURA, 
    Infusione, Tessitura, 
    # NUOVI MODELLI INTERMEDI
    InfusioneCaratteristica, TessituraCaratteristica, PropostaTecnicaCaratteristica,
    InfusioneStatisticaBase, TessituraStatisticaBase, ModelloAura, InfusioneStatistica,
    CerimonialeCaratteristica,
    OggettoBase, OggettoBaseStatisticaBase, OggettoBaseModificatore, 
    ForgiaturaInCorso, 
    Inventario, OggettoStatistica, OggettoStatisticaBase, AttivataStatisticaBase, 
    AttivataElemento, OggettoInInventario,     Statistica, Personaggio, EffettoRisorsaTemporaneo,
    TessituraEffettoRuntime, TessituraOggettoRuntime,
    CreditoMovimento, PersonaggioLog, TransazioneSospesa, PropostaTransazione,
    Gruppo, Messaggio,
    ModelloAuraRequisitoCaratt, ModelloAuraRequisitoMattone,
    PropostaTecnica, 
    STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE, 
    STATO_TRANSAZIONE_IN_ATTESA,
    LetturaMessaggio, Oggetto, ClasseOggetto,
    RichiestaAssemblaggio, OggettoCaratteristica, 
    Cerimoniale, StatoTimerAttivo, MattoneStatistica, abilita_tier as AbilitaTier,
    TipologiaEffetto, EffettoCasuale, Dichiarazione,
    Korp, Carriera, SegnoZodiacale, TipoCarriera, Carica, CarrieraTierSblocco,
    PersonaggioCarrieraMembership,
    StatisticaContainer, StatisticaContainerItem,
    Era, Prefettura, Regione,
    Campagna,
    CampagnaUtente,
    CampagnaFeaturePolicy,
    CAMPAGNA_ROLE_HEAD_MASTER,
    WatchDeviceBinding,
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


class CampagnaSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        next_default = attrs.get("is_default", instance.is_default if instance else False)
        next_base = attrs.get("is_base", instance.is_base if instance else False)

        if instance and "is_default" in attrs and not next_default:
            others_default = Campagna.objects.exclude(id=instance.id).filter(is_default=True).exists()
            if not others_default:
                raise serializers.ValidationError({"is_default": "Deve esistere almeno una campagna default."})

        if instance and "is_base" in attrs and not next_base:
            others_base = Campagna.objects.exclude(id=instance.id).filter(is_base=True).exists()
            if not others_base:
                raise serializers.ValidationError({"is_base": "Deve esistere almeno una campagna base."})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        if instance.is_default:
            Campagna.objects.exclude(id=instance.id).filter(is_default=True).update(is_default=False)
        if instance.is_base:
            Campagna.objects.exclude(id=instance.id).filter(is_base=True).update(is_base=False)
        request = self.context.get("request")
        creator = getattr(request, "user", None)
        if creator and getattr(creator, "is_authenticated", False):
            CampagnaUtente.objects.update_or_create(
                campagna=instance,
                user=creator,
                defaults={
                    "ruolo": CAMPAGNA_ROLE_HEAD_MASTER,
                    "attivo": True,
                },
            )
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        next_default = validated_data.get("is_default", instance.is_default)
        next_base = validated_data.get("is_base", instance.is_base)
        instance = super().update(instance, validated_data)
        if next_default:
            Campagna.objects.exclude(id=instance.id).filter(is_default=True).update(is_default=False)
        if next_base:
            Campagna.objects.exclude(id=instance.id).filter(is_base=True).update(is_base=False)
        return instance

    class Meta:
        model = Campagna
        fields = (
            "id",
            "slug",
            "nome",
            "descrizione",
            "is_default",
            "is_base",
            "attiva",
        )


class CampagnaUtenteSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    campagna_nome = serializers.CharField(source="campagna.nome", read_only=True)

    class Meta:
        model = CampagnaUtente
        fields = (
            "id",
            "campagna",
            "campagna_nome",
            "user",
            "user_username",
            "ruolo",
            "attivo",
        )


class CampagnaFeaturePolicySerializer(serializers.ModelSerializer):
    campagna_nome = serializers.CharField(source="campagna.nome", read_only=True)

    class Meta:
        model = CampagnaFeaturePolicy
        fields = (
            "id",
            "campagna",
            "campagna_nome",
            "feature_key",
            "mode",
        )


class TierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tier
        fields = '__all__'


class TipoCarrieraSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCarriera
        fields = ("id", "sync_id", "codice", "nome", "ordine", "attivo", "updated_at")


class KorpSerializer(serializers.ModelSerializer):
    tipo_carriera = TipoCarrieraSerializer(read_only=True)

    class Meta:
        model = Korp
        fields = ("id", "nome", "descrizione", "tipo", "foto", "tipo_carriera", "sync_id", "updated_at")


class CarrieraSerializer(serializers.ModelSerializer):
    tipo_carriera = TipoCarrieraSerializer(read_only=True)
    tipo_carriera_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoCarriera.objects.filter(attivo=True),
        source="tipo_carriera",
        write_only=True,
    )

    class Meta:
        model = Carriera
        fields = (
            "id",
            "nome",
            "descrizione",
            "tipo",
            "foto",
            "tipo_carriera",
            "tipo_carriera_id",
            "sync_id",
            "updated_at",
        )


class SegnoZodiacaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SegnoZodiacale
        fields = "__all__"


class CaricaSerializer(serializers.ModelSerializer):
    carriera_nome = serializers.CharField(source="carriera.nome", read_only=True)
    tipo_carriera_codice = serializers.CharField(source="carriera.tipo_carriera.codice", read_only=True)

    class Meta:
        model = Carica
        fields = "__all__"


class PersonaggioCarrieraMembershipSerializer(serializers.ModelSerializer):
    carriera_nome = serializers.CharField(source="carriera.nome", read_only=True)
    carica_nome = serializers.CharField(source="carica.nome", read_only=True)
    tipo_carriera_codice = serializers.CharField(source="tipo_carriera.codice", read_only=True)
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True)

    class Meta:
        model = PersonaggioCarrieraMembership
        fields = "__all__"


class TipoCarrieraStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCarriera
        fields = "__all__"


class CarrieraStaffSerializer(serializers.ModelSerializer):
    tipo_carriera = serializers.PrimaryKeyRelatedField(queryset=TipoCarriera.objects.all())
    tipo_carriera_nome = serializers.CharField(source="tipo_carriera.nome", read_only=True)
    tipo_carriera_codice = serializers.CharField(source="tipo_carriera.codice", read_only=True)
    tiers_sblocco_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
    )
    tiers_sblocco_dettaglio = serializers.SerializerMethodField()

    class Meta:
        model = Carriera
        fields = (
            "id",
            "nome",
            "descrizione",
            "tipo",
            "foto",
            "tipo_carriera",
            "bonus_crediti_evento",
            "tipo_carriera_nome",
            "tipo_carriera_codice",
            "tiers_sblocco_ids",
            "tiers_sblocco_dettaglio",
            "sync_id",
            "updated_at",
        )
        extra_kwargs = {
            "tipo_carriera": {"required": True},
        }

    def get_tiers_sblocco_dettaglio(self, obj):
        return list(
            obj.tiers_sblocco.order_by("tipo", "nome").values("id", "nome", "tipo")
        )

    def _sync_tiers_sblocco(self, carriera, tier_ids):
        from personaggi.carriere_tier_sblocco import tiers_selezionabili_per_sblocco_carriera

        if tier_ids is None:
            return
        allowed = set(tiers_selezionabili_per_sblocco_carriera().filter(pk__in=tier_ids).values_list("pk", flat=True))
        CarrieraTierSblocco.objects.filter(carriera=carriera).exclude(tier_id__in=allowed).delete()
        existing = set(
            CarrieraTierSblocco.objects.filter(carriera=carriera).values_list("tier_id", flat=True)
        )
        for tid in allowed:
            if tid not in existing:
                CarrieraTierSblocco.objects.create(carriera=carriera, tier_id=tid)

    def create(self, validated_data):
        from personaggi.models import TIER_3

        tier_ids = validated_data.pop("tiers_sblocco_ids", None)
        tipo_carriera = validated_data.pop("tipo_carriera", None)
        validated_data.setdefault("tipo", TIER_3)
        carriera = Carriera.objects.create(tipo_carriera=tipo_carriera, **validated_data)
        self._sync_tiers_sblocco(carriera, tier_ids)
        return carriera

    def update(self, instance, validated_data):
        tier_ids = validated_data.pop("tiers_sblocco_ids", None)
        instance = super().update(instance, validated_data)
        self._sync_tiers_sblocco(instance, tier_ids)
        return instance


class CaricaStaffSerializer(serializers.ModelSerializer):
    carriera = serializers.PrimaryKeyRelatedField(queryset=Carriera.objects.all())
    carriera_nome = serializers.CharField(source="carriera.nome", read_only=True)

    class Meta:
        model = Carica
        fields = (
            "id",
            "sync_id",
            "updated_at",
            "carriera",
            "carriera_nome",
            "nome",
            "bonus_stipendio_evento",
            "bonus_crediti_evento",
            "ordine",
            "attiva",
        )
        read_only_fields = ("id", "sync_id", "updated_at", "carriera_nome")


class PersonaggioCarrieraMembershipStaffSerializer(serializers.ModelSerializer):
    personaggio = serializers.PrimaryKeyRelatedField(queryset=Personaggio.objects.all())
    carriera = serializers.PrimaryKeyRelatedField(queryset=Carriera.objects.all())
    tipo_carriera = serializers.PrimaryKeyRelatedField(queryset=TipoCarriera.objects.all())
    carica = serializers.PrimaryKeyRelatedField(
        queryset=Carica.objects.filter(attiva=True),
        allow_null=True,
        required=False,
    )
    carriera_nome = serializers.CharField(source="carriera.nome", read_only=True)
    carica_nome = serializers.CharField(source="carica.nome", read_only=True)
    tipo_carriera_codice = serializers.CharField(source="tipo_carriera.codice", read_only=True)
    personaggio_nome = serializers.SerializerMethodField()

    class Meta:
        model = PersonaggioCarrieraMembership
        fields = (
            "id",
            "sync_id",
            "updated_at",
            "personaggio",
            "personaggio_nome",
            "carriera",
            "tipo_carriera",
            "carica",
            "data_da",
            "data_a",
            "carriera_nome",
            "carica_nome",
            "tipo_carriera_codice",
        )
        read_only_fields = (
            "id",
            "sync_id",
            "updated_at",
            "personaggio_nome",
            "carriera_nome",
            "carica_nome",
            "tipo_carriera_codice",
        )

    def get_personaggio_nome(self, obj):
        pg = obj.personaggio
        if not pg:
            return ""
        owner = getattr(pg, "proprietario", None)
        if owner:
            login = owner.username or owner.email or str(owner.pk)
            return f"{pg.nome} ({login})"
        return pg.nome

    def validate(self, attrs):
        carriera = attrs.get("carriera") or getattr(self.instance, "carriera", None)
        carica = attrs.get("carica")
        if carica and carriera and carica.carriera_id != carriera.pk:
            raise serializers.ValidationError("La carica non appartiene alla carriera selezionata.")
        tipo = attrs.get("tipo_carriera")
        if carriera and tipo and carriera.tipo_carriera_id != tipo.pk:
            raise serializers.ValidationError("Il tipo non coincide con la carriera.")
        return attrs


class PrefetturaSerializer(serializers.ModelSerializer):
    era_nome = serializers.CharField(source="era.nome", read_only=True)
    era_abbreviazione = serializers.CharField(source="era.abbreviazione", read_only=True)
    regione_nome = serializers.CharField(source="regione.nome", read_only=True)
    regione_sigla = serializers.CharField(source="regione.sigla", read_only=True)

    class Meta:
        model = Prefettura
        fields = ("id", "era", "era_nome", "era_abbreviazione", "regione", "regione_nome", "regione_sigla", "nome", "descrizione", "ordine")


class EraAbilitaObbligatoriaSerializer(serializers.ModelSerializer):
    caratteristica = serializers.SerializerMethodField()

    class Meta:
        model = Abilita
        fields = ("id", "nome", "descrizione", "caratteristica")

    def get_caratteristica(self, obj):
        if not obj.caratteristica_id:
            return None
        return {
            "id": obj.caratteristica_id,
            "nome": obj.caratteristica.nome,
            "sigla": obj.caratteristica.sigla,
            "colore": obj.caratteristica.colore,
            "icona_url": obj.caratteristica.icona_url,
        }


class EraSerializer(serializers.ModelSerializer):
    prefetture = PrefetturaSerializer(many=True, read_only=True)
    abilita_obbligatorie = serializers.SerializerMethodField()

    class Meta:
        model = Era
        fields = (
            "id",
            "nome",
            "abbreviazione",
            "descrizione_breve",
            "descrizione",
            "difetto_interpretativo_titolo",
            "difetto_interpretativo_testo",
            "abilita_obbligatorie",
            "ordine",
            "attiva",
            "prefetture",
        )

    def get_abilita_obbligatorie(self, obj):
        qs = (
            Abilita.objects.filter(abilita_era__era=obj, abilita_era__is_default=True)
            .select_related("caratteristica")
            .order_by("abilita_era__ordine", "nome")
        )
        return EraAbilitaObbligatoriaSerializer(qs, many=True).data


class RegioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regione
        fields = ("id", "nome", "sigla", "descrizione", "ordine", "attiva")


class EraStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Era
        fields = "__all__"


class PrefetturaStaffSerializer(serializers.ModelSerializer):
    era_nome = serializers.CharField(source="era.nome", read_only=True)
    regione_nome = serializers.CharField(source="regione.nome", read_only=True)
    regione_sigla = serializers.CharField(source="regione.sigla", read_only=True)

    class Meta:
        model = Prefettura
        fields = ("id", "era", "era_nome", "regione", "regione_nome", "regione_sigla", "nome", "descrizione", "ordine", "sync_id", "updated_at")


class RegioneStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regione
        fields = "__all__"


class TabellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tabella
        fields = '__all__'


class StatisticaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statistica
        fields = ('id', 'nome', 'sigla', 'parametro', 'valore_base_predefinito', 'formula')


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
            'colore', 'icona_nome_originale', 'icona_nome_display', 'aure_infusione_consentite', 'ordine',
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
        tratti = Abilita.objects.filter(is_tratto_aura=True, aura_riferimento=obj).select_related(
            'caratteristica', 'caratteristica_2'
        )
        return AbilitaSmallSerializer(tratti, many=True).data


class PunteggioSmallSerializer(serializers.ModelSerializer):
    """ Serializer ridotto per l'uso in liste e relazioni """
    icona_nome_display = serializers.ReadOnlyField()
    class Meta:
        model = Punteggio
        fields = ('id', 'nome', 'sigla', 'colore', 'icona_url', 'icona_nome_originale', 'icona_nome_display', 'ordine',)


class StatisticaContainerItemSerializer(serializers.ModelSerializer):
    statistica_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = StatisticaContainerItem
        fields = (
            "id",
            "ordine",
            "dimensione",
            "is_dipendente",
            "nascondi_se_negativa",
            "nascondi_se_zero",
            "nascondi_se_uno",
            "statistica_id",
        )


class StatisticaContainerSerializer(serializers.ModelSerializer):
    parent_id = serializers.UUIDField(allow_null=True, read_only=True)
    icona_url = serializers.ReadOnlyField()
    icona_nome_display = serializers.ReadOnlyField()
    items = StatisticaContainerItemSerializer(many=True, read_only=True)

    class Meta:
        model = StatisticaContainer
        fields = (
            "id",
            "nome",
            "sigla",
            "ordine",
            "dimensione",
            "colore",
            "icona_url",
            "icona_nome_originale",
            "icona_nome_display",
            "parent_id",
            "render_in_primarie",
            "usa_colore_contenitore_per_figli",
            "items",
        )


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
    formula = serializers.SerializerMethodField()

    class Meta:
        model = Punteggio
        fields = (
            'id', 'nome', 'sigla', 'tipo', 'colore',
            'icona_url', 'icona_nome_originale', 'icona_nome_display',
            'is_primaria', 'valore_predefinito', 'valore_base_predefinito', 'parametro', 'ordine', 'has_models',
            'formula',
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

    def get_formula(self, obj):
        try:
            return bool(obj.statistica.formula)
        except Exception:
            return False
        
    def get_produce_mod(self, obj):
        # Logica: È un mod se produce potenziamenti ed è tecnologico (es. nome='Mod' o spegne a zero cariche)
        return obj.produce_potenziamenti and obj.nome_tipo_potenziamento == 'Mod'

    def get_produce_materia(self, obj):
        return obj.produce_potenziamenti and obj.nome_tipo_potenziamento == 'Materia'

    def get_produce_innesti(self, obj):
        return obj.produce_aumenti and obj.nome_tipo_aumento == 'Innesto'

    def get_produce_mutazioni(self, obj):
        return obj.produce_aumenti and obj.nome_tipo_aumento == 'Mutazione'
        
    def get_icona_url(self, obj):
        # Sempre path relativo (/media/...), come la property sul modello.
        # Così mirror, staging e prod servono i file dal proprio host (nessun URL fisso verso produzione).
        return obj.icona_url

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
        ).select_related('caratteristica', 'caratteristica_2')
        
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
    caratteristica_2 = PunteggioSmallSerializer(many=False, allow_null=True, read_only=True)
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
            'caratteristica_2',
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
    caratteristica_2 = PunteggioSmallSerializer(read_only=True, allow_null=True)
    aura_riferimento = PunteggioSmallSerializer(read_only=True, allow_null=True)
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
            'caratteristica', 'caratteristica_2', 'aura_riferimento', 'livello_riferimento',
            'requisiti', 'prerequisiti',
            'punteggi_assegnati', 'statistiche_modificate',
            'costo_pieno', 'costo_effettivo', 'is_tratto_aura', 'nascondi_in_scheda_abilita',
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
    deve_essere_attivato = serializers.SerializerMethodField()
    aura_dettagli = serializers.SerializerMethodField()
    slot_fisici_possibili = serializers.SerializerMethodField()

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
            'is_danneggiato',
            'slot_corpo',
            'slot_equip',
            'slot_fisici_possibili',
            'attacco_base',
            'attacco_formattato',

            # Gestione Cariche e Origine
            'cariche_attuali',
            'oggetto_base_generatore',
            'infusione_generatrice',
            'infusione_nome',

            # Socketing
            'potenziamenti_installati',
            'data_fine_attivazione', 
            'seconds_remaining',
            'is_active',
            'cariche_massime', 'durata_totale', 'testo_ricarica', 'costo_ricarica', 
            'spegne_a_zero_cariche',
            'deve_essere_attivato',
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

    def get_deve_essere_attivato(self, obj):
        return self.get_spegne_a_zero_cariche(obj)

    def get_slot_fisici_possibili(self, obj):
        from .services import GestioneOggettiService
        if obj.tipo_oggetto != 'FIS':
            return []
        return GestioneOggettiService._infer_physical_slots(obj)

    def get_attacco_formattato(self, obj):
        if not obj.attacco_base:
            return None
        
        personaggio = self.context.get('personaggio')
        # Passa le statistiche_base dell'oggetto per includere i valori base
        statistiche_base = obj.oggettostatisticabase_set.select_related('statistica').all()
        item_mods = obj.oggettostatistica_set.select_related('statistica').all()
        from .models import FORMULA_SCOPE_ATTACK

        context = {
            'livello': obj.livello,
            'aura': obj.aura,
            'item_modifiers': item_mods,
            'formula_kind': FORMULA_SCOPE_ATTACK,
            'attack_formula_template': obj.attacco_base,
        }

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
            'tipo_risultato', 'non_acquistabile',
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
            'usa_effetto_temporaneo', 'abilita_temporanea', 'durata_effetto_secondi', 'oggetto_runtime_config',
            'non_acquistabile',
        )

    def get_costo_effettivo(self, obj):
        personaggio = self.context.get('personaggio')
        if personaggio:
            return personaggio.get_costo_item_scontato(obj)
        return obj.costo_crediti


class TessituraOggettoRuntimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TessituraOggettoRuntime
        fields = (
            'id',
            'nome',
            'slot_key',
            'equipaggiato',
            'config_modificatori',
            'config_formule',
            'config_cariche',
        )


class TessituraEffettoRuntimeSerializer(serializers.ModelSerializer):
    tessitura_nome = serializers.CharField(source='tessitura.nome', read_only=True)
    abilita_temporanea_nome = serializers.CharField(source='abilita_temporanea.nome', read_only=True)
    abilita_temporanea_descrizione_html = serializers.SerializerMethodField()
    oggetto_runtime = TessituraOggettoRuntimeSerializer(read_only=True)
    secondi_rimanenti = serializers.SerializerMethodField()

    class Meta:
        model = TessituraEffettoRuntime
        fields = (
            'id',
            'tessitura',
            'tessitura_nome',
            'abilita_temporanea',
            'abilita_temporanea_nome',
            'abilita_temporanea_descrizione_html',
            'inizio',
            'fine',
            'is_attivo',
            'motivo_fine',
            'metadata',
            'secondi_rimanenti',
            'oggetto_runtime',
        )

    def get_abilita_temporanea_descrizione_html(self, obj):
        ab = getattr(obj, 'abilita_temporanea', None)
        if not ab:
            return ''
        personaggio = self.context.get('personaggio')
        if personaggio:
            html = personaggio.get_testo_formattato_per_item(ab)
            if html and str(html).strip():
                return html
        return ab.descrizione or ''

    def get_secondi_rimanenti(self, obj):
        delta = (obj.fine - timezone.now()).total_seconds()
        return max(0, int(delta))

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
            'TestoFormattato', 'costo_crediti', 'componenti', 'non_acquistabile'
        )


class InfusioneStaffListSerializer(serializers.ModelSerializer):
    """
    Payload leggero per lista staff infusioni.
    """
    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    has_qrcode = serializers.BooleanField(read_only=True)
    livello = serializers.IntegerField(source='livello_calc', read_only=True)

    class Meta:
        model = Infusione
        fields = ('id', 'nome', 'livello', 'aura_richiesta', 'has_qrcode', 'non_acquistabile')


class TessituraStaffListSerializer(serializers.ModelSerializer):
    """
    Payload leggero per lista staff tessiture.
    """
    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    has_qrcode = serializers.BooleanField(read_only=True)
    livello = serializers.IntegerField(source='livello_calc', read_only=True)

    class Meta:
        model = Tessitura
        fields = ('id', 'nome', 'livello', 'aura_richiesta', 'has_qrcode', 'non_acquistabile')


class CerimonialeStaffListSerializer(serializers.ModelSerializer):
    """
    Payload leggero per lista staff cerimoniali.
    """
    aura_richiesta = PunteggioSmallSerializer(read_only=True)
    has_qrcode = serializers.BooleanField(read_only=True)
    livello = serializers.IntegerField(source='liv', read_only=True)

    class Meta:
        model = Cerimoniale
        fields = ('id', 'nome', 'liv', 'livello', 'aura_richiesta', 'has_qrcode', 'non_acquistabile')

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
        from .models import QrCode

        rep = super().to_representation(instance)
        # Espande l'aura per permettere al frontend di vedere l'icona
        if instance.aura_richiesta:
            rep['aura_richiesta'] = PunteggioSmallSerializer(instance.aura_richiesta).data
        if instance.aura_infusione:
            rep['aura_infusione'] = PunteggioSmallSerializer(instance.aura_infusione).data
        if hasattr(instance, "has_qrcode"):
            rep["has_qrcode"] = bool(instance.has_qrcode)
        else:
            rep["has_qrcode"] = QrCode.objects.filter(vista_id=instance.pk).exists()
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
        from .models import QrCode

        rep = super().to_representation(instance)
        # Per la lista nel frontend servono gli oggetti completi, non solo gli ID
        rep['aura_richiesta'] = PunteggioSmallSerializer(instance.aura_richiesta).data if instance.aura_richiesta else None
        rep['elemento_principale'] = PunteggioSmallSerializer(instance.elemento_principale).data if instance.elemento_principale else None
        rep['abilita_temporanea'] = AbilitaSmallForPrereqSerializer(instance.abilita_temporanea).data if instance.abilita_temporanea else None
        if hasattr(instance, "has_qrcode"):
            rep["has_qrcode"] = bool(instance.has_qrcode)
        else:
            rep["has_qrcode"] = QrCode.objects.filter(vista_id=instance.pk).exists()
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
        from .models import QrCode

        rep = super().to_representation(instance)
        rep['aura_richiesta'] = PunteggioSmallSerializer(instance.aura_richiesta).data if instance.aura_richiesta else None
        if hasattr(instance, "has_qrcode"):
            rep["has_qrcode"] = bool(instance.has_qrcode)
        else:
            rep["has_qrcode"] = QrCode.objects.filter(vista_id=instance.pk).exists()
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
            'prerequisiti', 'svolgimento', 'effetto', 'spiegazione_teorie',
            'personaggio_nome', 'autore_nome',
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
        fields = ("id", "nome", "testo", "requisiti_lettura")


class ManifestoStaffSerializer(serializers.ModelSerializer):
    """CRUD staff manifesti (contenuto HTML in `testo`, requisiti opzionali)."""

    has_qrcode = serializers.BooleanField(read_only=True)

    class Meta:
        model = Manifesto
        fields = ("id", "nome", "testo", "requisiti_lettura", "has_qrcode")


class NodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nodo
        fields = (
            "id",
            "nome",
            "testo",
            "tipo_nodo",
        )


class NodoRewardConfigStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodoRewardConfig
        fields = (
            "id",
            "nome",
            "attiva",
            "prob_minore_to_maggiore",
            "prob_maggiore_to_minore",
            "cooldown_minuti_min",
            "cooldown_minuti_max",
        )


class NodoStaffSerializer(serializers.ModelSerializer):
    foto_posizione_url = serializers.SerializerMethodField()
    has_qrcode = serializers.BooleanField(read_only=True)
    reward_config_nome = serializers.CharField(source="reward_config.nome", read_only=True)

    def get_foto_posizione_url(self, obj):
        if not obj.foto_posizione:
            return None
        req = self.context.get("request")
        try:
            return req.build_absolute_uri(obj.foto_posizione.url) if req else obj.foto_posizione.url
        except Exception:
            return None

    class Meta:
        model = Nodo
        fields = (
            "id",
            "nome",
            "testo",
            "tipo_nodo",
            "disponibile_dal",
            "ultima_scansione_at",
            "foto_posizione",
            "foto_posizione_url",
            "campagna",
            "reward_config",
            "reward_config_nome",
            "has_qrcode",
        )
        read_only_fields = ("campagna",)


class InnescoTimerStaffSerializer(serializers.ModelSerializer):
    """Lettura include ID target; scrittura liste gestita nel ViewSet (`target_ere_ids` nel body)."""

    target_ere_ids = serializers.SerializerMethodField()
    target_regioni_ids = serializers.SerializerMethodField()
    target_korps_ids = serializers.SerializerMethodField()
    campagna = serializers.PrimaryKeyRelatedField(read_only=True)
    has_qrcode = serializers.BooleanField(read_only=True)

    class Meta:
        model = InnescoTimer
        fields = (
            "id",
            "nome",
            "testo",
            "modalita_target",
            "durata_secondi",
            "max_cariche",
            "rigenera_cariche_ogni_secondi",
            "segnale_luminoso",
            "campagna",
            "target_ere_ids",
            "target_regioni_ids",
            "target_korps_ids",
            "has_qrcode",
        )
        read_only_fields = ("campagna", "target_ere_ids", "target_regioni_ids", "target_korps_ids")

    def get_target_ere_ids(self, obj):
        return list(obj.target_ere.values_list("id", flat=True))

    def get_target_regioni_ids(self, obj):
        return list(obj.target_regioni.values_list("id", flat=True))

    def get_target_korps_ids(self, obj):
        return list(obj.target_korps.values_list("id", flat=True))


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
    has_qrcode = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventario
        fields = ('id', 'nome', 'testo', 'oggetti_count', 'is_personaggio', 'has_qrcode')
    
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


class TipologiaEffettoStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipologiaEffetto
        fields = '__all__'


class EffettoCasualeStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = EffettoCasuale
        fields = '__all__'


class DichiarazioneStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dichiarazione
        fields = '__all__'


class ConsumabilePersonaggioSerializer(serializers.ModelSerializer):
    """
    Serializer per consumabili del personaggio con descrizione e formula formattate.
    Usa get_testo_formattato_consumabile (formatta_testo_generico con statistiche_base, contesto,
    bonus del personaggio, get_testo_rango, formatta_valore_avanzato) come per le tessiture.
    """
    descrizione_formattata = serializers.SerializerMethodField()
    formula_formattata = serializers.SerializerMethodField()

    class Meta:
        model = ConsumabilePersonaggio
        fields = ('id', 'nome', 'descrizione', 'formula', 'descrizione_formattata', 'formula_formattata',
                  'utilizzi_rimanenti', 'data_scadenza', 'data_creazione')

    def _get_formattato_cache(self, obj):
        if getattr(obj, '_consumabile_formattato_cache', None) is None:
            personaggio = self.context.get('personaggio')
            if not personaggio:
                obj._consumabile_formattato_cache = (obj.descrizione or '', obj.formula or '')
            else:
                obj._consumabile_formattato_cache = personaggio.get_testo_formattato_consumabile(obj)
        return obj._consumabile_formattato_cache

    def get_descrizione_formattata(self, obj):
        return self._get_formattato_cache(obj)[0]

    def get_formula_formattata(self, obj):
        return self._get_formattato_cache(obj)[1]


class PersonaggioDetailSerializer(serializers.ModelSerializer):
    proprietario = serializers.StringRelatedField(read_only=True)
    crediti = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    punti_caratteristica = serializers.IntegerField(read_only=True)
    punteggi_base = serializers.JSONField(read_only=True)
    statistiche_base_dict = serializers.JSONField(read_only=True)
    modificatori_calcolati = serializers.JSONField(read_only=True)
    TestoFormattatoPersonale = serializers.JSONField(read_only=True, required=False)
    tipologia = TipologiaPersonaggioSerializer(read_only=True)

    abilita_possedute = serializers.SerializerMethodField()

    oggetti = serializers.SerializerMethodField()
    attivate_possedute = serializers.SerializerMethodField()
    infusioni_possedute = serializers.SerializerMethodField()
    tessiture_possedute = serializers.SerializerMethodField()
    cerimoniali_posseduti = serializers.SerializerMethodField()
    consumabili = serializers.SerializerMethodField()
    creazioni_consumabili_in_corso = serializers.SerializerMethodField()
    creazioni_consumabili_pronte = serializers.SerializerMethodField()
    valore_aura_alchimia = serializers.SerializerMethodField()

    movimenti_credito = CreditoMovimentoSerializer(many=True, read_only=True)
    is_staff = serializers.BooleanField(source='proprietario.is_staff', read_only=True)
    modelli_aura = ModelloAuraSerializer(many=True, read_only=True)
    
    lavori_pendenti_count = serializers.SerializerMethodField()
    messaggi_non_letti_count = serializers.SerializerMethodField()
    statistiche_primarie = serializers.SerializerMethodField()
    risorse_consumabili = serializers.JSONField(read_only=True)
    risorse_pool_ui = serializers.SerializerMethodField()
    effetti_risorsa_attivi = serializers.SerializerMethodField()
    tessiture_attive_runtime = serializers.SerializerMethodField()
    tessiture_runtime_slots_occupati = serializers.SerializerMethodField()
    rigenerazioni_auto_ui = serializers.SerializerMethodField()
    
    impostazioni_ui = serializers.JSONField(required=False, allow_null=True)
    can_edit_razza = serializers.SerializerMethodField()
    can_edit_era = serializers.SerializerMethodField()
    era = EraSerializer(read_only=True)
    prefettura = PrefetturaSerializer(read_only=True)
    prefettura_esterna = serializers.BooleanField(required=False)
    avatar_url = serializers.SerializerMethodField()
    watch_enabled = serializers.BooleanField(read_only=True)
    watch_binding = serializers.SerializerMethodField()

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'proprietario', 'data_nascita', 'data_morte', 'costume',
            'tipologia', 'crediti', 'punti_caratteristica',
            'punteggi_base', 'statistiche_base_dict', 'modificatori_calcolati',
            'abilita_possedute', 'oggetti',
            'attivate_possedute', 'infusioni_possedute', 'tessiture_possedute',
            'cerimoniali_posseduti',
            'consumabili', 'creazioni_consumabili_in_corso', 'creazioni_consumabili_pronte', 'valore_aura_alchimia',
            'movimenti_credito',
            'TestoFormattatoPersonale',
            'is_staff', 'modelli_aura',
            'lavori_pendenti_count', 'messaggi_non_letti_count', 'statistiche_primarie',
            'statistiche_temporanee',
            'risorse_consumabili', 'risorse_pool_ui', 'effetti_risorsa_attivi', 'tessiture_attive_runtime', 'tessiture_runtime_slots_occupati', 'rigenerazioni_auto_ui',
            'impostazioni_ui',
            'can_edit_razza',
            'can_edit_era',
            'era', 'prefettura', 'prefettura_esterna',
            'avatar_url',
            'watch_enabled', 'watch_binding',
        )

    def get_avatar_url(self, obj):
        return _personaggio_avatar_url(obj, self.context.get("request"))

    def get_watch_binding(self, obj):
        binding = (
            WatchDeviceBinding.objects.filter(personaggio=obj, is_active=True)
            .order_by("-updated_at")
            .first()
        )
        if not binding:
            return None
        return {
            "id": str(binding.id),
            "device_id": binding.device_id,
            "transport_mode": binding.transport_mode,
            "firmware_version": binding.firmware_version,
            "last_seen_at": binding.last_seen_at.isoformat() if binding.last_seen_at else None,
            "is_active": bool(binding.is_active),
        }

    def to_representation(self, instance):
        """
        Applica i tick di rigenerazione automatica prima di serializzare i campi.
        `statistiche_primarie` è valutata prima di `risorse_pool_ui` / `rigenerazioni_auto_ui`
        (che chiamano già sync): senza questo, valori corrente pool e ranghi restano obsoleti
        dopo il refetch post-timer.
        """
        instance.sync_recuperi_automatici()
        return super().to_representation(instance)

    def get_can_edit_razza(self, personaggio):
        """
        Razza (archetipo/forma AIN) modificabile solo finché il personaggio
        non ha partecipazioni a eventi già iniziati (o conclusi).
        """
        try:
            from django.utils import timezone
            now = timezone.now()
            return not personaggio.eventi_partecipati.filter(data_inizio__lte=now).exists()
        except Exception:
            # fallback conservativo: se non riusciamo a calcolare, non blocchiamo la UI
            return True

    def get_can_edit_era(self, personaggio):
        try:
            return personaggio.can_edit_era_prefettura()
        except Exception:
            return True

    def _get_event_mod_context_cache(self):
        """
        Cache per una singola serializzazione: evita di rifare query eventi in ogni get_*.
        """
        if not hasattr(self, "_event_mod_context_cache"):
            from .modificabilita import get_event_context
            self._event_mod_context_cache = get_event_context()
        return self._event_mod_context_cache

    def _is_modificabile_per_eventi(self, acquisizione_dt):
        from .modificabilita import is_modificabile_per_eventi
        event_in_corso, latest_event_start = self._get_event_mod_context_cache()
        return is_modificabile_per_eventi(
            acquisizione_dt,
            event_in_corso=event_in_corso,
            latest_event_start=latest_event_start,
        )

    def get_abilita_possedute(self, personaggio):
        from .models import PersonaggioAbilita
        from .modificabilita import get_abilita_bloccate_da_prerequisito

        abilita_qs = personaggio.abilita_possedute.all()
        abilita_ids = list(abilita_qs.values_list("id", flat=True))
        if not abilita_ids:
            return []

        # data_acquisizione per singola abilità posseduta
        pivots = (
            PersonaggioAbilita.objects.filter(personaggio=personaggio, abilita_id__in=abilita_ids)
            .values("abilita_id", "data_acquisizione", "costo_crediti_pagato", "costo_pc_pagato")
        )
        acq_map = {p["abilita_id"]: p["data_acquisizione"] for p in pivots}
        paid_cr_map = {p["abilita_id"]: p["costo_crediti_pagato"] for p in pivots}
        paid_pc_map = {p["abilita_id"]: p["costo_pc_pagato"] for p in pivots}

        # Vincolo: se l'abilità è prerequisito di almeno un'altra abilità posseduta, non è mai modificabile
        prereq_locked_ids = get_abilita_bloccate_da_prerequisito(abilita_ids)

        context_con_pg = {**self.context, "personaggio": personaggio}
        serialized = AbilitaMasterListSerializer(abilita_qs, many=True, context=context_con_pg).data
        abilita_by_id = {ab.id: ab for ab in abilita_qs}

        for item in serialized:
            ab_id = item.get("id")
            acquired_at = acq_map.get(ab_id)
            mod_base = self._is_modificabile_per_eventi(acquired_at)
            item["is_modifiable"] = bool(mod_base and ab_id not in prereq_locked_ids)
            if paid_cr_map.get(ab_id):
                item["costo_crediti_pagato"] = paid_cr_map[ab_id]
            if paid_pc_map.get(ab_id):
                item["costo_pc_pagato"] = paid_pc_map[ab_id]

            # Se è la forma camaleonte posseduta, mostra la formattazione con "forma del giorno"
            # direttamente sotto la descrizione nella scheda personaggio.
            ab_obj = abilita_by_id.get(ab_id)
            if ab_obj and ab_obj.pk == getattr(personaggio.get_tratto_camaleonte_posseduto(), "pk", None):
                item["descrizione"] = personaggio.get_testo_formattato_per_item(ab_obj)

        return serialized

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
        from .models import PersonaggioInfusione

        infusioni = personaggio.infusioni_possedute.all()
        infusioni_ids = list(infusioni.values_list("id", flat=True))
        if not infusioni_ids:
            return []

        pivots = (
            PersonaggioInfusione.objects.filter(personaggio=personaggio, infusione_id__in=infusioni_ids)
            .values("infusione_id", "data_acquisizione", "costo_crediti_pagato")
        )
        acq_map = {p["infusione_id"]: p["data_acquisizione"] for p in pivots}
        paid_map = {p["infusione_id"]: p["costo_crediti_pagato"] for p in pivots}

        risultati = []
        context_con_pg = {**self.context, "personaggio": personaggio}
        for inf in infusioni:
            dati = InfusioneSerializer(inf, context=context_con_pg).data
            dati["testo_formattato_personaggio"] = personaggio.get_testo_formattato_per_item(inf)
            dati["is_modifiable"] = bool(self._is_modificabile_per_eventi(acq_map.get(inf.id)))
            if paid_map.get(inf.id):
                dati["costo_crediti_pagato"] = paid_map[inf.id]
            risultati.append(dati)
        return risultati

    def get_tessiture_possedute(self, personaggio):
        from .models import PersonaggioTessitura
        tessiture = personaggio.tessiture_possedute.all()
        tessiture_ids = list(tessiture.values_list("id", flat=True))
        if not tessiture_ids:
            return []

        pivots = (
            PersonaggioTessitura.objects.filter(personaggio=personaggio, tessitura_id__in=tessiture_ids)
            .values("tessitura_id", "data_acquisizione", "is_favorite", "costo_crediti_pagato")
        )
        acq_map = {p["tessitura_id"]: p["data_acquisizione"] for p in pivots}
        fav_map = {p["tessitura_id"]: p["is_favorite"] for p in pivots}
        paid_map = {p["tessitura_id"]: p["costo_crediti_pagato"] for p in pivots}

        risultati = []
        context_con_pg = {**self.context, "personaggio": personaggio}
        for tes in tessiture:
            dati = TessituraSerializer(tes, context=context_con_pg).data
            dati["testo_formattato_personaggio"] = personaggio.get_testo_formattato_per_item(tes)
            dati["is_favorite"] = bool(fav_map.get(tes.id, False))
            dati["is_modifiable"] = bool(self._is_modificabile_per_eventi(acq_map.get(tes.id)))
            if paid_map.get(tes.id):
                dati["costo_crediti_pagato"] = paid_map[tes.id]
            risultati.append(dati)
        return risultati

    def get_cerimoniali_posseduti(self, personaggio):
        from .models import PersonaggioCerimoniale

        cerimoniali = personaggio.cerimoniali_posseduti.all()
        cer_ids = list(cerimoniali.values_list("id", flat=True))
        if not cer_ids:
            return []

        pivots = (
            PersonaggioCerimoniale.objects.filter(personaggio=personaggio, cerimoniale_id__in=cer_ids)
            .values("cerimoniale_id", "data_acquisizione", "costo_crediti_pagato")
        )
        acq_map = {p["cerimoniale_id"]: p["data_acquisizione"] for p in pivots}
        paid_map = {p["cerimoniale_id"]: p["costo_crediti_pagato"] for p in pivots}

        context_con_pg = {**self.context, "personaggio": personaggio}
        serialized = CerimonialeSerializer(cerimoniali, many=True, context=context_con_pg).data

        for item in serialized:
            cid = item.get("id")
            item["is_modifiable"] = bool(self._is_modificabile_per_eventi(acq_map.get(cid)))
            if paid_map.get(cid):
                item["costo_crediti_pagato"] = paid_map[cid]

        return serialized

    def get_creazioni_consumabili_in_corso(self, personaggio):
        from django.utils import timezone
        from .models import CreazioneConsumabileInCorso
        now = timezone.now()
        creazioni = CreazioneConsumabileInCorso.objects.filter(
            personaggio=personaggio, completata=False, data_fine_creazione__gt=now
        ).select_related('tessitura').order_by('data_fine_creazione')
        risultati = []
        for cc in creazioni:
            delta = (cc.data_fine_creazione - now).total_seconds()
            risultati.append({
                'id': cc.id,
                'tessitura_id': cc.tessitura_id,
                'tessitura_nome': cc.tessitura.nome,
                'data_fine_creazione': cc.data_fine_creazione.isoformat(),
                'secondi_rimanenti': max(0, int(delta)),
            })
        return risultati

    def get_creazioni_consumabili_pronte(self, personaggio):
        from django.utils import timezone
        from .models import CreazioneConsumabileInCorso
        now = timezone.now()
        creazioni = CreazioneConsumabileInCorso.objects.filter(
            personaggio=personaggio, completata=False, data_fine_creazione__lte=now
        ).select_related('tessitura').order_by('data_fine_creazione')
        return [{'id': cc.id, 'tessitura_id': cc.tessitura_id, 'tessitura_nome': cc.tessitura.nome} for cc in creazioni]

    def get_valore_aura_alchimia(self, personaggio):
        from .models import Punteggio, AURA
        aura_alc = Punteggio.objects.filter(tipo=AURA, sigla='ALC').first()
        if not aura_alc:
            return 0
        return personaggio.get_valore_aura_effettivo(aura_alc)

    def get_consumabili(self, personaggio):
        from django.utils import timezone
        from django.db.models import Prefetch
        oggi = timezone.now().date()
        consumabili = personaggio.consumabili.filter(
            utilizzi_rimanenti__gt=0,
            data_scadenza__gte=oggi
        ).select_related(
            'tessitura', 'tessitura__aura_richiesta', 'tessitura__elemento_principale',
            'effetto_casuale', 'effetto_casuale__tipologia', 'effetto_casuale__elemento_principale'
        ).prefetch_related(
            Prefetch('tessitura__tessiturastatisticabase_set', queryset=TessituraStatisticaBase.objects.select_related('statistica')),
            'tessitura__componenti__caratteristica',
        ).order_by('-data_creazione')
        context_con_pg = {**self.context, 'personaggio': personaggio}
        return ConsumabilePersonaggioSerializer(consumabili, many=True, context=context_con_pg).data
    
    def get_lavori_pendenti_count(self, obj):
        return obj.richieste_assemblaggio_ricevute.filter(stato='PEND').count()

    def get_messaggi_non_letti_count(self, obj):
        return obj.messaggi_ricevuti_individuali.exclude(stati_lettura__letto=True).count() # Semplificato

    def get_statistiche_primarie(self, obj):
        # Restituisce una lista strutturata delle stat primarie per il GameTab
        stats = []
        for stat in Statistica.objects.filter(is_primaria=True):
            val_max = obj.get_valore_statistica(stat.sigla)
            if stat.is_risorsa_pool:
                val_current = obj.get_risorsa_corrente(stat.sigla)
            else:
                val_current = obj.statistiche_temporanee.get(stat.sigla, val_max)
            stats.append({
                'sigla': stat.sigla,
                'nome': stat.nome,
                'colore': getattr(stat, 'colore', None),
                'valore_max': val_max,
                'valore_corrente': val_current
            })
        return stats

    def get_risorse_pool_ui(self, obj):
        """Pool consumabili (Fortuna e future statistiche is_risorsa_pool)."""
        out = []
        rec_map = obj.get_recuperi_risorsa_stato()
        for stat in Statistica.objects.filter(is_risorsa_pool=True).order_by('-formula', 'ordine', 'nome'):
            # Visibilità: massimo di scheda della statistica (non il solo runtime da massimo_pool_sigla).
            if obj.get_valore_statistica(stat.sigla) <= 0:
                continue
            max_v = obj.get_valore_massimo_risorsa_runtime(stat.sigla)
            if max_v <= 0:
                continue
            cur = obj.get_risorsa_corrente(stat.sigla)
            rec = rec_map.get(stat.sigla) or {}
            out.append({
                'sigla': stat.sigla,
                'nome': stat.nome,
                'colore': getattr(stat, 'colore', None),
                'descrizione': stat.descrizione or '',
                'valore_max': max_v,
                'valore_corrente': cur,
                'recupero_auto': {
                    'active': bool(rec.get('active')),
                    'next_tick_at': rec.get('next_tick_at').isoformat() if rec.get('next_tick_at') else None,
                    'seconds_to_next_tick': rec.get('seconds_to_next_tick'),
                    'step': rec.get('step'),
                    'interval_seconds': rec.get('interval_seconds'),
                },
            })
        return out

    def get_effetti_risorsa_attivi(self, obj):
        now = timezone.now()
        qs = EffettoRisorsaTemporaneo.objects.filter(personaggio=obj, scadenza__gt=now).select_related('abilita')
        return [
            {
                'id': str(e.id),
                'stat_sigla': e.statistica_risorsa_sigla,
                'abilita_nome': e.abilita.nome if e.abilita else None,
                'scadenza': e.scadenza.isoformat(),
                'durata_tipo': e.durata_tipo,
                'modifiche': e.modifiche or [],
            }
            for e in qs
        ]

    def get_tessiture_attive_runtime(self, obj):
        runtime_qs = obj.get_tessiture_runtime_attive()
        ctx = {**self.context, 'personaggio': obj}
        return TessituraEffettoRuntimeSerializer(runtime_qs, many=True, context=ctx).data

    def get_tessiture_runtime_slots_occupati(self, obj):
        runtime_qs = obj.get_tessiture_runtime_attive()
        slots = []
        for rt in runtime_qs:
            rt_obj = getattr(rt, 'oggetto_runtime', None)
            if rt_obj and rt_obj.equipaggiato and rt_obj.slot_key:
                slots.append(rt_obj.slot_key)
        return sorted(set(slots))

    def get_rigenerazioni_auto_ui(self, obj):
        rec_map = obj.get_recuperi_risorsa_stato()
        out = []
        for sigla, rec in rec_map.items():
            if obj.get_valore_statistica(sigla) <= 0:
                continue
            stat_obj = Statistica.objects.filter(sigla=sigla).first()
            max_v = obj.get_valore_massimo_risorsa_runtime(sigla)
            if max_v <= 0:
                continue
            cur = obj.get_risorsa_corrente_runtime(sigla)
            out.append({
                'sigla': sigla,
                'nome': stat_obj.nome if stat_obj else sigla,
                'active': bool(rec.get('active')),
                'paused': bool(rec.get('paused')),
                'valore_corrente': cur,
                'valore_max': max_v,
                'next_tick_at': rec.get('next_tick_at').isoformat() if rec.get('next_tick_at') else None,
                'seconds_to_next_tick': rec.get('seconds_to_next_tick'),
                'step': rec.get('step'),
                'interval_seconds': rec.get('interval_seconds'),
                'abilita_nomi': rec.get('abilita_nomi') or [],
            })
        return sorted(out, key=lambda x: x['sigla'])


# Chiavi estratte da PersonaggioDetailSerializer per cache offline (IndexedDB / mesh instabile).
# Mantenerle allineate a GameTab e alle esigenze di consultazione in campo.
OFFLINE_GAME_STATE_KEYS = (
    "id",
    "nome",
    "data_morte",
    "statistiche_primarie",
    "statistiche_temporanee",
    "risorse_consumabili",
    "risorse_pool_ui",
    "effetti_risorsa_attivi",
    "tessiture_attive_runtime",
    "tessiture_runtime_slots_occupati",
    "rigenerazioni_auto_ui",
    "abilita_possedute",
    "tessiture_possedute",
    "cerimoniali_posseduti",
    "attivate_possedute",
    "infusioni_possedute",
    "oggetti",
    "consumabili",
    "creazioni_consumabili_in_corso",
    "creazioni_consumabili_pronte",
    "lavori_pendenti_count",
    "impostazioni_ui",
)


def serialize_personaggio_offline_game_state(personaggio, request):
    """
    Snapshot compatto per consultazione offline sul client (PWA).
    Riutilizza PersonaggioDetailSerializer per evitare drift di regole di gioco.
    """
    serializer = PersonaggioDetailSerializer(personaggio, context={"request": request})
    detail = serializer.data
    payload = {key: detail[key] for key in OFFLINE_GAME_STATE_KEYS if key in detail}
    updated_at = getattr(personaggio, "updated_at", None)
    return {
        **payload,
        "snapshot_server_at": timezone.now().isoformat(),
        "personaggio_updated_at": updated_at.isoformat() if updated_at else None,
    }


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
    segno_zodiacale = serializers.PrimaryKeyRelatedField(read_only=True)
    segno_zodiacale_nome = serializers.CharField(source="segno_zodiacale.nome", read_only=True)
    era = serializers.PrimaryKeyRelatedField(queryset=Era.objects.filter(attiva=True), allow_null=True, required=False)
    prefettura = serializers.PrimaryKeyRelatedField(queryset=Prefettura.objects.all(), allow_null=True, required=False)
    prefettura_esterna = serializers.BooleanField(required=False)
    era_nome = serializers.CharField(source="era.nome", read_only=True)
    prefettura_nome = serializers.CharField(source="prefettura.nome", read_only=True)
    prefettura_era_nome = serializers.CharField(source="prefettura.era.nome", read_only=True)
    prefettura_regione_sigla = serializers.CharField(source="prefettura.regione.sigla", read_only=True)
    campagna = serializers.PrimaryKeyRelatedField(queryset=Campagna.objects.filter(attiva=True), required=False)
    campagna_nome = serializers.CharField(source="campagna.nome", read_only=True)
    
    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'costume', 
            'tipologia', 'tipologia_nome', 
            'proprietario', 'data_nascita', 'data_morte',
            'crediti', 'punti_caratteristica',
            'giocante', 'proprietario_id', 'is_staff',
            'segno_zodiacale', 'segno_zodiacale_nome',
            'campagna', 'campagna_nome',
            'era', 'prefettura', 'prefettura_esterna', 'era_nome', 'prefettura_nome', 'prefettura_era_nome', 'prefettura_regione_sigla',
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
    tipologia_giocante = serializers.SerializerMethodField()
    proprietario = serializers.StringRelatedField(read_only=True)
    segno_zodiacale = serializers.PrimaryKeyRelatedField(read_only=True)
    segno_zodiacale_nome = serializers.CharField(source="segno_zodiacale.nome", read_only=True)
    era = serializers.PrimaryKeyRelatedField(queryset=Era.objects.filter(attiva=True), allow_null=True, required=False)
    prefettura = serializers.PrimaryKeyRelatedField(queryset=Prefettura.objects.all(), allow_null=True, required=False)
    prefettura_esterna = serializers.BooleanField(required=False)
    era_nome = serializers.CharField(source="era.nome", read_only=True)
    prefettura_nome = serializers.CharField(source="prefettura.nome", read_only=True)
    prefettura_era_nome = serializers.CharField(source="prefettura.era.nome", read_only=True)
    prefettura_regione_sigla = serializers.CharField(source="prefettura.regione.sigla", read_only=True)
    campagna = serializers.PrimaryKeyRelatedField(queryset=Campagna.objects.filter(attiva=True), required=False)
    campagna_nome = serializers.CharField(source="campagna.nome", read_only=True)
    can_edit_razza = serializers.SerializerMethodField()
    can_edit_era = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    impostazioni_ui = serializers.JSONField(required=False)

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'testo', 'costume',
            'tipologia', 'tipologia_nome', 'tipologia_giocante',
            'proprietario', 'data_nascita', 'data_morte',
            'crediti', 'punti_caratteristica',
            'watch_enabled',
            'segno_zodiacale', 'segno_zodiacale_nome',
            'campagna', 'campagna_nome',
            'era', 'prefettura', 'prefettura_esterna', 'era_nome', 'prefettura_nome', 'prefettura_era_nome', 'prefettura_regione_sigla',
            'can_edit_razza', 'can_edit_era',
            'avatar_url',
            'impostazioni_ui',
        )
        read_only_fields = ('crediti', 'punti_caratteristica', 'proprietario')

    def get_avatar_url(self, obj):
        return _personaggio_avatar_url(obj, self.context.get("request"))

    def get_tipologia_giocante(self, obj):
        t = getattr(obj, "tipologia", None)
        return bool(t and getattr(t, "giocante", False))

    def get_can_edit_razza(self, personaggio):
        try:
            from django.utils import timezone
            now = timezone.now()
            return not personaggio.eventi_partecipati.filter(data_inizio__lte=now).exists()
        except Exception:
            return True

    def get_can_edit_era(self, personaggio):
        try:
            return personaggio.can_edit_era_prefettura()
        except Exception:
            return True

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
    era = serializers.PrimaryKeyRelatedField(read_only=True)
    prefettura = serializers.PrimaryKeyRelatedField(read_only=True)
    prefettura_esterna = serializers.BooleanField(read_only=True)
    era_nome = serializers.CharField(source="era.nome", read_only=True)
    prefettura_nome = serializers.CharField(source="prefettura.nome", read_only=True)
    prefettura_era_nome = serializers.CharField(source="prefettura.era.nome", read_only=True)
    prefettura_regione_sigla = serializers.CharField(source="prefettura.regione.sigla", read_only=True)
    campagna = serializers.PrimaryKeyRelatedField(read_only=True)
    campagna_nome = serializers.CharField(source="campagna.nome", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Personaggio
        fields = (
            'id', 'nome', 'proprietario', 'tipologia', 
            'proprietario_nome', 'data_nascita', 'data_morte',
            'testo', 'costume', 'crediti', 'punti_caratteristica',
            'campagna', 'campagna_nome',
            'era', 'prefettura', 'prefettura_esterna',
            'era_nome', 'prefettura_nome', 'prefettura_era_nome', 'prefettura_regione_sigla',
            'avatar_url',
            'watch_enabled',
            )
        read_only_fields = ('crediti', 'punti_caratteristica') 

    def get_avatar_url(self, obj):
        return _personaggio_avatar_url(obj, self.context.get("request"))

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
            qr = QrCode.objects.select_related("vista").get(id=str(data.get("qrcode_id")))
            if not qr.vista:
                raise serializers.ValidationError("QrCode vuoto.")
            self.context["qr_code"] = qr
            v = qr.vista
            if hasattr(v, "oggetto"):
                item = v.oggetto
            elif hasattr(v, "attivata"):
                item = v.attivata
            elif hasattr(v, "infusione"):
                item = v.infusione
            elif hasattr(v, "tessitura"):
                item = v.tessitura
            elif hasattr(v, "cerimoniale"):
                item = v.cerimoniale
            else:
                raise serializers.ValidationError(
                    "Questo QR non supporta l'acquisizione da questa azione (es. manifesto, inventario, innesco timer)."
                )
            self.context["item"] = item
            if isinstance(item, Oggetto):
                ok, msg = qr_logic.oggetto_puo_essere_acquisito_da_qr(self.context["richiedente"], item)
                if not ok:
                    raise serializers.ValidationError(msg)
        except serializers.ValidationError:
            raise
        except QrCode.DoesNotExist:
            raise serializers.ValidationError("QrCode non valido.")
        except Exception:
            raise serializers.ValidationError("QrCode non valido.")
        return data

    def save(self):
        item = self.context["item"]
        pg = self.context["richiedente"]
        qr = self.context["qr_code"]
        with transaction.atomic():
            if isinstance(item, Oggetto):
                item.sposta_in_inventario(pg)
            elif isinstance(item, Attivata):
                pg.attivate_possedute.add(item)
            elif isinstance(item, Infusione):
                pg.infusioni_possedute.add(item)
            elif isinstance(item, Tessitura):
                pg.tessiture_possedute.add(item)
            elif isinstance(item, Cerimoniale):
                pg.cerimoniali_posseduti.add(item)
            qr.vista = None
            qr.save()
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
            'crediti_allegati', 'oggetti_allegati_snapshot',
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
        if obj.mittente_personaggio:
            return obj.mittente_personaggio.nome
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
    mittente_personaggio_id = serializers.PrimaryKeyRelatedField(
        queryset=Personaggio.objects.all(), source='mittente_personaggio', write_only=True, required=False, allow_null=True
    )
    crediti_da_inviare = serializers.IntegerField(required=False, min_value=0, default=0)
    oggetti_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        default=list,
    )

    class Meta:
        model = Messaggio
        fields = (
            'destinatario_id',
            'titolo',
            'testo',
            'is_staff_message',
            'mittente_personaggio_id',
            'crediti_da_inviare',
            'oggetti_ids',
        )

    def create(self, validated_data):
        validated_data.pop('crediti_da_inviare', None)
        validated_data.pop('oggetti_ids', None)
        validated_data['mittente'] = self.context['request'].user
        campagna = None
        mittente_pg = validated_data.get('mittente_personaggio')
        destinatario_pg = validated_data.get('destinatario_personaggio')
        if mittente_pg:
            campagna = mittente_pg.campagna
        elif destinatario_pg:
            campagna = destinatario_pg.campagna
        if not campagna:
            campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.filter(is_default=True).first()
        if campagna:
            validated_data['campagna'] = campagna
        
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

    def to_representation(self, instance):
        from .models import QrCode

        rep = super().to_representation(instance)
        rep['aura'] = PunteggioSmallSerializer(instance.aura).data if instance.aura else None
        rep['classe_oggetto'] = {
            'id': instance.classe_oggetto.id,
            'nome': instance.classe_oggetto.nome,
        } if instance.classe_oggetto else None
        rep['classe_oggetto_nome'] = instance.classe_oggetto.nome if instance.classe_oggetto else ''
        if hasattr(instance, "has_qrcode"):
            rep["has_qrcode"] = bool(instance.has_qrcode)
        else:
            rep["has_qrcode"] = QrCode.objects.filter(vista_id=instance.pk).exists()
        return rep

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

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['classe_oggetto'] = {
            'id': instance.classe_oggetto.id,
            'nome': instance.classe_oggetto.nome,
        } if instance.classe_oggetto else None
        rep['classe_oggetto_nome'] = instance.classe_oggetto.nome if instance.classe_oggetto else ''
        return rep

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

class AbilitaPunteggioDipendenteEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_punteggio_dipendente
        fields = ['punteggio_target', 'incremento', 'ogni_x', 'punteggio_sorgente']
        read_only_fields = ['abilita']

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


class AbilitaFormulaRuleEditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbilitaFormulaRule
        fields = "__all__"
        read_only_fields = ["abilita"]
        validators = []

class AbilitaFullEditorSerializer(serializers.ModelSerializer):
    """
    Serializer completo per CRUD Abilità lato Staff.
    Gestisce salvataggio atomico di tutte le inlines.
    """
    tiers = AbilitaTierEditorSerializer(source='abilita_tier_set', many=True, required=False)
    requisiti = AbilitaRequisitoEditorSerializer(source='abilita_requisito_set', many=True, required=False)
    punteggi_assegnati = AbilitaPunteggioEditorSerializer(source='abilita_punteggio_set', many=True, required=False)
    punteggi_dipendenti = AbilitaPunteggioDipendenteEditorSerializer(many=True, required=False)
    prerequisiti = AbilitaPrerequisitoEditorSerializer(source='abilita_prerequisiti', many=True, required=False)
    statistiche = AbilitaStatisticaEditorSerializer(source='abilitastatistica_set', many=True, required=False)
    formula_rules = AbilitaFormulaRuleEditorSerializer(many=True, required=False)

    class Meta:
        model = Abilita
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['aura_riferimento'] = PunteggioSmallSerializer(instance.aura_riferimento).data if instance.aura_riferimento else None
        return rep

    @transaction.atomic
    def create(self, validated_data):
        tiers_data = validated_data.pop('abilita_tier_set', [])
        req_data = validated_data.pop('abilita_requisito_set', [])
        punt_data = validated_data.pop('abilita_punteggio_set', [])
        punt_dep_data = validated_data.pop('punteggi_dipendenti', [])
        pre_data = validated_data.pop('abilita_prerequisiti', [])
        stat_data = validated_data.pop('abilitastatistica_set', [])
        formula_rules_data = validated_data.pop('formula_rules', [])

        abilita = Abilita.objects.create(**validated_data)
        self._save_inlines(abilita, tiers_data, req_data, punt_data, punt_dep_data, pre_data, stat_data, formula_rules_data)
        return abilita

    @transaction.atomic
    def update(self, instance, validated_data):
        tiers_data = validated_data.pop('abilita_tier_set', None)
        req_data = validated_data.pop('abilita_requisito_set', None)
        punt_data = validated_data.pop('abilita_punteggio_set', None)
        punt_dep_data = validated_data.pop('punteggi_dipendenti', None)
        pre_data = validated_data.pop('abilita_prerequisiti', None)
        stat_data = validated_data.pop('abilitastatistica_set', None)
        formula_rules_data = validated_data.pop('formula_rules', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        self._save_inlines(instance, tiers_data, req_data, punt_data, punt_dep_data, pre_data, stat_data, formula_rules_data)
        return instance

    def _save_inlines(self, instance, tiers, reqs, punts, punt_deps, pres, stats, formula_rules):
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

        # 4. Punteggi Dipendenti
        if punt_deps is not None:
            instance.punteggi_dipendenti.all().delete()
            for item in punt_deps:
                abilita_punteggio_dipendente.objects.create(abilita=instance, **item)

        # 5. Prerequisiti
        if pres is not None:
            instance.abilita_prerequisiti.all().delete()
            for item in pres:
                abilita_prerequisito.objects.create(abilita=instance, **item)

        # 6. Statistiche
        if stats is not None:
            instance.abilitastatistica_set.all().delete()
            for item in stats:
                aure = item.pop('limit_a_aure', [])
                elementi = item.pop('limit_a_elementi', [])
                new_stat = AbilitaStatistica.objects.create(abilita=instance, **item)
                if aure: new_stat.limit_a_aure.set(aure)
                if elementi: new_stat.limit_a_elementi.set(elementi)

        # 7. Regole semantiche formula
        if formula_rules is not None:
            instance.formula_rules.all().delete()
            for item in formula_rules:
                AbilitaFormulaRule.objects.create(abilita=instance, **item)
                
# SSO per OSSN 

class SSOUserSerializer(serializers.ModelSerializer):
    """Profilo utente corrente (token). Include flag staff per allineare la UI al backend."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
        
        
# Serializers per tabelle

class AbilitaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abilita
        fields = ['id', 'nome']


class AbilitaStaffListSerializer(serializers.ModelSerializer):
    """Serializer leggero per la lista staff delle abilita."""
    aura_riferimento = PunteggioSmallSerializer(read_only=True)

    class Meta:
        model = Abilita
        fields = [
            'id',
            'sync_id',
            'nome',
            'costo_pc',
            'costo_crediti',
            'is_tratto_aura',
            'nascondi_in_scheda_abilita',
            'aura_riferimento',
            'livello_riferimento',
        ]

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
    caratteristiche_visibili = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Punteggio.objects.filter(tipo='CA'),
        required=False,
    )
    caratteristiche_visibili_dettaglio = serializers.SerializerMethodField()

    class Meta:
        model = Tier
        fields = [
            'id',
            'nome',
            'tipo',
            'descrizione',
            'caratteristiche_visibili',
            'caratteristiche_visibili_dettaglio',
            'abilita_collegate',
            'abilita_count',
        ]

    def get_abilita_collegate(self, obj):
        # CORRETTO: Filtra su 'tabella' (il nome del campo FK in abilita_tier)
        qs = abilita_tier.objects.filter(tabella=obj).order_by('ordine')
        return AbilitaTierSerializer(qs, many=True).data

    def create(self, validated_data):
        # Gestione custom per salvare le relazioni se passate, 
        # ma spesso è più facile gestire le relazioni in un secondo step o con logica separata.
        # Qui salvo solo il tier base, le abilità le gestiremo separatamente o nel frontend
        # inviando una lista. Per semplicità, qui creo il Tier.
        caratteristiche = validated_data.pop('caratteristiche_visibili', [])
        self._validate_characteristics_count(validated_data.get('tipo'), len(caratteristiche))
        tier = super().create(validated_data)
        if caratteristiche:
            tier.caratteristiche_visibili.set(caratteristiche)
        return tier

    def update(self, instance, validated_data):
        caratteristiche = validated_data.pop('caratteristiche_visibili', None)
        tipo = validated_data.get('tipo', instance.tipo)
        if caratteristiche is not None:
            self._validate_characteristics_count(tipo, len(caratteristiche))
        tier = super().update(instance, validated_data)
        if caratteristiche is not None:
            tier.caratteristiche_visibili.set(caratteristiche)
        return tier

    def get_caratteristiche_visibili_dettaglio(self, obj):
        return list(
            obj.caratteristiche_visibili.all()
            .order_by('ordine', 'nome')
            .values('id', 'nome', 'sigla', 'colore', 'ordine')
        )

    def _validate_characteristics_count(self, tipo, count):
        if tipo in ('T1', 'T2') and count > 1:
            raise serializers.ValidationError({'caratteristiche_visibili': 'I Tier 1/2 possono avere al massimo 1 caratteristica.'})
        if tipo == 'T3' and count > 2:
            raise serializers.ValidationError({'caratteristiche_visibili': 'I Tier 3 possono avere al massimo 2 caratteristiche.'})
        if tipo == 'T4' and count > 4:
            raise serializers.ValidationError({'caratteristiche_visibili': 'I Tier 4 possono avere al massimo 4 caratteristiche.'})
    
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