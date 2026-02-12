from django.contrib import admin
from .models import (
    Evento, GiornoEvento, Quest, QuestMostro, QuestVista,
    MostroTemplate, AttaccoTemplate, PngAssegnato, 
    StaffOffGame, QuestFase, QuestTask,
    PaginaRegolamento, WikiImmagine,
    ConfigurazioneSito, LinkSocial
)
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin

# --- INLINES ---

class AttaccoTemplateInline(admin.TabularInline):
    model = AttaccoTemplate
    extra = 1

class GiornoEventoInline(admin.StackedInline):
    model = GiornoEvento
    extra = 0
    show_change_link = True

class QuestTaskInline(admin.TabularInline):
    model = QuestTask
    extra = 1
    # CAMPI CORRETTI: 'nome', 'descrizione', 'is_opzionale' non esistono nel model QuestTask.
    # Usiamo i campi esistenti: ruolo, staffer, istruzioni.
    fields = ('ruolo', 'staffer', 'istruzioni')

class QuestFaseInline(admin.StackedInline):
    model = QuestFase
    extra = 0
    show_change_link = True

class QuestMostroInline(admin.TabularInline):
    model = QuestMostro
    extra = 1
    # CORREZIONE: Nel model il campo si chiama 'template', non 'mostro_template'
    autocomplete_fields = ['template']

# --- ADMIN CLASSES ---

@admin.register(PaginaRegolamento)
class PaginaRegolamentoAdmin(SModelAdmin):
    list_display = ('titolo', 'slug', 'parent', 'ordine', 'public')
    list_editable = ('ordine', 'public')
    list_filter = ('public', 'parent')
    search_fields = ('titolo', 'contenuto')
    prepopulated_fields = {'slug': ('titolo',)}
    ordering = ('parent', 'ordine', 'titolo')
    fieldsets = (
        ('Intestazione', {
            'fields': ('titolo', 'slug', 'parent', 'ordine', 'public', 'immagine', 'visibile_solo_staff'),
        }),
        ('Contenuto', {
            'fields': ('contenuto',),
            'description': 'Usa i placeholder {{WIDGET_...}} per inserire elementi dinamici.'
        }),
    )

@admin.register(MostroTemplate)
class MostroTemplateAdmin(SModelAdmin):
    list_display = ('nome', 'punti_vita_base', 'armatura_base', 'guscio_base')
    search_fields = ('nome', 'note_generali')
    inlines = [AttaccoTemplateInline]

@admin.register(Evento)
class EventoAdmin(SModelAdmin):
    list_display = ('titolo', 'data_inizio', 'data_fine', 'luogo')
    list_filter = ('data_inizio',)
    search_fields = ('titolo',)
    inlines = [GiornoEventoInline]
    filter_horizontal = ('staff_assegnato', 'partecipanti')

@admin.register(GiornoEvento)
class GiornoEventoAdmin(SModelAdmin):
    # CORREZIONE: 'data_giorno' non esiste. Uso 'data_ora_inizio'.
    list_display = ('evento', 'data_ora_inizio', 'sinossi_breve')
    list_filter = ('evento',)

@admin.register(Quest)
class QuestAdmin(SModelAdmin):
    # CORREZIONE: Rimosso 'stato' e 'staff_responsabile' (non esistono nel model).
    list_display = ('titolo', 'giorno', 'orario_indicativo')
    # Rimosso 'stato' dai filtri.
    list_filter = ('giorno__evento',)
    search_fields = ('titolo', 'descrizione_ampia')
    inlines = [QuestFaseInline, QuestMostroInline]
    # Rimosso autocomplete_fields perché 'staff_responsabile' non c'è.

@admin.register(QuestFase)
class QuestFaseAdmin(SModelAdmin):
    list_display = ('titolo', 'quest', 'ordine')
    list_filter = ('quest',)
    inlines = [QuestTaskInline]

@admin.register(PngAssegnato)
class PngAssegnatoAdmin(admin.ModelAdmin):
    # CORREZIONE: 'nome_png', 'giocatore', 'ruolo' non esistono in PngAssegnato.
    # Uso 'personaggio' e 'staffer' che sono i campi reali.
    list_display = ('personaggio', 'staffer', 'quest', 'ordine_uscita')
    search_fields = ('personaggio__nome', 'staffer__username')
    # Rimosso list_filter su 'ruolo' che non c'è.

