from django.contrib import admin
from .models import (
    Evento, GiornoEvento, Quest, 
    MostroTemplate, AttaccoTemplate, 
    QuestMostro, PngAssegnato, QuestVista
)

# --- INLINES PER TEMPLATE ---

class AttaccoTemplateInline(admin.TabularInline):
    model = AttaccoTemplate
    extra = 1
    fields = ('ordine', 'nome_attacco', 'descrizione_danno')

@admin.register(MostroTemplate)
class MostroTemplateAdmin(admin.ModelAdmin):
    list_display = ('nome', 'punti_vita_base', 'armatura_base', 'guscio_base')
    search_fields = ('nome',)
    inlines = [AttaccoTemplateInline]

# --- INLINES PER EVENTI E QUEST ---

class GiornoEventoInline(admin.StackedInline):
    model = GiornoEvento
    extra = 1
    show_change_link = True # Permette di andare alla modifica del giorno

class QuestMostroInline(admin.TabularInline):
    model = QuestMostro
    extra = 1
    # Mostriamo i campi statistici così il Master può ritoccarli dopo la copia dal template
    fields = ('template', 'staffer', 'punti_vita', 'armatura', 'guscio', 'note_per_staffer')
    autocomplete_fields = ['template', 'staffer']

class PngAssegnatoInline(admin.TabularInline):
    model = PngAssegnato
    extra = 1
    autocomplete_fields = ['personaggio', 'staffer']

class QuestVistaInline(admin.TabularInline):
    model = QuestVista
    extra = 1
    fields = ('tipo', 'manifesto', 'inventario', 'qr_code')
    autocomplete_fields = ['manifesto', 'inventario', 'qr_code']

# --- ADMIN MODELS PRINCIPALI ---

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('titolo', 'data_inizio', 'data_fine', 'luogo')
    filter_horizontal = ('partecipanti', 'staff_assegnato')
    search_fields = ('titolo', 'luogo')
    inlines = [GiornoEventoInline]

@admin.register(GiornoEvento)
class GiornoEventoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'data_ora_inizio', 'data_ora_fine')
    list_filter = ('evento',)

@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ('orario_indicativo', 'titolo', 'giorno')
    list_filter = ('giorno__evento', 'giorno')
    search_fields = ('titolo', 'descrizione_ampia')
    # Qui il Master gestisce tutto il "Plot" della singola scena
    inlines = [QuestMostroInline, PngAssegnatoInline, QuestVistaInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('giorno__evento')