from django.contrib import admin

from django import forms

from django.forms import Media
# from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django.contrib.admin import ModelAdmin as SModelAdmin # temporaneo senza summernote
# from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin
from django.contrib.admin import TabularInline as SInlineModelAdmin # temporaneo senza summernote

from django.utils.html import format_html
from .models import CreditoMovimento, OggettoStatisticaBase, Personaggio, PersonaggioLog, QrCode, Oggetto, Manifesto, OggettoStatistica, Attivata, AttivataStatisticaBase, TipologiaPersonaggio
from .models import Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica, PuntiCaratteristicaMovimento 

from .models import Tabella, Punteggio, Tier, Abilita, Spell, Mattone, Statistica
from .models import abilita_tier, abilita_punteggio, abilita_requisito, abilita_sbloccata, spell_mattone, abilita_prerequisito, AbilitaStatistica

from django_icon_picker.widgets import IconPicker

# ----------- CLASSI ASTRATTE -------------

IconPicker.media = property(lambda self: Media(
    css={'all': ('django_icon_picker/css/icon_picker.css',)}
    # Niente 'js' qui!
))

class A_Admin(SModelAdmin):
    actions_on_top = True
    save_on_top = True

    class Meta:
        abstract = True

		
class A_Multi_Inline (admin.TabularInline):
	extra = 1
	
	class Meta:
		abstract = True

# class MuteIconPickerWidget(IconPicker):
#     @property
#     def media(self):
#         # PATCH: Silenzia solo il JS, ma carica il CSS.
#         # Il JS verrà caricato (una sola volta) dal template del widget nel <body>.
#         return Media(
#             css={'all': ('django_icon_picker/css/icon_picker.css',)}
#             # Niente 'js' qui!
#         )

# class PunteggioAdminForm(forms.ModelForm):
#     class Meta:
#         model = Punteggio
#         fields = '__all__'
#         widgets = {
#             'icona': MuteIconPickerWidget, # Corretto: applica la patch
#         }
        


# ----------- CLASSI INLINE -------------
class abilita_tier_inline(A_Multi_Inline):
	model = abilita_tier
	
class abilita_punteggio_inline(A_Multi_Inline):
	model = abilita_punteggio
	
class abilita_requisito_inline(A_Multi_Inline):
	model = abilita_requisito
	
class abilita_sbloccata_inline(A_Multi_Inline):
	model = abilita_sbloccata	
	
class spell_mattone_inline(A_Multi_Inline):
	model = spell_mattone

class abilita_prerequisiti_inline(A_Multi_Inline):
    model = abilita_prerequisito
    autocomplete_fields=['prerequisito',]
    search_fields=['prerequisito__nome',]
    fk_name= "abilita"
    verbose_name = "Prerequisito dell'abilità"
    verbose_name_plural = "Prerequisiti dell'abilità"

class abilita_abilitati_inline(A_Multi_Inline):
    model = abilita_prerequisito
    autocomplete_fields=['abilita',]
    search_fields=['abilita__nome',]
    fk_name= "prerequisito"
    verbose_name = "Abilita sbloccata dall'abilità"
    verbose_name_plural = "Abilita sbloccate dall'abilità"


class StatisticaPivotInlineBase(admin.TabularInline):
    """
    Inline personalizzato (v5) che pre-salva le statistiche mancanti
    nella "Change View" per creare la "pivot table".
    
    Può essere configurato per usare campi diversi per valore e default.
    """
    
    # --- INIZIO CONFIGURAZIONE ---
    # Questi valori saranno sovrascritti dalle classi figlie
    value_field = 'valore' # Campo da mostrare/modificare (es. 'valore' o 'valore_base')
    default_field = 'valore_predefinito' # Campo da cui prendere il default da Statistica
    # --- FINE CONFIGURAZIONE ---
    
    # 'statistica' è sempre readonly
    readonly_fields = ('statistica',)
    extra = 0
    # has_delete_permission = False 

    def has_delete_permission(self, request, obj=None):
        # Impedisce all'utente di cancellare una riga di statistica
        return False

    def get_fields(self, request, obj=None):
        # Aggiungi 'tipo_modificatore' se il campo valore è 'valore'
        if self.value_field == 'valore':
            return ('statistica', self.value_field, 'tipo_modificatore')
        # Altrimenti (per i Valori Base) mostra solo i due campi
        return ('statistica', self.value_field)

    def get_max_num(self, request, obj=None, **kwargs):
        return Statistica.objects.count()

    def get_formset(self, request, obj=None, **kwargs):
        if obj is not None: 
            fk_name = self.fk_name
            all_stats = Statistica.objects.all()
            
            existing_stat_pks = self.model.objects.filter(
                **{fk_name: obj}
            ).values_list('statistica_id', flat=True)

            missing_stats = all_stats.exclude(pk__in=existing_stat_pks)
            
            new_instances_to_create = []
            for stat in missing_stats:
                # Usa i campi configurati (self.value_field e self.default_field)
                new_instances_to_create.append(
                    self.model(
                        **{fk_name: obj},
                        statistica=stat,
                        # Imposta il 'valore' O 'valore_base'
                        **{self.value_field: getattr(stat, self.default_field)}
                    )
                )
            
            if new_instances_to_create:
                self.model.objects.bulk_create(new_instances_to_create)
        
        return super().get_formset(request, obj, **kwargs)
    
    class Media:
        css = {
            'all': ('admin/css/nascondi-inline-header.css',)
        }


