from django.contrib import admin
from django import forms
from django.forms import Media
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe 

# Import aggiornati dai models
from .models import (
    CARATTERISTICA, CreditoMovimento, OggettoStatisticaBase, Personaggio, 
    PersonaggioLog, QrCode, Oggetto, Manifesto, OggettoStatistica, 
    Attivata, AttivataStatisticaBase, TipologiaPersonaggio,
    # NUOVI IMPORT PER TECNICHE
    Infusione, Tessitura, InfusioneMattone, TessituraMattone,
    InfusioneStatisticaBase, TessituraStatisticaBase,
    PersonaggioInfusione, PersonaggioTessitura,
    InfusionePluginModel, TessituraPluginModel
)
from .models import (
    Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica, 
    PuntiCaratteristicaMovimento, STATISTICA
)
from .models import (
    Tabella, Tier, Abilita, Mattone, 
    Caratteristica, Aura, ModelloAura, MattoneStatistica, PersonaggioModelloAura,
    Messaggio, Gruppo,
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
            'icona': CustomIconWidget,
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
                for field_name in self.fields:
                    self.fields[field_name].widget.attrs['style'] = HIGHLIGHT_STYLE

class MattoneStatisticaForm(forms.ModelForm):
    """Form specifico per il Mattone per evidenziare modifiche"""
    class Meta:
        model = MattoneStatistica
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.statistica:
            default_value = self.instance.statistica.valore_predefinito
            current_value = self.instance.valore
            if current_value != default_value:
                for field_name in self.fields:
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
                for field_name in self.fields:
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
                for field_name in self.fields:
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
                for field_name in self.fields:
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
    def has_delete_permission(self, request, obj=None): return False
    def get_fields(self, request, obj=None):
        if self.value_field == 'valore': return ('statistica', self.value_field, 'tipo_modificatore')
        return ('statistica', self.value_field)
    def get_max_num(self, request, obj=None, **kwargs): return Statistica.objects.count()
    def get_formset(self, request, obj=None, **kwargs):
        if obj is not None: 
            fk_name = self.fk_name
            all_stats = Statistica.objects.all()
            existing_stat_pks = self.model.objects.filter(**{fk_name: obj}).values_list('statistica_id', flat=True)
            missing_stats = all_stats.exclude(pk__in=existing_stat_pks)
            new_instances_to_create = []
            for stat in missing_stats:
                new_instances_to_create.append(self.model(**{fk_name: obj}, statistica=stat, **{self.value_field: getattr(stat, self.default_field)}))
            if new_instances_to_create:
                self.model.objects.bulk_create(new_instances_to_create)
        return super().get_formset(request, obj, **kwargs)
    class Media:
        css = {'all': ('admin/css/nascondi-inline-header.css',)}

class AbilitaStatisticaInline(StatisticaPivotInlineBase):
    model = AbilitaStatistica
    form = AbilitaStatisticaForm 
    fk_name = 'abilita' 
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    value_field = 'valore'
    default_field = 'valore_predefinito'

class MattoneStatisticaInline(StatisticaPivotInlineBase):
    model = MattoneStatistica
    form = MattoneStatisticaForm
    fk_name = 'mattone'
    verbose_name = "Statistica (Modificatore Metatalento)"
    verbose_name_plural = "Statistiche (Modificatori Metatalento)"
    value_field = 'valore'
    default_field = 'valore_predefinito'

class MattoneInlineForAura(admin.TabularInline):
    model = Mattone
    fk_name = 'aura'
    extra = 1
    verbose_name = "Mattone associato"
    verbose_name_plural = "Mattoni associati a questa Aura"
    fields = ('nome', 'caratteristica_associata', 'funzionamento_metatalento')
    show_change_link = True 

# --- INLINE PER PERSONAGGIO ---
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

class PersonaggioModelloAuraInline(admin.TabularInline):
    model = PersonaggioModelloAura
    extra = 1
    verbose_name = "Modello Aura Applicato"
    verbose_name_plural = "Modelli Aura Applicati"

# --- INLINE PER PERSONAGGIO (INFUSIONI E TESSITURE) ---
class PersonaggioInfusioneInline(admin.TabularInline):
    model = PersonaggioInfusione
    extra = 1
    verbose_name = "Infusione Posseduta"
    verbose_name_plural = "Infusioni Possedute"
    autocomplete_fields = ['infusione']

class PersonaggioTessituraInline(admin.TabularInline):
    model = PersonaggioTessitura
    extra = 1
    verbose_name = "Tessitura Posseduta"
    verbose_name_plural = "Tessiture Possedute"
    autocomplete_fields = ['tessitura']

# ----------- HELPER FUNCTION PER RENDERING HTML -------------

def get_statistica_base_help_text():
    try:
        stats = Statistica.objects.filter(parametro__isnull=False).exclude(parametro__exact='')
        if not stats.exists(): return mark_safe("Nessuna variabile statistica definita.")
        items = []
        for s in stats:
            item_html = "&bull; <b>{{{}}}</b>: {}".format(s.parametro, s.nome)
            items.append(item_html)
        base_text = "<b>Variabili Valori Base disponibili:</b><br>"
        joined_items = "<br>".join(items)
        return mark_safe(base_text + joined_items)
    except Exception as e:
        return format_html(f"<b style='color:red;'>Errore nel caricare le variabili: {e}</b>")

def get_mattone_help_text():
    stats_text = get_statistica_base_help_text() 
    extra_text = mark_safe("<br><b>Variabili Speciali Mattone:</b><br>&bull; <b>{caratt}</b>: Valore della caratteristica associata.<br>&bull; <b>{3*caratt}</b>: Moltiplicatore (es. 3x).")
    return stats_text + extra_text

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
    inlines = (abilita_tier_inline, AbilitaStatisticaInline, abilita_punteggio_inline, abilita_requisito_inline, abilita_prerequisiti_inline,)
    save_as = True
    exclude = ('statistiche',)

@admin.register(Punteggio)
class PunteggioAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome','icona_html', 'icona_cerchio_html', 'icona_cerchio_inverted_html', 'tipo', 'ordine', 'caratteristica_relativa','colore',)
    list_filter = ('tipo', 'caratteristica_relativa',)
    list_editable = ('ordine','tipo', )
    search_fields = ('nome', )
    summernote_fields = ('descrizione',)
    save_as = True
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(tipo=CARATTERISTICA).exclude(tipo='MA')

@admin.register(Caratteristica)
class CaratteristicaAdmin(A_Admin): 
    form = PunteggioAdminForm
    list_display = ('nome', 'sigla', 'icona_html', 'icona_cerchio_html','ordine', 'icona_cerchio_inverted_html','colore',)
    list_editable = ('ordine',)
    search_fields = ('nome', 'sigla')
    summernote_fields = ('descrizione',) 
    inlines = [CaratteristicaModificatoreInline]
    def get_queryset(self, request): return super().get_queryset(request).filter(tipo=CARATTERISTICA)
    def get_exclude(self, request, obj=None): return ('tipo', 'descrizione',)

@admin.register(Aura)
class AuraAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'sigla', 'icona_html', 'ordine', 'icona_cerchio_html', 'is_soprannaturale', 'is_generica')
    list_editable = ('ordine', 'is_soprannaturale', 'is_generica')
    search_fields = ('nome',)
    summernote_fields = ('descrizione',)
    inlines = [MattoneInlineForAura]
    def get_queryset(self, request): return super().get_queryset(request).filter(tipo=AURA)
    def get_exclude(self, request, obj=None): return ('tipo', 'descrizione', 'caratteristica_relativa')

