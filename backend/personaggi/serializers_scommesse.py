from rest_framework import serializers

from personaggi.scommesse_logic import calendario_ancora_visibile, calendario_visibile_fino, risultati_pubblicati
from personaggi.scommesse_risultati import (
    formatta_risultato,
    meta_tipo_risultato,
    pareggio_consentito,
)
from personaggi.scommesse_models import (
    CalendarioScommesse,
    CodiceScommessa,
    ConfigurazioneScommesse,
    IncontroScommesse,
    PuntataScommessa,
    SelezionePuntata,
    SportScommesse,
    SquadraScommesse,
)


class SportScommesseSerializer(serializers.ModelSerializer):
    num_squadre = serializers.SerializerMethodField()
    tipo_risultato_label = serializers.SerializerMethodField()
    pareggio_consentito = serializers.SerializerMethodField()

    class Meta:
        model = SportScommesse
        fields = [
            "id", "sync_id", "nome", "descrizione", "campagna", "attivo",
            "tipo_risultato", "tipo_risultato_label", "pareggio_consentito",
            "created_at", "updated_at", "num_squadre",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at"]

    def get_num_squadre(self, obj):
        return obj.squadre.filter(attiva=True).count()

    def get_tipo_risultato_label(self, obj):
        return meta_tipo_risultato(obj.tipo_risultato).label

    def get_pareggio_consentito(self, obj):
        return pareggio_consentito(obj.tipo_risultato)


class SquadraScommesseSerializer(serializers.ModelSerializer):
    sport_nome = serializers.CharField(source="sport.nome", read_only=True)

    class Meta:
        model = SquadraScommesse
        fields = [
            "id", "sync_id", "sport", "sport_nome", "nome", "potenza", "attiva",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at"]


class IncontroScommesseSerializer(serializers.ModelSerializer):
    squadra_casa_nome = serializers.CharField(source="squadra_casa.nome", read_only=True)
    squadra_trasferta_nome = serializers.CharField(source="squadra_trasferta.nome", read_only=True)
    esito = serializers.SerializerMethodField()
    gol_casa = serializers.SerializerMethodField()
    gol_trasferta = serializers.SerializerMethodField()
    risultato_formattato = serializers.SerializerMethodField()
    pareggio_consentito = serializers.SerializerMethodField()
    tipo_risultato = serializers.SerializerMethodField()

    class Meta:
        model = IncontroScommesse
        fields = [
            "id", "sync_id", "ordine",
            "squadra_casa", "squadra_casa_nome",
            "squadra_trasferta", "squadra_trasferta_nome",
            "quota_casa", "quota_pareggio", "quota_trasferta",
            "esito", "gol_casa", "gol_trasferta", "risultato_formattato",
            "tipo_risultato", "pareggio_consentito",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def _tipo_risultato(self, obj):
        cal = self.context.get("calendario") or obj.calendario
        sport = getattr(cal, "sport", None)
        if sport is not None:
            return sport.tipo_risultato
        return None

    def _risultati_visibili(self, obj):
        cal = self.context.get("calendario") or obj.calendario
        if self.context.get("staff_view"):
            return True
        return risultati_pubblicati(cal.data_risoluzione)

    def get_esito(self, obj):
        if self._risultati_visibili(obj):
            return obj.esito
        return None

    def get_gol_casa(self, obj):
        return obj.gol_casa if self._risultati_visibili(obj) else None

    def get_gol_trasferta(self, obj):
        return obj.gol_trasferta if self._risultati_visibili(obj) else None

    def get_risultato_formattato(self, obj):
        if not self._risultati_visibili(obj):
            return None
        return formatta_risultato(self._tipo_risultato(obj), obj.gol_casa, obj.gol_trasferta)

    def get_tipo_risultato(self, obj):
        return self._tipo_risultato(obj)

    def get_pareggio_consentito(self, obj):
        return pareggio_consentito(self._tipo_risultato(obj))


class IncontroScommesseStaffSerializer(serializers.ModelSerializer):
    squadra_casa_nome = serializers.CharField(source="squadra_casa.nome", read_only=True)
    squadra_trasferta_nome = serializers.CharField(source="squadra_trasferta.nome", read_only=True)
    risultato_formattato = serializers.SerializerMethodField()
    tipo_risultato = serializers.SerializerMethodField()
    pareggio_consentito = serializers.SerializerMethodField()

    class Meta:
        model = IncontroScommesse
        fields = [
            "id", "sync_id", "ordine",
            "squadra_casa", "squadra_casa_nome",
            "squadra_trasferta", "squadra_trasferta_nome",
            "potenza_casa_effettiva", "potenza_trasferta_effettiva",
            "quota_casa", "quota_pareggio", "quota_trasferta",
            "esito", "gol_casa", "gol_trasferta", "risultato_formattato",
            "tipo_risultato", "pareggio_consentito",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at"]

    def _tipo_risultato(self, obj):
        cal = self.context.get("calendario")
        if cal is not None:
            return cal.sport.tipo_risultato
        return obj.calendario.sport.tipo_risultato

    def get_risultato_formattato(self, obj):
        return formatta_risultato(self._tipo_risultato(obj), obj.gol_casa, obj.gol_trasferta)

    def get_tipo_risultato(self, obj):
        return self._tipo_risultato(obj)

    def get_pareggio_consentito(self, obj):
        return pareggio_consentito(self._tipo_risultato(obj))


class CalendarioScommesseListSerializer(serializers.ModelSerializer):
    sport_nome = serializers.CharField(source="sport.nome", read_only=True)
    sport_tipo_risultato = serializers.CharField(source="sport.tipo_risultato", read_only=True)
    sport_tipo_risultato_label = serializers.SerializerMethodField()
    sport_pareggio_consentito = serializers.SerializerMethodField()
    num_incontri = serializers.SerializerMethodField()
    risultati_visibili = serializers.SerializerMethodField()
    visibile_fino = serializers.SerializerMethodField()
    scommesse_aperte = serializers.SerializerMethodField()

    class Meta:
        model = CalendarioScommesse
        fields = [
            "id", "sync_id", "sport", "sport_nome",
            "sport_tipo_risultato", "sport_tipo_risultato_label", "sport_pareggio_consentito",
            "titolo",
            "data_apertura", "data_risoluzione", "importo_max_senza_codice",
            "attivo", "liquidato", "num_incontri",
            "risultati_visibili", "visibile_fino", "scommesse_aperte",
            "created_at", "updated_at",
        ]

    def get_sport_tipo_risultato_label(self, obj):
        return meta_tipo_risultato(obj.sport.tipo_risultato).label

    def get_sport_pareggio_consentito(self, obj):
        return pareggio_consentito(obj.sport.tipo_risultato)

    def get_num_incontri(self, obj):
        return obj.incontri.count()

    def get_risultati_visibili(self, obj):
        return risultati_pubblicati(obj.data_risoluzione)

    def get_visibile_fino(self, obj):
        limite = calendario_visibile_fino(obj.data_risoluzione, campagna=getattr(obj.sport, "campagna_id", None))
        return limite.isoformat() if limite else None

    def get_scommesse_aperte(self, obj):
        from django.utils import timezone
        if not obj.attivo or not calendario_ancora_visibile(obj):
            return False
        if risultati_pubblicati(obj.data_risoluzione):
            return False
        return timezone.now() >= obj.data_apertura


class CalendarioScommesseDetailSerializer(CalendarioScommesseListSerializer):
    incontri = serializers.SerializerMethodField()

    class Meta(CalendarioScommesseListSerializer.Meta):
        fields = CalendarioScommesseListSerializer.Meta.fields + ["incontri"]

    def get_incontri(self, obj):
        qs = obj.incontri.select_related("squadra_casa", "squadra_trasferta").order_by("ordine")
        staff = self.context.get("staff_view", False)
        if staff:
            return IncontroScommesseStaffSerializer(
                qs, many=True, context={**self.context, "calendario": obj},
            ).data
        return IncontroScommesseSerializer(
            qs, many=True, context={**self.context, "calendario": obj, "staff_view": staff}
        ).data


class CalendarioScommesseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarioScommesse
        fields = [
            "id", "sport", "titolo", "data_apertura", "data_risoluzione",
            "importo_max_senza_codice", "attivo",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        from personaggi.scommesse_config import get_config_scommesse
        sport = validated_data["sport"]
        cfg = get_config_scommesse(sport.campagna_id)
        if validated_data.get("importo_max_senza_codice") in (None, ""):
            validated_data["importo_max_senza_codice"] = cfg.importo_max_senza_codice_default
        return super().create(validated_data)


class ConfigurazioneScommesseSerializer(serializers.ModelSerializer):
    campagna_nome = serializers.CharField(source="campagna.nome", read_only=True)

    class Meta:
        model = ConfigurazioneScommesse
        fields = [
            "id", "sync_id", "campagna", "campagna_nome", "attiva",
            "importo_max_senza_codice_default", "scadenza_calendario_ore",
            "commissione_allibratore_pct", "margine_book_default", "margine_book_min",
            "riduzione_margine_per_punto_all", "variabilita_potenza_pct",
            "max_selezioni_combinata", "potenza_delta_vittoria", "potenza_delta_sconfitta",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at"]


class CodiceScommessaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodiceScommessa
        fields = ["id", "sync_id", "codice", "usato", "usato_at", "created_at", "updated_at"]
        read_only_fields = fields


class SelezionePuntataSerializer(serializers.ModelSerializer):
    incontro_label = serializers.SerializerMethodField()
    esito_reale = serializers.SerializerMethodField()

    class Meta:
        model = SelezionePuntata
        fields = ["id", "incontro", "incontro_label", "esito_scelto", "esito_reale"]

    def get_incontro_label(self, obj):
        return str(obj.incontro)

    def get_esito_reale(self, obj):
        cal = obj.incontro.calendario
        if risultati_pubblicati(cal.data_risoluzione) or self.context.get("staff_view"):
            return obj.incontro.esito
        return None


class PuntataScommessaSerializer(serializers.ModelSerializer):
    selezioni = SelezionePuntataSerializer(many=True, read_only=True)
    calendario_titolo = serializers.SerializerMethodField()

    class Meta:
        model = PuntataScommessa
        fields = [
            "id", "sync_id", "calendario", "calendario_titolo", "importo", "tipo",
            "quota_totale", "stato", "vincita", "codice", "selezioni",
            "created_at", "liquidata_at",
        ]

    def get_calendario_titolo(self, obj):
        return obj.calendario.titolo or obj.calendario.sport.nome


class PiazzamentoPuntataSerializer(serializers.Serializer):
    calendario_id = serializers.UUIDField()
    importo = serializers.DecimalField(max_digits=12, decimal_places=2)
    codice = serializers.CharField(required=False, allow_blank=True, max_length=5)
    selezioni = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=10,
    )
