"""
Serializer DRF per l'app pilotaggio.

Espone i cataloghi (sottosistemi, comandi, eventi, sequenze) e lo stato
runtime (sessione di volo, evento attivo, sottosistemi).
"""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    ComandoCriticoGlobale,
    ComandoNave,
    EventoAttivoSessione,
    EventoNave,
    IntensitaComando,
    PilotConsoleToken,
    PilotRuntimeConfig,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoAllertaPilot,
    StatoSottosistemaSessione,
    TentativoCodice,
)


class SottosistemaNaveSerializer(serializers.ModelSerializer):
    """
    Non espone a_vista né id QR grezzi: solo stato sintetico per l'interfaccia staff.
    """

    stato_qr = serializers.SerializerMethodField()
    qrcode_id = serializers.SerializerMethodField()

    class Meta:
        model = SottosistemaNave
        fields = [
            "id",
            "codice",
            "nome",
            "descrizione",
            "durata_ripristino_secondi",
            "attivo",
            "gruppo",
            "ordine_gruppo",
            "ordine",
            "tipo",
            "coeff_produzione",
            "coeff_consumo_energia",
            "coeff_consumo_carburante",
            "coeff_effetto_speciale",
            "rampa_livelli_per_tick",
            "capacita_storage",
            "coeff_ricarica_storage",
            "capacita_carburante",
            "effetti_guasto_json",
            "effetti_inversione_json",
            "effetti_espulsione_json",
            "probabilita_guasto_7",
            "probabilita_guasto_8",
            "probabilita_guasto_9",
            "guasto_percent_per_livello",
            "ripristino_percent_per_livello",
            "colori_per_livello",
            "supporta_inversione",
            "supporta_espulsione",
            "supporta_direzioni",
            "stato_qr",
            "qrcode_id",
        ]
        read_only_fields = ["id", "stato_qr", "qrcode_id"]

    def get_stato_qr(self, obj):
        """nessuno = no vista; incompleto = vista senza QR; pronto = QR collegato alla vista."""
        if not obj.a_vista_id:
            return "nessuno"
        try:
            qr = getattr(obj.a_vista, "qrcode", None)
        except Exception:
            qr = None
        return "pronto" if qr else "incompleto"

    def get_qrcode_id(self, obj):
        if not obj.a_vista_id:
            return None
        try:
            qr = getattr(obj.a_vista, "qrcode", None)
        except Exception:
            qr = None
        if qr is None:
            from personaggi.models import QrCode

            qr = QrCode.objects.filter(vista_id=obj.a_vista_id).first()
        return qr.id if qr else None


class SottosistemaNaveListSerializer(SottosistemaNaveSerializer):
    """Elenco leggero staff (liste tab) con stato/qrcode per minigioco."""

    class Meta:
        model = SottosistemaNave
        fields = [
            "id",
            "codice",
            "nome",
            "gruppo",
            "ordine_gruppo",
            "ordine",
            "tipo",
            "attivo",
            "stato_qr",
            "qrcode_id",
        ]
        read_only_fields = fields


class ComandoCriticoGlobaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComandoCriticoGlobale
        fields = ["id", "pattern", "nome", "attivo"]
        read_only_fields = ["id"]


class ComandoNaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComandoNave
        fields = ["id", "codice", "nome", "descrizione", "attivo"]
        read_only_fields = ["id"]


class IntensitaComandoSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntensitaComando
        fields = ["id", "valore", "nome", "descrizione", "attivo"]
        read_only_fields = ["id"]


class IntensitaComandoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntensitaComando
        fields = ["id", "valore", "nome", "attivo"]
        read_only_fields = fields


class EventoNaveListSerializer(serializers.ModelSerializer):
    sottosistema_codice = serializers.CharField(
        source="sottosistema.codice", read_only=True, default=None
    )

    class Meta:
        model = EventoNave
        fields = [
            "id",
            "nome",
            "attivo",
            "codice_soluzione_esatta",
            "durata_tick",
            "peso_random",
            "sottosistema",
            "sottosistema_codice",
        ]
        read_only_fields = fields


class ComandoCriticoGlobaleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComandoCriticoGlobale
        fields = ["id", "pattern", "nome", "attivo"]
        read_only_fields = fields


class StatoAllertaPilotListSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatoAllertaPilot
        fields = [
            "id",
            "livello",
            "nome",
            "colore",
            "frequenza_evento_min_sec",
            "frequenza_evento_max_sec",
            "tempo_risoluzione_secondi",
            "probabilita_evento_per_tick",
            "equivale_nave_abbattuta",
        ]
        read_only_fields = fields


class EventoNaveSerializer(serializers.ModelSerializer):
    sottosistema_codice = serializers.CharField(
        source="sottosistema.codice", read_only=True, default=None
    )

    class Meta:
        model = EventoNave
        fields = [
            "id",
            "nome",
            "descrizione",
            "codice_soluzione_esatta",
            "codici_soluzione_parziale",
            "codici_precipizio",
            "regole_json",
            "durata_base_secondi",
            "durata_tick",
            "peso_random",
            "sottosistema",
            "sottosistema_codice",
            "attivo",
        ]
        read_only_fields = ["id", "sottosistema_codice"]

    def validate_durata_tick(self, value):
        raw = str(value or "").strip()
        if not raw:
            raise serializers.ValidationError("Inserisci una durata in tick.")
        import re
        if not re.fullmatch(r"(\d+|\d+-\d+|-\d+|-)", raw):
            raise serializers.ValidationError('Formato valido: N, A-B, -N oppure -')
        if "-" in raw and raw not in ("-",) and raw.startswith("-"):
            if int(raw[1:]) <= 0:
                raise serializers.ValidationError("Nel formato -N, N deve essere > 0.")
        if "-" in raw and not raw.startswith("-"):
            a, b = raw.split("-", 1)
            if int(a) <= 0 or int(b) <= 0 or int(a) > int(b):
                raise serializers.ValidationError("Nel formato A-B servono A,B > 0 e A <= B.")
        if raw.isdigit() and int(raw) <= 0:
            raise serializers.ValidationError("La durata numerica deve essere > 0.")
        return raw


class SequenzaVoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = SequenzaVolo
        fields = ["id", "tipo", "nome", "codici", "attiva"]
        read_only_fields = ["id"]


class StatoAllertaPilotSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatoAllertaPilot
        fields = [
            "id",
            "livello",
            "nome",
            "colore",
            "frequenza_evento_min_sec",
            "frequenza_evento_max_sec",
            "tempo_risoluzione_secondi",
            "probabilita_evento_per_tick",
            "equivale_nave_abbattuta",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        lo = attrs.get("frequenza_evento_min_sec")
        hi = attrs.get("frequenza_evento_max_sec")
        if lo is not None and hi is not None and lo > hi:
            raise serializers.ValidationError(
                {
                    "frequenza_evento_max_sec": "Deve essere >= frequenza minima.",
                }
            )
        col = attrs.get("colore")
        if col is not None and str(col).strip() != "":
            c = str(col).strip()
            if len(c) != 7 or not c.startswith("#"):
                raise serializers.ValidationError(
                    {"colore": "Usa formato esadecimale #RRGGBB."}
                )
        return attrs

    def validate_livello(self, value):
        if value < 0 or value > 6:
            raise serializers.ValidationError("Livello consentito: 0..6.")
        return value


class StatoAllertaPilotPublicSerializer(serializers.ModelSerializer):
    """Sottinsieme per console pilota (colori e nomi)."""

    class Meta:
        model = StatoAllertaPilot
        fields = [
            "livello",
            "nome",
            "colore",
            "equivale_nave_abbattuta",
        ]


class StatoSottosistemaRuntimeSerializer(serializers.ModelSerializer):
    sottosistema_id = serializers.UUIDField(source="sottosistema.id", read_only=True)
    codice = serializers.CharField(source="sottosistema.codice", read_only=True)
    nome = serializers.CharField(source="sottosistema.nome", read_only=True)
    tipo = serializers.CharField(source="sottosistema.tipo", read_only=True)
    supporta_direzioni = serializers.BooleanField(
        source="sottosistema.supporta_direzioni", read_only=True
    )
    supporta_inversione = serializers.BooleanField(
        source="sottosistema.supporta_inversione", read_only=True
    )
    supporta_espulsione = serializers.BooleanField(
        source="sottosistema.supporta_espulsione", read_only=True
    )
    colore_livello_attuale = serializers.SerializerMethodField()
    durata_ripristino_secondi = serializers.IntegerField(
        source="sottosistema.durata_ripristino_secondi", read_only=True
    )
    ordine = serializers.IntegerField(source="sottosistema.ordine", read_only=True)
    ordine_gruppo = serializers.IntegerField(
        source="sottosistema.ordine_gruppo", read_only=True
    )

    class Meta:
        model = StatoSottosistemaSessione
        fields = [
            "id",
            "sottosistema_id",
            "codice",
            "nome",
            "tipo",
            "ordine",
            "ordine_gruppo",
            "supporta_direzioni",
            "supporta_inversione",
            "supporta_espulsione",
            "colore_livello_attuale",
            "online",
            "guasto_at",
            "recovery_at",
            "livello_target",
            "livello_attuale",
            "invertito",
            "espulso",
            "direzione",
            "durata_ripristino_secondi",
        ]

    def get_colore_livello_attuale(self, obj):
        livello = int(obj.livello_attuale or 0)
        colori = obj.sottosistema.colori_per_livello or {}
        return str(colori.get(str(livello)) or "")


class EventoAttivoSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="evento.nome", read_only=True)
    descrizione = serializers.CharField(source="evento.descrizione", read_only=True)

    class Meta:
        model = EventoAttivoSessione
        fields = [
            "id",
            "nome",
            "descrizione",
            "deadline_at",
            "ticks_rimanenti",
            "persiste_fino_st",
            "precipita_a_scadenza",
            "esito",
            "codice_inserito",
            "direzione_evento",
            "risolto_at",
        ]


class TentativoCodiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TentativoCodice
        fields = [
            "id",
            "codice",
            "esito",
            "defcon_pre",
            "defcon_post",
            "note",
            "created_at",
        ]


class SessioneVoloSerializer(serializers.ModelSerializer):
    pilota_nome = serializers.CharField(source="pilota.nome", read_only=True)
    partenza_nome = serializers.CharField(
        source="prefettura_partenza.nome", read_only=True, default=None
    )
    arrivo_nome = serializers.CharField(
        source="prefettura_arrivo.nome", read_only=True, default=None
    )

    class Meta:
        model = SessioneVolo
        fields = [
            "id",
            "stato",
            "defcon",
            "durata_pianificata_secondi",
            "started_at",
            "decollo_completato_at",
            "atterraggio_iniziato_at",
            "ended_at",
            "decollo_idx",
            "atterraggio_idx",
            "next_event_at",
            "pilota",
            "pilota_nome",
            "prefettura_partenza",
            "prefettura_arrivo",
            "partenza_nome",
            "arrivo_nome",
            "tick_secondi",
            "carburante_massimo",
            "carburante_attuale",
            "storage_energia_massimo",
            "storage_energia_attuale",
            "coeff_rigenerazione_carburante_riposo",
            "produzione_ultimo_tick",
            "consumo_ultimo_tick",
            "distanza_target",
            "distanza_percorsa",
            "crash_reason",
        ]
        read_only_fields = fields


class PilotConsoleTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PilotConsoleToken
        fields = ["id", "token", "pilota", "created_at", "revocato_at"]
        read_only_fields = fields


class PilotRuntimeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PilotRuntimeConfig
        fields = [
            "tick_enabled",
            "tick_interval_secondi",
            "tick_last_heartbeat",
            "login_required_console",
            "alarm_audio_enabled",
            "updated_at",
        ]
        read_only_fields = ["tick_last_heartbeat", "updated_at"]