class AbilitaStatisticaInline(StatisticaPivotInlineBase):
    model = AbilitaStatistica
    fk_name = 'abilita' # Nome del FK nel modello "through"
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    
    

# --- NUOVI INLINE PER PERSONAGGIO ---
class CreditoMovimentoInline(admin.TabularInline):
    model = CreditoMovimento
    extra = 1
    fields = ('importo', 'descrizione', 'data')
    readonly_fields = ('data',)

class PuntiCaratteristicaMovimentoInline(admin.TabularInline):
    model = PuntiCaratteristicaMovimento
    extra = 1
    fields = ('importo', 'descrizione', 'data')
    readonly_fields = ('data',)

class PersonaggioLogInline(admin.TabularInline):
    model = PersonaggioLog
    extra = 0 # Generalmente non si aggiungono log a mano
    fields = ('testo_log', 'data')
    readonly_fields = ('data',)
    
# ----------- CLASSI ADMIN -------------

@admin.register(TipologiaPersonaggio)
class TipologiaPersonaggioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'crediti_iniziali', 'caratteristiche_iniziali', 'giocante')

# class SpellAdmin(A_Admin):
# 	list_display = (
# 		'id', 
# 		'nome', 
# 		#'livello',
# 		)
# 	inlines = (spell_mattone_inline, )

@admin.register(Abilita)
class AbilitaAdmin(A_Admin):
	list_display = ('id', 'nome', )
	summernote_fields = ['descrizione', ]
	search_fields = ['nome', 'descrizione',]
	inlines = (
    	abilita_tier_inline, 
    	abilita_punteggio_inline, 
    	abilita_requisito_inline, 
    	abilita_sbloccata_inline, 
		abilita_prerequisiti_inline,
		abilita_abilitati_inline,
		AbilitaStatisticaInline,
    	)
	save_as = True
	exclude = ('statistiche',)

@admin.register(Punteggio)
class PunteggioAdmin(admin.ModelAdmin):
    # form = PunteggioAdminForm # <-- USA IL FORM PER SILENZIARE IL WIDGET
    
    # list_display = ('nome', 'tipo', 'caratteristica_relativa',)
    list_display = ('nome', 'tipo',)
    list_filter = ('tipo', 'caratteristica_relativa',)
    search_fields = ('nome', )
    # summernote_fields = ('descrizione',)
    # def formfield_for_dbfield(self, db_field, request, **kwargs):
    #     # Se stiamo processando il campo 'icona'
    #     if db_field.name == 'icona':
    #         # Forza l'uso del nostro widget "muto" (che carica solo CSS)
    #         kwargs['widget'] = MuteIconPickerWidget
            
    #     # Chiama il metodo originale con le nostre modifiche
    #     return super().formfield_for_dbfield(db_field, request, **kwargs)    






@admin.register(abilita_prerequisito)
class AbilitaPrerequisitoAdmin(A_Admin):
	list_display = ('abilita', 'prerequisito', )
	search_fields = ['abilita__nome', 'prerequisito__nome', ]
	autocomplete_fields = ['abilita', 'prerequisito',]

@admin.register(Tier)
class TierAdmin(A_Admin):
	list_display = ['nome', 'descrizione', ]
	summernote_fields = ["descrizione",]
	inlines = [abilita_tier_inline, ]
	save_as = True

@admin.register(Statistica)
class StatisticaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valore_predefinito', 'valore_base_predefinito', 'tipo_modificatore')
    # Questo eredita i campi di Punteggio, potresti doverli nascondere
    exclude = ('tipo',) # Nasconde il campo 'tipo' che forziamo a 'ST'

# Register your models here.

admin.site.register(Tabella)
#admin.site.register(Abilita, AbilitaAdmin)
#admin.site.register(Tier, TierAdmin)
#admin.site.register(Spell, SpellAdmin)
#admin.site.register(Punteggio, PunteggioAdmin)
admin.site.register(abilita_tier)
admin.site.register(abilita_punteggio)
admin.site.register(abilita_requisito)
admin.site.register(abilita_sbloccata)
admin.site.register(Mattone)
#admin.site.register(abilita_prerequisito, AbilitaPrerequisitoAdmin)

def get_statistica_base_help_text():
    """
    Crea dinamicamente l'help text con le variabili disponibili
    basate sulle 'sigle' del modello Statistica.
    """
    try:
        # Filtra solo le statistiche che hanno una sigla definita
        stats = Statistica.objects.filter(parametro__isnull=False).exclude(parametro__exact='')
        if not stats.exists():
            return "Nessuna variabile statistica (parametro) definita."
        
        # Costruisci l'elenco HTML
        base_text = "<b>Variabili Valori Base disponibili:</b><br>"
        variabili = [f"&bull; <b>{{{{{s.parametro}}}}}</b>: {s.nome}" for s in stats]
        
        # format_html è importante per la sicurezza e per renderizzare l'HTML
        return format_html(base_text + "<br>".join(variabili))
    except Exception as e:
        # Se la tabella Statistica non esiste ancora (es. prima migrazione)
        return format_html(f"<b style='color:red;'>Errore nel caricare le variabili: {e}</b>")



