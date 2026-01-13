from django.contrib import admin
from .models import (
    Evento, GiornoEvento, Quest, QuestMostro, QuestVista,
    MostroTemplate, AttaccoTemplate, PngAssegnato, 
    StaffOffGame, QuestFase, QuestTask,
    PaginaRegolamento
)
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin

# --- INLINES (Per gestire sottocategorie dentro le pagine principali) ---

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
    fields = ('nome', 'descrizione', 'is_opzionale', 'xp_reward')

class QuestFaseInline(admin.StackedInline):
    model = QuestFase
    extra = 0
    show_change_link = True

class QuestMostroInline(admin.TabularInline):
    model = QuestMostro
    extra = 1
    autocomplete_fields = ['mostro_template']

# --- ADMIN CLASSES ---

@admin.register(PaginaRegolamento)
class PaginaRegolamentoAdmin(SModelAdmin):
    list_display = ('titolo', 'slug', 'parent', 'ordine', 'public')
    list_editable = ('ordine', 'public') # Permette modifica rapida dalla lista
    list_filter = ('public', 'parent')
    search_fields = ('titolo', 'contenuto')
    prepopulated_fields = {'slug': ('titolo',)} # Compila lo slug mentre scrivi il titolo
    ordering = ('parent', 'ordine', 'titolo')
    fieldsets = (
        ('Intestazione', {
            'fields': ('titolo', 'slug', 'parent', 'ordine', 'public', 'immagine')
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
    filter_horizontal = ('staff_assegnato', 'partecipanti') # Widget migliore per i ManyToMany

@admin.register(GiornoEvento)
class GiornoEventoAdmin(SModelAdmin):
    list_display = ('evento', 'data_giorno', 'sinossi_breve')
    list_filter = ('evento',)

@admin.register(Quest)
class QuestAdmin(SModelAdmin):
    list_display = ('titolo', 'giorno', 'stato', 'staff_responsabile')
    list_filter = ('stato', 'giorno__evento')
    search_fields = ('titolo', 'descrizione')
    inlines = [QuestFaseInline, QuestMostroInline]
    autocomplete_fields = ['staff_responsabile']

@admin.register(QuestFase)
class QuestFaseAdmin(SModelAdmin):
    list_display = ('titolo', 'quest', 'ordine')
    list_filter = ('quest',)
    inlines = [QuestTaskInline]

@admin.register(PngAssegnato)
class PngAssegnatoAdmin(admin.ModelAdmin):
    list_display = ('nome_png', 'giocatore', 'quest', 'ruolo')
    search_fields = ('nome_png', 'giocatore__username')
    list_filter = ('ruolo',)

@admin.register(StaffOffGame)
class StaffOffGameAdmin(admin.ModelAdmin):
    list_display = ('staffer', 'ruolo', 'quest')
    list_filter = ('ruolo',)

@admin.register(QuestVista)
class QuestVistaAdmin(admin.ModelAdmin):
    list_display = ('nome_vista', 'data_creazione')

# QuestTask è gestito inline dentro QuestFase, ma se vuoi vederli tutti:
@admin.register(QuestTask)
class QuestTaskAdmin(admin.ModelAdmin):
    list_display = ('nome', 'fase', 'is_opzionale', 'is_completato')
    list_filter = ('is_completato', 'fase__quest')