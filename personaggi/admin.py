from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe 
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin

# Import Models
from .models import (
    CARATTERISTICA, CreditoMovimento, OggettoStatisticaBase, Personaggio, 
    PersonaggioLog, QrCode, Oggetto, Manifesto, OggettoStatistica, 
    Attivata, AttivataStatisticaBase, TipologiaPersonaggio,
    Infusione, Tessitura, InfusioneMattone, TessituraMattone,
    InfusioneStatisticaBase, TessituraStatisticaBase,
    InfusioneStatistica, TessituraStatistica, # Modificatori
    PersonaggioInfusione, PersonaggioTessitura, PersonaggioModelloAura,
    InfusionePluginModel, TessituraPluginModel,
    Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica, 
    PuntiCaratteristicaMovimento, STATISTICA,
    Tabella, Tier, Abilita, Mattone, 
    Caratteristica, Aura, ModelloAura, MattoneStatistica, 
    Messaggio, Gruppo,
    abilita_tier, abilita_punteggio, abilita_requisito, abilita_sbloccata, 
    abilita_prerequisito, AbilitaStatistica, CaratteristicaModificatore
)

from icon_widget.widgets import CustomIconWidget

HIGHLIGHT_STYLE = 'background-color: #fff3e0; border: 2px solid #ff9800; font-weight: bold;'

class PunteggioAdminForm(forms.ModelForm):
    class Meta:
        model = Punteggio
        fields = '__all__'
        widgets = {
            'icona': CustomIconWidget,
        }

# Forms
class AbilitaStatisticaForm(forms.ModelForm):
    class Meta:
        model = AbilitaStatistica
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.statistica and self.instance.valore != self.instance.statistica.valore_predefinito:
             for f in self.fields:
                 self.fields[f].widget.attrs['style'] = HIGHLIGHT_STYLE

class MattoneStatisticaForm(forms.ModelForm):
    class Meta:
        model = MattoneStatistica
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.statistica and self.instance.valore != self.instance.statistica.valore_predefinito:
             for f in self.fields:
                 self.fields[f].widget.attrs['style'] = HIGHLIGHT_STYLE

class OggettoStatisticaBaseForm(forms.ModelForm):
    class Meta:
        model = OggettoStatisticaBase
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.statistica and self.instance.valore_base != self.instance.statistica.valore_base_predefinito:
             for f in self.fields:
                 self.fields[f].widget.attrs['style'] = HIGHLIGHT_STYLE

class OggettoStatisticaForm(forms.ModelForm):
    class Meta:
        model = OggettoStatistica
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.statistica and self.instance.valore != self.instance.statistica.valore_predefinito:
             for f in self.fields:
                 self.fields[f].widget.attrs['style'] = HIGHLIGHT_STYLE

class AttivataStatisticaBaseForm(forms.ModelForm):
    class Meta:
        model = AttivataStatisticaBase
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.statistica and self.instance.valore_base != self.instance.statistica.valore_base_predefinito:
             for f in self.fields:
                 self.fields[f].widget.attrs['style'] = HIGHLIGHT_STYLE

# Base Classes
class A_Admin(SModelAdmin):
    actions_on_top = True
    save_on_top = True
    class Meta:
        abstract = True

class A_Multi_Inline (admin.TabularInline):
    extra = 1
    class Meta:
        abstract = True

# Inlines
class CaratteristicaModificatoreInline(admin.TabularInline):
    model = CaratteristicaModificatore
    fk_name = "caratteristica"
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
    verbose_name_plural = "Punteggi Assegnati"
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
    fk_name= "abilita"
    autocomplete_fields=['prerequisito']

class abilita_abilitati_inline(A_Multi_Inline):
    model = abilita_prerequisito
    fk_name= "prerequisito"
    autocomplete_fields=['abilita']

# Pivot Logic
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
            existing = self.model.objects.filter(**{fk_name: obj}).values_list('statistica_id', flat=True)
            missing = all_stats.exclude(pk__in=existing)
            new_objs = [self.model(**{fk_name: obj}, statistica=s, **{self.value_field: getattr(s, self.default_field)}) for s in missing]
            if new_objs:
                self.model.objects.bulk_create(new_objs)
        return super().get_formset(request, obj, **kwargs)
    
    class Media:
        css = {'all': ('admin/css/nascondi-inline-header.css',)}