class PunteggioOggettoInline(admin.TabularInline):
    # Questo ora punta correttamente al modello 'OggettoElemento'
    model = Oggetto.elementi.through 
    extra = 1
    # Aggiungiamo verbose_name per chiarezza nell'admin
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Oggetto"
    
    
class PunteggioAttivataInline(admin.TabularInline):
    # Questo ora punta correttamente al modello 'AttivataElemento'
    model = Attivata.elementi.through
    extra = 1
    # Aggiungiamo verbose_name per chiarezza nell'admin
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Attivata"

class OggettoStatisticaInline(StatisticaPivotInlineBase):
    model = OggettoStatistica
    fk_name = 'oggetto' # Nome del FK nel modello "through"
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    fields = ('statistica', 'valore', 'tipo_modificatore')
    
class OggettoStatisticaBaseInline(StatisticaPivotInlineBase):
    model = OggettoStatisticaBase
    fk_name = 'oggetto'
    # Sovrascrivi i campi per usare i Valori Base
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'
    verbose_name = "Statistica (Valore Base)"
    verbose_name_plural = "Statistiche (Valori Base)"

@admin.register(Manifesto)
class ManifestoAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome', )
    readonly_fields = ('id', 'data_creazione',)
    summernote_fields = ['testo', ]

@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione',)
    readonly_fields = ('id', 'data_creazione',) 
    summernote_fields = ['testo', ]
    
@admin.register(Oggetto)
class OggettoAdmin(SModelAdmin):
    
    list_display = ('id', 'data_creazione', 'nome', 'livello')
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione',) 

    fieldsets = (
        ('Informazioni Principali', {
            'fields': ('nome', 'aura', 'testo', ('id', 'data_creazione', 'livello'))
        }),
        # Questo crea il box separato per l'anteprima
        ('Anteprima', {
            'classes': ('wide',), # 'wide' lo rende più largo
            'fields': ('mostra_testo_formattato',)
        }),
    )
    
    
    inlines = [
        PunteggioOggettoInline, 
        OggettoStatisticaInline,
        OggettoStatisticaBaseInline,
        ]
    # filter_vertical = [Oggetto.elementi.through]
    exclude = ('elementi', 'statistiche', 'statistiche_base')  # Escludi i campi ManyToMany originali  
    summernote_fields = ['testo', ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Imposta l'help_text per il campo 'testo' (che viene da A_vista)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        # Chiama la proprietà dal modello e formatta l'HTML
        return format_html(obj.TestoFormattato)
    # Imposta la caption personalizzata
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'
    
    
class AttivataStatisticaBaseInline(StatisticaPivotInlineBase):
    model = AttivataStatisticaBase
    fk_name = 'attivata'
    # Sovrascrivi i campi per usare i Valori Base
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'
    verbose_name = "Statistica (Valore Base)"
    verbose_name_plural = "Statistiche (Valori Base)"

@admin.register(Attivata)
class AttivataAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome')
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione',) 
    inlines = [AttivataStatisticaBaseInline]
    exclude = ('statistiche_base',) 
    summernote_fields = ['testo', ]   

    fieldsets = (
        ('Informazioni Principali', {
            'fields': ('nome', 'testo', ('id', 'data_creazione', 'livello'))
        }),
        # Questo crea il box separato per l'anteprima
        ('Anteprima', {
            'classes': ('wide',),
            'fields': ('mostra_testo_formattato',)
        }),
    )



    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Imposta l'help_text per il campo 'testo' (che viene da A_vista)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        # Chiama la proprietà dal modello e formatta l'HTML
        return format_html(obj.TestoFormattato)
    # Imposta la caption personalizzata
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'
    
@admin.register(Personaggio)
class PersonaggioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'proprietario', 'tipologia', 'crediti', 'punti_caratteristica')
    readonly_fields = ('id', 'data_creazione', 'crediti', 'punti_caratteristica')
    list_filter = ('tipologia',)
    search_fields = ('nome', 'proprietario__username')
    
    # Aggiungiamo i nuovi inline
    inlines = [
        CreditoMovimentoInline,
        PuntiCaratteristicaMovimentoInline,
        PersonaggioLogInline
        # Potresti voler aggiungere qui anche PersonaggioAbilitaInline, ecc.
    ]
    
    fieldsets = (
        ('Informazioni Principali', {
            'fields': (
                'nome', 'proprietario', 'tipologia', 'testo', 
                ('data_nascita', 'data_morte')
            )
        }),
        ('Valori Calcolati (Sola Lettura)', {
            'classes': ('collapse',),
            'fields': (
                ('id', 'data_creazione'),
                ('crediti', 'punti_caratteristica')
            )
        }),
    )