@admin.register(StaffOffGame)
class StaffOffGameAdmin(admin.ModelAdmin):
    # CORREZIONE: 'ruolo' non esiste, esiste 'compito'.
    list_display = ('staffer', 'compito', 'quest')
    list_filter = ('compito',) # Attenzione: compito è un TextField, filtrare potrebbe essere scomodo se i testi sono lunghi/diversi.

@admin.register(QuestVista)
class QuestVistaAdmin(admin.ModelAdmin):
    # CORREZIONE: 'nome_vista' e 'data_creazione' non esistono.
    list_display = ('quest', 'tipo', 'manifesto', 'inventario')

@admin.register(QuestTask)
class QuestTaskAdmin(admin.ModelAdmin):
    # CORREZIONE: 'nome', 'is_opzionale', 'is_completato' non esistono.
    list_display = ('ruolo', 'fase', 'staffer')
    list_filter = ('ruolo', 'fase__quest')

@admin.register(WikiImmagine)
class WikiImmagineAdmin(admin.ModelAdmin):
    list_display = ('titolo', 'immagine_preview', 'allineamento', 'larghezza_max', 'creatore', 'data_creazione')
    list_filter = ('allineamento', 'data_creazione', 'creatore')
    search_fields = ('titolo', 'descrizione')
    readonly_fields = ('data_creazione', 'data_modifica', 'immagine_preview')
    ordering = ('-data_creazione',)
    
    fieldsets = (
        ('Informazioni Generali', {
            'fields': ('titolo', 'descrizione', 'creatore')
        }),
        ('Immagine', {
            'fields': ('immagine', 'immagine_preview')
        }),
        ('Impostazioni Visualizzazione', {
            'fields': ('larghezza_max', 'allineamento')
        }),
        ('Metadati', {
            'fields': ('data_creazione', 'data_modifica'),
            'classes': ('collapse',)
        }),
    )
    
    def immagine_preview(self, obj):
        if obj.immagine:
            return f'<img src="{obj.immagine.url}" style="max-width: 200px; max-height: 150px;" />'
        return "Nessuna immagine"
    immagine_preview.short_description = 'Anteprima'
    immagine_preview.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        if not change:  # Solo quando viene creato
            obj.creatore = request.user
        super().save_model(request, obj, form, change)


@admin.register(ConfigurazioneSito)
class ConfigurazioneSitoAdmin(admin.ModelAdmin):
    """
    Admin per la configurazione del sito (Singleton).
    """
    list_display = ('nome_associazione', 'email', 'citta', 'anno_fondazione', 'ultima_modifica')
    readonly_fields = ('ultima_modifica',)
    
    fieldsets = (
        ('Informazioni Associazione', {
            'fields': ('nome_associazione', 'descrizione_breve', 'anno_fondazione')
        }),
        ('Sede', {
            'fields': ('indirizzo', 'cap', 'citta', 'provincia', 'nazione')
        }),
        ('Contatti', {
            'fields': ('email', 'pec', 'telefono')
        }),
        ('Metadata', {
            'fields': ('ultima_modifica',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Impedisce la creazione di più di un record (Singleton)
        return not ConfigurazioneSito.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Impedisce la cancellazione della configurazione
        return False


@admin.register(LinkSocial)
class LinkSocialAdmin(admin.ModelAdmin):
    """
    Admin per i link social.
    """
    list_display = ('tipo', 'nome_visualizzato', 'url', 'ordine', 'attivo')
    list_filter = ('tipo', 'attivo')
    search_fields = ('nome_visualizzato', 'url', 'descrizione')
    list_editable = ('ordine', 'attivo')
    ordering = ('ordine', 'tipo')
    
    fieldsets = (
        ('Informazioni Link', {
            'fields': ('tipo', 'nome_visualizzato', 'url', 'descrizione')
        }),
        ('Visualizzazione', {
            'fields': ('ordine', 'attivo')
        }),
    )