class AbilitaStatisticaInline(StatisticaPivotInlineBase):
    model = AbilitaStatistica
    form = AbilitaStatisticaForm
    fk_name = 'abilita'
    value_field = 'valore'
    default_field = 'valore_predefinito'

class MattoneStatisticaInline(StatisticaPivotInlineBase):
    model = MattoneStatistica
    form = MattoneStatisticaForm
    fk_name = 'mattone'
    value_field = 'valore'
    default_field = 'valore_predefinito'

class MattoneInlineForAura(admin.TabularInline):
    model = Mattone
    fk_name = 'aura'
    extra = 1
    fields = ('nome', 'caratteristica_associata', 'funzionamento_metatalento')
    show_change_link = True

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

# Helpers
def get_statistica_base_help_text():
    try:
        stats = Statistica.objects.filter(parametro__isnull=False).exclude(parametro__exact='')
        if not stats.exists():
            return mark_safe("Nessuna variabile statistica definita.")
        items = ["&bull; <b>{{{}}}</b>: {}".format(s.parametro, s.nome) for s in stats]
        return mark_safe("<b>Variabili Valori Base disponibili:</b><br>" + "<br>".join(items))
    except Exception as e:
        return format_html(f"<b style='color:red;'>Errore: {e}</b>")

def get_mattone_help_text():
    return get_statistica_base_help_text() + mark_safe("<br><b>Variabili Speciali Mattone:</b><br>&bull; <b>{caratt}</b>: Valore della caratteristica associata.<br>&bull; <b>{3*caratt}</b>: Moltiplicatore (es. 3x).")

# Admins
@admin.register(TipologiaPersonaggio)
class TipologiaPersonaggioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'crediti_iniziali', 'caratteristiche_iniziali', 'giocante')

@admin.register(Abilita)
class AbilitaAdmin(A_Admin):
    list_display = ('id', 'nome','costo_pc', 'costo_crediti')
    list_editable = ('costo_pc', 'costo_crediti')
    summernote_fields = ['descrizione']
    search_fields = ['nome', 'descrizione']
    inlines = (abilita_tier_inline, AbilitaStatisticaInline, abilita_punteggio_inline, abilita_requisito_inline, abilita_prerequisiti_inline)
    save_as = True
    exclude = ('statistiche',)

@admin.register(Punteggio)
class PunteggioAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome','icona_html', 'icona_cerchio_html', 'tipo', 'ordine', 'caratteristica_relativa','colore')
    list_filter = ('tipo', 'caratteristica_relativa')
    list_editable = ('ordine','tipo')
    search_fields = ('nome',)
    summernote_fields = ('descrizione',)
    save_as = True
    
    def get_queryset(self, request):
        return super().get_queryset(request).exclude(tipo=CARATTERISTICA).exclude(tipo='MA')

@admin.register(Caratteristica)
class CaratteristicaAdmin(A_Admin): 
    form = PunteggioAdminForm
    list_display = ('nome', 'sigla', 'icona_html', 'icona_cerchio_html','ordine', 'colore')
    list_editable = ('ordine',)
    search_fields = ('nome', 'sigla')
    summernote_fields = ('descrizione',) 
    inlines = [CaratteristicaModificatoreInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo=CARATTERISTICA)
    
    def get_exclude(self, request, obj=None):
        return ('tipo', 'descrizione',)

@admin.register(Aura)
class AuraAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'sigla', 'icona_html', 'ordine', 'icona_cerchio_html', 'is_soprannaturale', 'is_generica')
    list_editable = ('ordine', 'is_soprannaturale', 'is_generica')
    search_fields = ('nome',)
    summernote_fields = ('descrizione',)
    inlines = [MattoneInlineForAura]
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo=AURA)
    
    def get_exclude(self, request, obj=None):
        return ('tipo', 'descrizione', 'caratteristica_relativa')

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
        ('Metatalento', {'fields': ('funzionamento_metatalento', 'descrizione_metatalento', 'testo_addizionale')}),
        ('Sistema', {'fields': ('sigla',), 'classes': ('collapse',)})
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo_addizionale' in form.base_fields:
            form.base_fields['testo_addizionale'].help_text = get_mattone_help_text()
        return form
    
    def get_exclude(self, request, obj=None):
        return ('tipo', 'descrizione', 'caratteristica_relativa')

@admin.register(abilita_prerequisito)
class AbilitaPrerequisitoAdmin(A_Admin):
    list_display = ('abilita', 'prerequisito', )
    search_fields = ['abilita__nome', 'prerequisito__nome', ]
    autocomplete_fields = ['abilita', 'prerequisito']