@admin.register(ModelloAura)
class ModelloAuraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'aura')
    list_filter = ('aura',)
    filter_horizontal = ('mattoni_proibiti',)

@admin.register(Mattone)
class MattoneAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'aura', 'caratteristica_associata', 'funzionamento_metatalento')
    list_filter = ('aura', 'caratteristica_associata', 'funzionamento_metatalento')
    search_fields = ('nome', 'testo_addizionale')
    summernote_fields = ('descrizione_mattone', 'descrizione_metatalento', 'testo_addizionale')
    inlines = [MattoneStatisticaInline]
    fieldsets = (
        ('Dati Mattone', {'fields': ('nome', 'aura', 'caratteristica_associata', 'tipo', 'descrizione_mattone', 'icona', 'colore')}),
        ('Metatalento', {'fields': ('funzionamento_metatalento', 'descrizione_metatalento', 'testo_addizionale'),}),
        ('Sistema', {'fields': ('sigla',), 'classes': ('collapse',),})
    )
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo_addizionale' in form.base_fields:
            form.base_fields['testo_addizionale'].help_text = get_mattone_help_text()
        return form
    def get_exclude(self, request, obj=None): return ('tipo', 'descrizione', 'caratteristica_relativa')

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

# --- OGGETTI E ATTIVATE ---

