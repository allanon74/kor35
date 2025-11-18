from django.contrib import admin
from django import forms
from django.forms import Media
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin
from django.utils.html import format_html
from .models import (
    CARATTERISTICA, CreditoMovimento, OggettoStatisticaBase, Personaggio, 
    PersonaggioLog, QrCode, Oggetto, Manifesto, OggettoStatistica, Attivata, 
    AttivataStatisticaBase, TipologiaPersonaggio
)
from .models import (
    Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica, 
    PuntiCaratteristicaMovimento, STATISTICA
)
from .models import (
    Tabella, Punteggio, Tier, Abilita, 
    Caratteristica # Importa il modello Proxy
)
from .models import (
    abilita_tier, abilita_punteggio, abilita_requisito, abilita_sbloccata, 
    abilita_prerequisito, AbilitaStatistica, 
    CaratteristicaModificatore
)

from django_icon_picker.widgets import IconPicker
from icon_widget.widgets import CustomIconWidget

# ----------- STILE E FORMS PERSONALIZZATI -------------

HIGHLIGHT_STYLE = 'background-color: #fff3e0; border: 2px solid #ff9800; font-weight: bold;'

class PunteggioAdminForm(forms.ModelForm):
    class Meta:
        model = Punteggio
        fields = '__all__'
        widgets = {
            'icona': CustomIconWidget, # Applica il widget al campo 'icona
        }

# --- Forms per evidenziare i valori modificati ---

class AbilitaStatisticaForm(forms.ModelForm):
    class Meta:
        model = AbilitaStatistica
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.statistica:
            default_value = self.instance.statistica.valore_predefinito
            current_value = self.instance.valore
            
            if current_value != default_value:
                # Applica lo stile a tutti i campi della riga
                for field_name in self.fields:
                    # if field_name != 'statistica': # Non evidenziare il campo readonly
                        self.fields[field_name].widget.attrs['style'] = HIGHLIGHT_STYLE
                        
class OggettoStatisticaBaseForm(forms.ModelForm):
    class Meta:
        model = OggettoStatisticaBase
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.statistica:
            default_value = self.instance.statistica.valore_base_predefinito
            current_value = self.instance.valore_base
            
            if current_value != default_value:
                # Applica lo stile a tutti i campi della riga
                for field_name in self.fields:
                    # if field_name != 'statistica':
                        self.fields[field_name].widget.attrs['style'] = HIGHLIGHT_STYLE

class OggettoStatisticaForm(forms.ModelForm):
    class Meta:
        model = OggettoStatistica
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.statistica:
            default_value = self.instance.statistica.valore_predefinito
            current_value = self.instance.valore
            
            if current_value != default_value:
                # Applica lo stile a tutti i campi della riga
                for field_name in self.fields:
                    # if field_name != 'statistica':
                        self.fields[field_name].widget.attrs['style'] = HIGHLIGHT_STYLE
                        
class AttivataStatisticaBaseForm(forms.ModelForm):
    class Meta:
        model = AttivataStatisticaBase
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.statistica:
            default_value = self.instance.statistica.valore_base_predefinito
            current_value = self.instance.valore_base
            
            if current_value != default_value:
                # Applica lo stile a tutti i campi della riga
                for field_name in self.fields:
                    # if field_name != 'statistica':
                        self.fields[field_name].widget.attrs['style'] = HIGHLIGHT_STYLE


# ----------- CLASSI ASTRATTE ADMIN -------------

class A_Admin(SModelAdmin):
    actions_on_top = True
    save_on_top = True

    class Meta:
        abstract = True
        
class A_Multi_Inline (admin.TabularInline):
    extra = 1
    
    class Meta:
        abstract = True

# ----------- CLASSI INLINE -------------

class CaratteristicaModificatoreInline(admin.TabularInline):
    model = CaratteristicaModificatore
    fk_name = "caratteristica" 
    verbose_name = "Modificatore Statistica"
    verbose_name_plural = "Statistiche Modificate da questa Caratteristica"
    extra = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "statistica_modificata":
            kwargs["queryset"] = Statistica.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class abilita_tier_inline(A_Multi_Inline):
    model = abilita_tier
    
class abilita_punteggio_inline(A_Multi_Inline):
    model = abilita_punteggio
    extra = 1
    verbose_name = "Punteggio Assegnato"
    verbose_name_plural = "Punteggi Assegnati (es. +1 Forza, +1 Culto)"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "punteggio":
            kwargs["queryset"] = Punteggio.objects.exclude(tipo=STATISTICA)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
class abilita_requisito_inline(A_Multi_Inline):
    model = abilita_requisito
    