@admin.register(Tier)
class TierAdmin(A_Admin):
    list_display = ['nome', 'descrizione', ]
    summernote_fields = ["descrizione"]
    inlines = [abilita_tier_inline, ]
    save_as = True

@admin.register(Statistica)
class StatisticaAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'parametro', 'is_primaria', 'valore_predefinito', 'valore_base_predefinito', 'tipo_modificatore')
    list_editable = ('is_primaria',)
    exclude = ('tipo',) 
    summernote_fields = ('descrizione',)

admin.site.register(Tabella)
admin.site.register(abilita_tier)
admin.site.register(abilita_punteggio)
admin.site.register(abilita_requisito)
admin.site.register(abilita_sbloccata)

class PunteggioOggettoInline(admin.TabularInline):
    model = Oggetto.elementi.through
    extra = 1
    verbose_name_plural = "Elementi dell'Oggetto"

# --- INLINE SPECIALI (Conditional + Pivot) ---

class StatisticaCondizionaleInlineBase(admin.StackedInline):
    extra = 0
    filter_horizontal = ('limit_a_aure', 'limit_a_elementi') 
    readonly_fields = ('statistica',)
    
    fieldsets = (
        (None, {'fields': (('statistica', 'valore', 'tipo_modificatore'),)}),
        ('Condizioni', {
            'classes': ('collapse',),
            'fields': (('usa_limitazione_aura', 'limit_a_aure'), ('usa_limitazione_elemento', 'limit_a_elementi'))
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_max_num(self, request, obj=None, **kwargs):
        return Statistica.objects.count()
    
    def get_formset(self, request, obj=None, **kwargs):
        if obj is not None: 
            fk_name = self.fk_name
            all_stats = Statistica.objects.all()
            existing = self.model.objects.filter(**{fk_name: obj}).values_list('statistica_id', flat=True)
            missing = all_stats.exclude(pk__in=existing)
            new_objs = [self.model(**{fk_name: obj}, statistica=s, **{self.value_field: getattr(s, self.default_field)}) for s in missing]
            if new_objs:
                self.model.objects.bulk_create(new_objs)
        return super().get_formset(request, obj, **kwargs)

class OggettoStatisticaInline(StatisticaCondizionaleInlineBase):
    model = OggettoStatistica
    fk_name = 'oggetto'
    value_field = 'valore'
    default_field = 'valore_predefinito'

class OggettoStatisticaBaseInline(StatisticaPivotInlineBase):
    model = OggettoStatisticaBase
    form = OggettoStatisticaBaseForm
    fk_name = 'oggetto'
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'
    verbose_name = "Statistica (Valore Base)"

@admin.register(Manifesto)
class ManifestoAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome')
    readonly_fields = ('id', 'data_creazione')
    summernote_fields = ['testo']

@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione')
    readonly_fields = ('id', 'data_creazione')
    summernote_fields = ['testo']

@admin.register(Oggetto)
class OggettoAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome', 'livello')
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    
    fieldsets = (
        ('Info', {'fields': ('nome', 'aura', 'testo', ('id', 'data_creazione', 'livello'))}),
        ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)})
    )
    
    inlines = [PunteggioOggettoInline, OggettoStatisticaBaseInline, OggettoStatisticaInline]
    exclude = ('elementi', 'statistiche', 'statistiche_base')
    summernote_fields = ['testo']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

class AttivataStatisticaBaseInline(StatisticaPivotInlineBase):
    model = AttivataStatisticaBase
    form = AttivataStatisticaBaseForm
    fk_name = 'attivata'
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'

class PunteggioAttivataInline(admin.TabularInline):
    model = Attivata.elementi.through
    extra = 1
    verbose_name = "Elemento"

@admin.register(Attivata)
class AttivataAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome')
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    inlines = [AttivataStatisticaBaseInline, PunteggioAttivataInline]
    exclude = ('statistiche_base', 'elementi')
    summernote_fields = ['testo']
    
    fieldsets = (
        ('Info', {'fields': ('nome', 'testo', ('id', 'data_creazione', 'livello'))}),
        ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)})
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))

# --- INFUSIONE & TESSITURA ---

class InfusioneStatisticaInline(StatisticaCondizionaleInlineBase):
    model = InfusioneStatistica
    fk_name = 'infusione'
    value_field = 'valore'
    default_field = 'valore_predefinito'

