"""Admin Django — carte collezionabili «Sette Elegie»."""
from django.contrib import admin

from personaggi.models import (
    BustinaCarte,
    CartaCollezionabile,
    CartaPosseduta,
    CartaReliquiarioStatistica,
    ComboReliquiario,
    ComboReliquiarioStatistica,
    ConfigurazioneCarteCollezionabili,
    DuelloCarte,
    EspansioneCarte,
    KeywordCarta,
    MazzoDuello,
    OffertaScambioCarte,
    ReliquiarioSlot,
)


class CartaReliquiarioStatisticaInline(admin.TabularInline):
    model = CartaReliquiarioStatistica
    extra = 0
    autocomplete_fields = ["statistica"]
    fields = ("statistica", "valore", "tipo_modificatore")


class ComboReliquiarioStatisticaInline(admin.TabularInline):
    model = ComboReliquiarioStatistica
    extra = 0
    autocomplete_fields = ["statistica"]
    fields = ("statistica", "valore", "tipo_modificatore")


@admin.register(KeywordCarta)
class KeywordCartaAdmin(admin.ModelAdmin):
    list_display = ("codice", "nome", "campagna", "priorita", "attiva", "updated_at")
    list_filter = ("attiva", "campagna")
    search_fields = ("codice", "nome", "testo_regola")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna"]


@admin.register(EspansioneCarte)
class EspansioneCarteAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "campagna", "attiva", "ordine", "updated_at")
    list_filter = ("attiva", "campagna")
    search_fields = ("nome", "slug")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna"]


@admin.register(CartaCollezionabile)
class CartaCollezionabileAdmin(admin.ModelAdmin):
    list_display = ("codice", "nome", "tipo", "energia", "rarita", "campagna", "attiva")
    list_filter = ("tipo", "energia", "rarita", "attiva", "campagna", "espansione")
    search_fields = ("codice", "nome", "testo_gioco", "testo_reliquiario")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna", "espansione"]
    inlines = [CartaReliquiarioStatisticaInline]
    fieldsets = (
        (None, {
            "fields": (
                "campagna", "espansione", "codice", "nome", "attiva",
                "tipo", "energia", "rarita", "costo_gioco",
                "attacco", "salute", "iniziativa",
            ),
        }),
        ("Testi", {
            "fields": ("testo_gioco", "testo_lore", "testo_reliquiario", "immagine"),
        }),
        ("Collezione", {
            "fields": ("set_collezione", "bonus_equip"),
            "classes": ("collapse",),
        }),
        ("Sync", {
            "fields": ("id", "sync_id", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(BustinaCarte)
class BustinaCarteAdmin(admin.ModelAdmin):
    list_display = ("nome", "campagna", "costo_crediti", "carte_per_bustina", "attiva")
    list_filter = ("attiva", "campagna")
    search_fields = ("nome",)
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna", "espansione"]


@admin.register(ConfigurazioneCarteCollezionabili)
class ConfigurazioneCarteCollezionabiliAdmin(admin.ModelAdmin):
    list_display = ("campagna", "accesso_modo", "updated_at")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna"]


@admin.register(ComboReliquiario)
class ComboReliquiarioAdmin(admin.ModelAdmin):
    list_display = ("nome", "campagna", "ordine", "attiva", "colore")
    list_filter = ("attiva", "campagna")
    search_fields = ("nome", "codice", "descrizione", "testo")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna"]
    inlines = [ComboReliquiarioStatisticaInline]


@admin.register(CartaPosseduta)
class CartaPossedutaAdmin(admin.ModelAdmin):
    list_display = ("personaggio", "carta", "created_at")
    search_fields = ("personaggio__nome", "carta__nome", "carta__codice")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["personaggio", "carta"]


@admin.register(ReliquiarioSlot)
class ReliquiarioSlotAdmin(admin.ModelAdmin):
    list_display = ("personaggio", "slot_index", "carta_posseduta")
    list_filter = ("slot_index",)
    search_fields = ("personaggio__nome",)
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["personaggio", "carta_posseduta"]


@admin.register(MazzoDuello)
class MazzoDuelloAdmin(admin.ModelAdmin):
    list_display = ("nome", "personaggio", "is_default", "updated_at")
    search_fields = ("nome", "personaggio__nome")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["personaggio"]


@admin.register(DuelloCarte)
class DuelloCarteAdmin(admin.ModelAdmin):
    list_display = ("sfidante", "sfidato", "stato", "campagna", "updated_at")
    list_filter = ("stato", "campagna", "modalita_partita")
    search_fields = ("sfidante__nome", "sfidato__nome", "codice_invito")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at")
    autocomplete_fields = ["campagna", "sfidante", "sfidato", "vincitore", "qr_code"]


@admin.register(OffertaScambioCarte)
class OffertaScambioCarteAdmin(admin.ModelAdmin):
    list_display = (
        "offerente",
        "carta_offerta",
        "richiesta_carta",
        "richiesta_crediti",
        "stato",
        "accettante",
        "updated_at",
    )
    list_filter = ("stato", "campagna")
    search_fields = ("offerente__nome", "accettante__nome", "messaggio")
    readonly_fields = ("id", "sync_id", "created_at", "updated_at", "accettata_at")
    autocomplete_fields = [
        "campagna",
        "offerente",
        "carta_offerta",
        "richiesta_carta",
        "accettante",
        "carta_contropartita",
    ]
    fieldsets = (
        (None, {
            "fields": (
                "campagna", "stato", "offerente", "accettante", "messaggio",
            ),
        }),
        ("Scambio", {
            "fields": (
                "carta_offerta", "richiesta_carta", "richiesta_crediti",
                "carta_contropartita", "crediti_trasferiti", "commissione_crediti",
            ),
        }),
        ("Sync", {
            "fields": ("id", "sync_id", "created_at", "updated_at", "accettata_at"),
            "classes": ("collapse",),
        }),
    )