class abilita_sbloccata_inline(A_Multi_Inline):
    model = abilita_sbloccata    

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
    readonly_fields = ('statistica',)
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        if self.value_field == 'valore':
            return ('statistica', self.value_field, 'tipo_modificatore')
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
                new_instances_to_create.append(
                    self.model(
                        **{fk_name: obj},
                        statistica=stat,
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
    form = AbilitaStatisticaForm  # <-- USA IL FORM PERSONALIZZATO
    fk_name = 'abilita' 
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    
    # Sovrascrive i campi base per questa specifica implementazione
    value_field = 'valore'
    default_field = 'valore_predefinito'
    

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
    extra = 0 
    fields = ('testo_log', 'data')
    readonly_fields = ('data',)
    
# ----------- CLASSI ADMIN -------------

@admin.register(TipologiaPersonaggio)
class TipologiaPersonaggioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'crediti_iniziali', 'caratteristiche_iniziali', 'giocante')

@admin.register(Abilita)
class AbilitaAdmin(A_Admin):
    list_display = ('id', 'nome','costo_pc', 'costo_crediti' )
    list_editable = ('costo_pc', 'costo_crediti', )
    summernote_fields = ['descrizione', ]
    search_fields = ['nome', 'descrizione',]
    inlines = (
        abilita_tier_inline,
        AbilitaStatisticaInline, 
        abilita_punteggio_inline, 
        abilita_requisito_inline, 
        # abilita_sbloccata_inline, 
        abilita_prerequisiti_inline,
        # abilita_abilitati_inline,
        )
    save_as = True
    exclude = ('statistiche',) # 'statistiche' è corretto, non 'statistiche_base'

@admin.register(Punteggio)
class PunteggioAdmin(A_Admin):
    form = PunteggioAdminForm
    
    list_display = ('nome','icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html', 'tipo', 'caratteristica_relativa',)
    list_filter = ('tipo', 'caratteristica_relativa',)
    search_fields = ('nome', )
    summernote_fields = ('descrizione',)
    save_as = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(tipo=CARATTERISTICA)

@admin.register(Caratteristica)
class CaratteristicaAdmin(A_Admin): # <-- Eredita da A_Admin se vuoi Summernote
    form = PunteggioAdminForm # Usa lo stesso form per il widget icona
    list_display = ('nome', 'sigla', 'icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html',)
    search_fields = ('nome', 'sigla')
    summernote_fields = ('descrizione',) # Aggiunto
    
    inlines = [CaratteristicaModificatoreInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(tipo=CARATTERISTICA)
        
    def get_exclude(self, request, obj=None):
        # Escludiamo 'tipo' e altri campi non necessari di Tabella
        return ('tipo', 'descrizione',) # 'descrizione' è gestita da summernote_fields

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
class StatisticaAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'parametro', 'is_primaria', 'valore_predefinito', 'valore_base_predefinito', 'tipo_modificatore')
    list_editable = ('is_primaria',)
    exclude = ('tipo',) 
    summernote_fields = ('descrizione',)

# Registrazioni base
admin.site.register(Tabella)
admin.site.register(abilita_tier)
admin.site.register(abilita_punteggio)
admin.site.register(abilita_requisito)
admin.site.register(abilita_sbloccata)



def get_statistica_base_help_text():
    """
    Crea dinamicamente l'help text con le variabili disponibili
    basate sulle 'sigle' del modello Statistica.
    """
    try:
        stats = Statistica.objects.filter(parametro__isnull=False).exclude(parametro__exact='')
        if not stats.exists():
            return "Nessuna variabile statistica (parametro) definita."
        
        base_text = "<b>Variabili Valori Base disponibili:</b><br>"
        variabili = [f"&bull; <b>{{{{{s.parametro}}}}}</b>: {s.nome}" for s in stats]
        
        return format_html(base_text + "<br>".join(variabili))
    except Exception as e:
        return format_html(f"<b style='color:red;'>Errore nel caricare le variabili: {e}</b>")


class PunteggioOggettoInline(admin.TabularInline):
    model = Oggetto.elementi.through 
    extra = 1
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Oggetto"
    
    
class PunteggioAttivataInline(admin.TabularInline):
    model = Attivata.elementi.through
    extra = 1
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Attivata"

class OggettoStatisticaInline(StatisticaPivotInlineBase):
    model = OggettoStatistica
    form = OggettoStatisticaForm      # <-- USA IL FORM PERSONALIZZATO
    fk_name = 'oggetto' 
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    
    # Configurazione per la classe base
    value_field = 'valore'
    default_field = 'valore_predefinito'
    
class OggettoStatisticaBaseInline(StatisticaPivotInlineBase):
    model = OggettoStatisticaBase
    form = OggettoStatisticaBaseForm  # <-- USA IL FORM PERSONALIZZATO
    fk_name = 'oggetto'
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
        ('Anteprima', {
            'classes': ('wide',), 
            'fields': ('mostra_testo_formattato',)
        }),
    )
    
    inlines = [
        PunteggioOggettoInline, 
        OggettoStatisticaInline,
        OggettoStatisticaBaseInline,
        ]
    exclude = ('elementi', 'statistiche', 'statistiche_base') 
    summernote_fields = ['testo', ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html(obj.TestoFormattato)
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'
    
    
class AttivataStatisticaBaseInline(StatisticaPivotInlineBase):
    model = AttivataStatisticaBase
    form = AttivataStatisticaBaseForm # <-- USA IL FORM PERSONALIZZATO
    fk_name = 'attivata'
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'
    verbose_name = "Statistica (Valore Base)"
    verbose_name_plural = "Statistiche (Valori Base)"

@admin.register(Attivata)
class AttivataAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome')
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione',) 
    inlines = [AttivataStatisticaBaseInline, PunteggioAttivataInline] # Aggiunto PunteggioAttivataInline
    exclude = ('statistiche_base', 'elementi') # Aggiunto elementi
    summernote_fields = ['testo', ]    

    fieldsets = (
        ('Informazioni Principali', {
            'fields': ('nome', 'testo', ('id', 'data_creazione', 'livello'))
        }),
        ('Anteprima', {
            'classes': ('wide',),
            'fields': ('mostra_testo_formattato',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html(obj.TestoFormattato)
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'
    
@admin.register(Personaggio)
class PersonaggioAdmin(A_Admin): # Eredita da A_Admin per Summernote
    list_display = ('nome', 'proprietario', 'tipologia', 'crediti', 'punti_caratteristica')
    readonly_fields = ('id', 'data_creazione', 'crediti', 'punti_caratteristica')
    list_filter = ('tipologia',)
    search_fields = ('nome', 'proprietario__username')
    summernote_fields = ('testo',) # Aggiunto
    
    inlines = [
        CreditoMovimentoInline,
        PuntiCaratteristicaMovimentoInline,
        PersonaggioLogInline
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