class TessituraStatisticaInline(StatisticaCondizionaleInlineBase):
    model = TessituraStatistica
    fk_name = 'tessitura'
    value_field = 'valore'
    default_field = 'valore_predefinito'

class InfusioneStatisticaBaseInline(StatisticaPivotInlineBase):
    model = InfusioneStatisticaBase
    fk_name = 'infusione'
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'

class TessituraStatisticaBaseInline(StatisticaPivotInlineBase):
    model = TessituraStatisticaBase
    fk_name = 'tessitura'
    value_field = 'valore_base'
    default_field = 'valore_base_predefinito'

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
    inlines = [InfusioneMattoneInline, InfusioneStatisticaBaseInline, InfusioneStatisticaInline]
    exclude = ('statistiche_base', 'statistiche', 'mattoni')
    summernote_fields = ['testo']
    autocomplete_fields = ['aura_richiesta', 'aura_infusione']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))

@admin.register(Tessitura)
class TessituraAdmin(SModelAdmin):
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'elemento_principale')
    search_fields = ['nome']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    inlines = [TessituraMattoneInline, TessituraStatisticaBaseInline, TessituraStatisticaInline]
    exclude = ('statistiche_base', 'statistiche', 'mattoni')
    summernote_fields = ['testo', 'formula']
    autocomplete_fields = ['aura_richiesta', 'elemento_principale']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        if 'formula' in form.base_fields:
            form.base_fields['formula'].help_text += " Supporta {elem}, {rango}."
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))

class PersonaggioInfusioneInline(admin.TabularInline):
    model = PersonaggioInfusione
    extra = 1
    verbose_name = "Infusione Posseduta"
    autocomplete_fields = ['infusione']

class PersonaggioTessituraInline(admin.TabularInline):
    model = PersonaggioTessitura
    extra = 1
    verbose_name = "Tessitura Posseduta"
    autocomplete_fields = ['tessitura']


@admin.register(Personaggio)
class PersonaggioAdmin(A_Admin):
    list_display = ('nome', 'proprietario', 'tipologia', 'crediti', 'punti_caratteristica')
    readonly_fields = ('id', 'data_creazione', 'crediti', 'punti_caratteristica')
    list_filter = ('tipologia',)
    search_fields = ('nome', 'proprietario__username')
    summernote_fields = ('testo',)
    inlines = [PersonaggioModelloAuraInline, PersonaggioInfusioneInline, PersonaggioTessituraInline, CreditoMovimentoInline, PuntiCaratteristicaMovimentoInline, PersonaggioLogInline]
    
    fieldsets = (
        ('Info', {'fields': ('nome', 'proprietario', 'tipologia', 'testo', ('data_nascita', 'data_morte'))}),
        ('Valori', {'classes': ('collapse',), 'fields': (('id', 'data_creazione'), ('crediti', 'punti_caratteristica'))})
    )

@admin.register(Gruppo)
class GruppoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'conteggio_membri')
    search_fields = ('nome',)
    filter_horizontal = ('membri',)
    
    def conteggio_membri(self, obj):
        return obj.membri.count()

@admin.register(Messaggio)
class MessaggioAdmin(SModelAdmin):
    list_display = ('titolo', 'tipo_messaggio', 'mittente', 'get_destinatario', 'data_invio')
    list_filter = ('tipo_messaggio', 'salva_in_cronologia', 'data_invio')
    search_fields = ('titolo', 'testo', 'mittente__username')
    date_hierarchy = 'data_invio'
    summernote_fields = ('testo',)
    autocomplete_fields = ['destinatario_personaggio', 'destinatario_gruppo']
    
    fieldsets = (
        ('Dettagli', {'fields': ('titolo', 'mittente', 'data_invio', 'salva_in_cronologia')}),
        ('Contenuto', {'fields': ('testo',)}),
        ('Destinazione', {'fields': ('tipo_messaggio', 'destinatario_personaggio', 'destinatario_gruppo')})
    )
    
    def get_destinatario(self, obj):
        if obj.tipo_messaggio == 'BROAD':
            return format_html("<b>TUTTI</b>")
        elif obj.tipo_messaggio == 'GROUP':
            return format_html(f"Gruppo: {obj.destinatario_gruppo}")
        return format_html(f"Pg: {obj.destinatario_personaggio}")
        
    def save_model(self, request, obj, form, change):
        if not obj.mittente:
            obj.mittente = request.user
        super().save_model(request, obj, form, change)