class PunteggioOggettoInline(admin.TabularInline):
    model = Oggetto.elementi.through 
    extra = 1
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Oggetto"
    
# --- INLINE SPECIALI CONDIZIONALI ---

class StatisticaCondizionaleInlineBase(admin.StackedInline):
    extra = 0
    filter_horizontal = ('limit_a_aure', 'limit_a_elementi') 
    fieldsets = (
        (None, {
            'fields': (('statistica', 'valore_base'),)
        }),
        ('Limitazioni Condizionali (Opzionale)', {
            'classes': ('collapse',),
            'fields': ('limit_a_aure', 'limit_a_elementi'),
            'description': "Seleziona elementi/aure per applicare questo bonus SOLO se la tecnica/oggetto corrisponde."
        }),
    )

# Inline per Oggetto (statistica base)
class OggettoStatisticaInline(StatisticaPivotInlineBase):
    model = OggettoStatistica
    form = OggettoStatisticaForm
    fk_name = 'oggetto' 
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    value_field = 'valore'
    default_field = 'valore_predefinito'

class OggettoStatisticaBaseInline(StatisticaPivotInlineBase):
    model = OggettoStatisticaBase
    form = OggettoStatisticaBaseForm
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
        ('Informazioni Principali', {'fields': ('nome', 'aura', 'testo', ('id', 'data_creazione', 'livello'))}),
        ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)}),
    )
    inlines = [PunteggioOggettoInline, OggettoStatisticaInline, OggettoStatisticaBaseInline,]
    exclude = ('elementi', 'statistiche', 'statistiche_base') 
    summernote_fields = ['testo', ]
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    # CORREZIONE: Utilizzo sicuro di format_html
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'

# --- NUOVE CONFIGURAZIONI E INLINE PER INFUSIONE E TESSITURA ---

class InfusioneStatisticaInline(StatisticaCondizionaleInlineBase):
    model = InfusioneStatisticaBase
    fk_name = 'infusione'

class TessituraStatisticaInline(StatisticaCondizionaleInlineBase):
    model = TessituraStatisticaBase
    fk_name = 'tessitura'

class InfusioneMattoneInline(admin.TabularInline):
    model = InfusioneMattone
    extra = 1
    autocomplete_fields = ['mattone']
    ordering = ['ordine']

class TessituraMattoneInline(admin.TabularInline):
    model = TessituraMattone
    extra = 1
    autocomplete_fields = ['mattone']
    ordering = ['ordine']

@admin.register(Infusione)
class InfusioneAdmin(SModelAdmin):
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'aura_infusione')
    search_fields = ['nome']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    inlines = [InfusioneMattoneInline, InfusioneStatisticaInline]
    exclude = ('statistiche_base', 'mattoni')
    summernote_fields = ['testo']
    autocomplete_fields = ['aura_richiesta', 'aura_infusione']
    
    fieldsets = (
        ('Dati Infusione', {
            'fields': ('nome', 'aura_richiesta', 'aura_infusione', 'testo', ('id', 'data_creazione', 'livello'))
        }),
        ('Anteprima', {
            'classes': ('wide',), 'fields': ('mostra_testo_formattato',)
        }),
    )
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields: form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    # CORREZIONE: Utilizzo sicuro di format_html
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

