from django.contrib import admin

from .models import (
    ComandoCriticoGlobale,
    ComandoNave,
    EventoAttivoSessione,
    EventoNave,
    IntensitaComando,
    PilotConsoleLoginTicket,
    PilotConsoleToken,
    PilotRuntimeConfig,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoAllertaPilot,
    StatoSottosistemaNave,
    StatoSottosistemaSessione,
    TentativoCodice,
)


@admin.register(StatoAllertaPilot)
class StatoAllertaPilotAdmin(admin.ModelAdmin):
    list_display = (
        "livello",
        "nome",
        "colore",
        "frequenza_evento_min_sec",
        "frequenza_evento_max_sec",
        "tempo_risoluzione_secondi",
        "probabilita_evento_per_tick",
        "equivale_nave_abbattuta",
    )
    list_editable = ("equivale_nave_abbattuta",)
    ordering = ("livello",)


@admin.register(SottosistemaNave)
class SottosistemaNaveAdmin(admin.ModelAdmin):
    """Il collegamento QR/vista si gestisce dall'app staff (Scansiona QR), non da qui."""

    list_display = (
        "codice",
        "nome",
        "gruppo",
        "ordine_gruppo",
        "ordine",
        "tipo",
        "attivo",
        "durata_ripristino_secondi",
    )
    search_fields = ("codice", "nome")
    # a_vista / QR: solo API staff (associa-qr), non form admin
    fields = (
        "codice",
        "nome",
        "gruppo",
        "ordine_gruppo",
        "ordine",
        "tipo",
        "descrizione",
        "durata_ripristino_secondi",
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
        "attivo",
    )


@admin.register(ComandoCriticoGlobale)
class ComandoCriticoGlobaleAdmin(admin.ModelAdmin):
    list_display = ("pattern", "nome", "attivo")
    list_filter = ("attivo",)
    search_fields = ("pattern", "nome")


@admin.register(ComandoNave)
class ComandoNaveAdmin(admin.ModelAdmin):
    list_display = ("codice", "nome", "attivo")
    search_fields = ("codice", "nome")


@admin.register(IntensitaComando)
class IntensitaComandoAdmin(admin.ModelAdmin):
    list_display = ("valore", "nome", "attivo")
    search_fields = ("nome",)


@admin.register(PilotConsoleLoginTicket)
class PilotConsoleLoginTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "pilota", "claimed_at", "expires_at", "token_issued_at")
    search_fields = ("codice", "pilota__nome")


@admin.register(EventoNave)
class EventoNaveAdmin(admin.ModelAdmin):
    list_display = ("nome", "durata_tick", "scadenza_critica", "peso_random", "attivo")
    search_fields = ("nome", "codice_soluzione_esatta")
    list_filter = ("attivo", "sottosistema")


@admin.register(SequenzaVolo)
class SequenzaVoloAdmin(admin.ModelAdmin):
    list_display = ("tipo", "nome", "attiva", "created_at")
    list_filter = ("tipo", "attiva")


@admin.register(SessioneVolo)
class SessioneVoloAdmin(admin.ModelAdmin):
    list_display = ("id", "pilota", "stato", "defcon", "started_at", "ended_at")
    list_filter = ("stato",)
    search_fields = ("pilota__nome",)


@admin.register(EventoAttivoSessione)
class EventoAttivoSessioneAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sessione",
        "evento",
        "esito",
        "ticks_rimanenti",
        "persiste_fino_st",
        "precipita_a_scadenza",
        "deadline_at",
    )
    list_filter = ("esito",)


@admin.register(StatoSottosistemaSessione)
class StatoSottosistemaSessioneAdmin(admin.ModelAdmin):
    list_display = ("sessione", "sottosistema", "online", "guasto_at", "recovery_at")
    list_filter = ("online",)


@admin.register(StatoSottosistemaNave)
class StatoSottosistemaNaveAdmin(admin.ModelAdmin):
    list_display = ("sottosistema", "online", "espulso", "livello_attuale", "livello_target", "updated_at")
    list_filter = ("online", "espulso")


@admin.register(TentativoCodice)
class TentativoCodiceAdmin(admin.ModelAdmin):
    list_display = ("created_at", "sessione", "codice", "esito", "defcon_pre", "defcon_post")
    list_filter = ("esito",)
    search_fields = ("codice",)


@admin.register(PilotConsoleToken)
class PilotConsoleTokenAdmin(admin.ModelAdmin):
    list_display = ("pilota", "created_at", "last_seen_at", "revocato_at")
    search_fields = ("pilota__nome",)


@admin.register(PilotRuntimeConfig)
class PilotRuntimeConfigAdmin(admin.ModelAdmin):
    list_display = (
        "login_required_console",
        "alarm_audio_enabled",
        "tick_enabled",
        "tick_interval_secondi",
        "tick_last_heartbeat",
        "updated_at",
    )