@admin.register(Tessitura)
class TessituraAdmin(SModelAdmin):
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'elemento_principale')
    search_fields = ['nome']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    inlines = [TessituraMattoneInline, TessituraStatisticaInline]
    exclude = ('statistiche_base', 'mattoni')
    summernote_fields = ['testo', 'formula']
    autocomplete_fields = ['aura_richiesta', 'elemento_principale']
    
    fieldsets = (
        ('Dati Tessitura', {
            'fields': ('nome', 'aura_richiesta', 'elemento_principale', 'formula', 'testo', ('id', 'data_creazione', 'livello'))
        }),
        ('Anteprima', {
            'classes': ('wide',), 'fields': ('mostra_testo_formattato',)
        }),
    )
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields: form.base_fields['testo'].help_text = get_statistica_base_help_text()
        if 'formula' in form.base_fields: form.base_fields['formula'].help_text += " Supporta anche {elem} e {rango}."
        return form
    
    # CORREZIONE: Utilizzo sicuro di format_html
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

# --- INLINE PER PERSONAGGIO: RELAZIONI (LEGACY E NUOVE) ---

class PersonaggioInfusioneInline(admin.TabularInline):
    model = PersonaggioInfusione
    extra = 1
    verbose_name = "Infusione Posseduta"
    verbose_name_plural = "Infusioni Possedute"
    autocomplete_fields = ['infusione']

class PersonaggioTessituraInline(admin.TabularInline):
    model = PersonaggioTessitura
    extra = 1
    verbose_name = "Tessitura Posseduta"
    verbose_name_plural = "Tessiture Possedute"
    autocomplete_fields = ['tessitura']

@admin.register(Personaggio)
class PersonaggioAdmin(A_Admin): 
    list_display = ('nome', 'proprietario', 'tipologia', 'crediti', 'punti_caratteristica')
    readonly_fields = ('id', 'data_creazione', 'crediti', 'punti_caratteristica')
    list_filter = ('tipologia',)
    search_fields = ('nome', 'proprietario__username')
    summernote_fields = ('testo',)
    
    inlines = [
        PersonaggioModelloAuraInline,
        PersonaggioInfusioneInline, # Nuovo
        PersonaggioTessituraInline, # Nuovo
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
    
# ----------- MESSAGGISTICA E GRUPPI -------------

@admin.register(Gruppo)
class GruppoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'conteggio_membri')
    search_fields = ('nome',)
    filter_horizontal = ('membri',)
    def conteggio_membri(self, obj): return obj.membri.count()
    conteggio_membri.short_description = "Numero Membri"

@admin.register(Messaggio)
class MessaggioAdmin(SModelAdmin): 
    list_display = ('titolo', 'tipo_messaggio', 'mittente', 'get_destinatario', 'data_invio', 'salva_in_cronologia')
    list_filter = ('tipo_messaggio', 'salva_in_cronologia', 'data_invio')
    search_fields = ('titolo', 'testo', 'mittente__username', 'destinatario_personaggio__nome', 'destinatario_gruppo__nome')
    date_hierarchy = 'data_invio'
    summernote_fields = ('testo',)
    autocomplete_fields = ['destinatario_personaggio', 'destinatario_gruppo'] 
    
    fieldsets = (
        ('Dettagli Messaggio', {
            'fields': ('titolo', 'mittente', 'data_invio', 'salva_in_cronologia')
        }),
        ('Contenuto', {
            'fields': ('testo',)
        }),
        ('Destinazione', {
            'fields': ('tipo_messaggio', 'destinatario_personaggio', 'destinatario_gruppo'),
            'description': "Seleziona il tipo di messaggio e compila SOLO il campo corrispondente (Personaggio o Gruppo). Se Broadcast, lascia vuoti i destinatari."
        }),
    )

    def get_destinatario(self, obj):
        if obj.tipo_messaggio == 'BROAD': return format_html("<b>TUTTI (Broadcast)</b>")
        elif obj.tipo_messaggio == 'GROUP': return format_html(f"Gruppo: {obj.destinatario_gruppo}")
        elif obj.tipo_messaggio == 'INDV': return format_html(f"Pg: {obj.destinatario_personaggio}")
        return "-"
    get_destinatario.short_description = "Destinatario"

    def save_model(self, request, obj, form, change):
        if not obj.mittente: obj.mittente = request.user
        super().save_model(request, obj, form, change)