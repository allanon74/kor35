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
    Infusione, Tessitura, InfusioneMattone, TessituraMattone,
    InfusioneStatisticaBase, TessituraStatisticaBase,
    PersonaggioInfusione, PersonaggioTessitura, PersonaggioModelloAura,
    PersonaggioAttivata,
    InfusionePluginModel, TessituraPluginModel,
    Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica, 
    PuntiCaratteristicaMovimento, STATISTICA,
    Tabella, Tier, Abilita, Mattone, 
    Caratteristica, Aura, ModelloAura, MattoneStatistica, 
    Messaggio, Gruppo,
    abilita_tier, abilita_punteggio, abilita_requisito, abilita_sbloccata, 
    abilita_prerequisito, AbilitaStatistica, CaratteristicaModificatore,
    TransazioneSospesa, STATO_TRANSAZIONE_CHOICES, STATO_TRANSAZIONE_IN_ATTESA, 
    STATO_TRANSAZIONE_ACCETTATA, STATO_TRANSAZIONE_RIFIUTATA
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

# --- Forms per evidenziare i valori modificati ---

def create_stat_form(model_class, field_valore, field_default_stat):
    class StatForm(forms.ModelForm):
        class Meta: model = model_class; fields = '__all__'
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.instance.pk and self.instance.statistica:
                default = getattr(self.instance.statistica, field_default_stat, 0)
                current = getattr(self.instance, field_valore, 0)
                if current != default:
                    for f in self.fields: 
                        if f == field_valore:
                            self.fields[f].widget.attrs['style'] = HIGHLIGHT_STYLE
    return StatForm

AbilitaStatisticaForm = create_stat_form(AbilitaStatistica, 'valore', 'valore_predefinito')
MattoneStatisticaForm = create_stat_form(MattoneStatistica, 'valore', 'valore_predefinito')
OggettoStatisticaForm = create_stat_form(OggettoStatistica, 'valore', 'valore_predefinito')

OggettoStatisticaBaseForm = create_stat_form(OggettoStatisticaBase, 'valore_base', 'valore_base_predefinito')
InfusioneStatisticaBaseForm = create_stat_form(InfusioneStatisticaBase, 'valore_base', 'valore_base_predefinito')
TessituraStatisticaBaseForm = create_stat_form(TessituraStatisticaBase, 'valore_base', 'valore_base_predefinito')
AttivataStatisticaBaseForm = create_stat_form(AttivataStatisticaBase, 'valore_base', 'valore_base_predefinito')


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

class IconaAdminMixin:
    def icona_html(self, obj): return obj.icona_html
    icona_html.short_description = "Icona"; icona_html.allow_tags = True
    def icona_cerchio_html(self, obj): return obj.icona_cerchio_html
    icona_cerchio_html.short_description = "Cerchio"; icona_cerchio_html.allow_tags = True
    def icona_cerchio_inverted_html(self, obj): return obj.icona_cerchio_inverted_html
    icona_cerchio_inverted_html.short_description = "Cerchio Inv."; icona_cerchio_inverted_html.allow_tags = True

# ----------- CLASSI INLINE -------------

class CaratteristicaModificatoreInline(admin.TabularInline):
    model = CaratteristicaModificatore; fk_name = "caratteristica"; extra = 1
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "statistica_modificata": kwargs["queryset"] = Statistica.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class abilita_tier_inline(A_Multi_Inline): model = abilita_tier
class abilita_punteggio_inline(A_Multi_Inline):
    model = abilita_punteggio; extra = 1; verbose_name_plural = "Punteggi Assegnati"
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "punteggio": kwargs["queryset"] = Punteggio.objects.exclude(tipo=STATISTICA)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
class abilita_requisito_inline(A_Multi_Inline): model = abilita_requisito
class abilita_sbloccata_inline(A_Multi_Inline): model = abilita_sbloccata    
class abilita_prerequisiti_inline(A_Multi_Inline):
    model = abilita_prerequisito; fk_name= "abilita"; autocomplete_fields=['prerequisito']
class abilita_abilitati_inline(A_Multi_Inline):
    model = abilita_prerequisito; fk_name= "prerequisito"; autocomplete_fields=['abilita']

# PIVOT LOGIC & VISUALIZZAZIONE

class StatisticaPivotMixin:
    readonly_fields = ('statistica_label',) 
    extra = 0
    
    # Da sovrascrivere nelle sottoclassi
    value_field = 'valore' 
    default_source_field = 'valore_predefinito'

    def statistica_label(self, obj):
        if not obj or not obj.statistica: return "-"
        label_html = format_html('<span style="font-size: 15px; font-weight: 800; color: #2c3e50;">{}</span>', obj.statistica.nome)
        css_hide = mark_safe('<style>.inline-related h3 { display: none !important; } .inline-related { border: 1px solid #eee !important; margin-bottom: 5px !important; padding-top: 10px !important; }</style>')
        return label_html + css_hide
    statistica_label.short_description = "Statistica"

    def has_delete_permission(self, request, obj=None): return False 
    def get_max_num(self, request, obj=None, **kwargs): return Statistica.objects.count()

    def get_formset(self, request, obj=None, **kwargs):
        if obj is not None: 
            fk_name = self.fk_name
            all_stats = Statistica.objects.all()
            existing_ids = self.model.objects.filter(**{fk_name: obj}).values_list('statistica_id', flat=True)
            missing_stats = all_stats.exclude(pk__in=existing_ids)
            new_objs = []
            for stat in missing_stats:
                default_val = getattr(stat, self.default_source_field, 0)
                kwargs_init = { fk_name: obj, 'statistica': stat, self.value_field: default_val }
                new_objs.append(self.model(**kwargs_init))
            if new_objs: self.model.objects.bulk_create(new_objs)
        return super().get_formset(request, obj, **kwargs)
    class Media: css = {'all': ('admin/css/nascondi-inline-header.css',)}

# 1. PIVOT BASE (Tabular)
class StatisticaBasePivotInline(StatisticaPivotMixin, admin.TabularInline):
    verbose_name = "Statistica (Valore Base)"
    verbose_name_plural = "Statistiche (Valori Base)"
    value_field = 'valore_base'
    default_source_field = 'valore_base_predefinito'
    def get_fields(self, request, obj=None): return ('statistica_label', self.value_field)

# 2. PIVOT MODIFICATORE (Stacked, Condizionale)
class StatisticaModificatorePivotInline(StatisticaPivotMixin, admin.StackedInline):
    verbose_name = "Statistica (Modificatore)"
    verbose_name_plural = "Statistiche (Modificatori)"
    value_field = 'valore'
    default_source_field = 'valore_predefinito'
    filter_horizontal = ('limit_a_aure', 'limit_a_elementi') 
    fieldsets = (
        (None, {'fields': (('statistica_label', 'valore', 'tipo_modificatore'),)}),
        ('Condizioni di Applicazione', {
            'classes': ('collapse',),
            'fields': (
                ('usa_limitazione_aura', 'limit_a_aure'), 
                ('usa_limitazione_elemento', 'limit_a_elementi'),
                ('usa_condizione_text', 'condizione_text')
            ),
            'description': "Se i flag sono attivi, il modificatore si applicherà SOLO se la condizione è soddisfatta."
        }),
    )

# --- IMPLEMENTAZIONI INLINE ---

class AbilitaStatisticaInline(StatisticaModificatorePivotInline):
    model = AbilitaStatistica; form = AbilitaStatisticaForm; fk_name = 'abilita'

class MattoneStatisticaInline(StatisticaModificatorePivotInline):
    model = MattoneStatistica; form = MattoneStatisticaForm; fk_name = 'mattone'

class MattoneInlineForAura(admin.TabularInline):
    model = Mattone; fk_name = 'aura'; extra = 1; fields = ('nome', 'caratteristica_associata', 'funzionamento_metatalento'); show_change_link = True

class OggettoStatisticaBaseInline(StatisticaBasePivotInline):
    model = OggettoStatisticaBase; form = OggettoStatisticaBaseForm; fk_name = 'oggetto'

class OggettoStatisticaInline(StatisticaModificatorePivotInline):
    model = OggettoStatistica; form = OggettoStatisticaForm; fk_name = 'oggetto'

class InfusioneStatisticaBaseInline(StatisticaBasePivotInline):
    model = InfusioneStatisticaBase; form = InfusioneStatisticaBaseForm; fk_name = 'infusione'

class TessituraStatisticaBaseInline(StatisticaBasePivotInline):
    model = TessituraStatisticaBase; form = TessituraStatisticaBaseForm; fk_name = 'tessitura'

class AttivataStatisticaBaseInline(StatisticaBasePivotInline):
    model = AttivataStatisticaBase; form = AttivataStatisticaBaseForm; fk_name = 'attivata'


# --- ALTRE INLINE ---

class CreditoMovimentoInline(admin.TabularInline):
    model = CreditoMovimento; extra = 1; fields = ('importo', 'descrizione', 'data'); readonly_fields = ('data',)
class PuntiCaratteristicaMovimentoInline(admin.TabularInline):
    model = PuntiCaratteristicaMovimento; extra = 1; fields = ('importo', 'descrizione', 'data'); readonly_fields = ('data',)
class PersonaggioLogInline(admin.TabularInline):
    model = PersonaggioLog; extra = 0; fields = ('testo_log', 'data'); readonly_fields = ('data',)
class PersonaggioModelloAuraInline(admin.TabularInline):
    model = PersonaggioModelloAura; extra = 1; verbose_name = "Modello Aura Applicato"

class PersonaggioInfusioneInline(admin.TabularInline):
    model = PersonaggioInfusione; extra = 1; autocomplete_fields = ['infusione']
class PersonaggioTessituraInline(admin.TabularInline):
    model = PersonaggioTessitura; extra = 1; autocomplete_fields = ['tessitura']
    
class PersonaggioAttivataInline(admin.TabularInline):
    model = PersonaggioAttivata; extra = 1; verbose_name = "Attivata (Legacy)"

class PunteggioOggettoInline(admin.TabularInline):
    model = Oggetto.elementi.through; extra = 1; verbose_name_plural = "Elementi dell'Oggetto"
class InfusioneMattoneInline(admin.TabularInline):
    model = InfusioneMattone; extra = 1; autocomplete_fields = ['mattone']; ordering = ['ordine']
class TessituraMattoneInline(admin.TabularInline):
    model = TessituraMattone; extra = 1; autocomplete_fields = ['mattone']; ordering = ['ordine']
class PunteggioAttivataInline(admin.TabularInline):
    model = Attivata.elementi.through; extra = 1; verbose_name = "Elemento"


# Helpers Testo
def get_statistica_base_help_text():
    return Statistica.get_help_text_parametri()
def get_mattone_help_text():
    extras = [('{caratt}', 'Valore Caratteristica'), ('{3*caratt}', 'Moltiplicatore (es. 3x)')]
    return Statistica.get_help_text_parametri(extras)


# --- MODEL ADMINS ---

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
    save_as = True; exclude = ('statistiche',)

@admin.register(Punteggio)
class PunteggioAdmin(IconaAdminMixin, A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome','icona_html', 'tipo', 'ordine', 'colore')
    list_filter = ('tipo',); list_editable = ('ordine','tipo'); search_fields = ('nome',); summernote_fields = ('descrizione',)
    save_as = True
    def get_queryset(self, request): return super().get_queryset(request).exclude(tipo=CARATTERISTICA).exclude(tipo='MA')

@admin.register(Caratteristica)
class CaratteristicaAdmin(IconaAdminMixin, A_Admin): 
    form = PunteggioAdminForm
    list_display = ('nome', 'sigla', 'icona_html', 'ordine', 'colore')
    list_editable = ('ordine',); search_fields = ('nome', 'sigla'); summernote_fields = ('descrizione',) 
    inlines = [CaratteristicaModificatoreInline]
    def get_queryset(self, request): return super().get_queryset(request).filter(tipo=CARATTERISTICA)
    def get_exclude(self, request, obj=None): return ('tipo', 'descrizione',)

@admin.register(Aura)
class AuraAdmin(IconaAdminMixin, A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'sigla', 'icona_html', 'ordine', 'is_soprannaturale', 'is_generica')
    list_editable = ('ordine', 'is_soprannaturale', 'is_generica'); search_fields = ('nome',); summernote_fields = ('descrizione',)
    inlines = [MattoneInlineForAura]
    def get_queryset(self, request): return super().get_queryset(request).filter(tipo=AURA)
    def get_exclude(self, request, obj=None): return ('tipo', 'descrizione', 'caratteristica_relativa')

@admin.register(ModelloAura)
class ModelloAuraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'aura')
    list_filter = ('aura',)
    filter_horizontal = ('mattoni_proibiti', 'mattoni_obbligatori',)

@admin.register(Mattone)
class MattoneAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'aura', 'tipo', 'caratteristica_associata','ordine', )
    list_editable = ('tipo', 'ordine',)
    list_filter = ('aura', 'caratteristica_associata'); search_fields = ('nome',); summernote_fields = ('descrizione_mattone', 'descrizione_metatalento', 'testo_addizionale')
    inlines = [MattoneStatisticaInline]
    
    fieldsets = (
        ('Dati Mattone', {'fields': ('nome', 'aura', 'tipo', 'ordine', 'caratteristica_associata', 'descrizione_mattone', 'icona', 'colore', 'dichiarazione')}),
        ('Metatalento', {'fields': ('funzionamento_metatalento', 'descrizione_metatalento', 'testo_addizionale')}),
        ('Sistema', {'fields': ('sigla',), 'classes': ('collapse',)})
    )
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo_addizionale' in form.base_fields: form.base_fields['testo_addizionale'].help_text = get_mattone_help_text()
        return form
    def get_exclude(self, request, obj=None): return ('descrizione', 'caratteristica_relativa')

@admin.register(Tier)
class TierAdmin(A_Admin):
    list_display = ['nome', 'descrizione']; summernote_fields = ["descrizione"]; inlines = [abilita_tier_inline]; save_as = True

@admin.register(Statistica)
class StatisticaAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'parametro', 'is_primaria', 'valore_predefinito', 'valore_base_predefinito', 'tipo_modificatore')
    list_editable = ('is_primaria',); exclude = ('tipo',); summernote_fields = ('descrizione',)

admin.site.register(Tabella)
admin.site.register(abilita_tier)
admin.site.register(abilita_punteggio)
admin.site.register(abilita_requisito)
admin.site.register(abilita_sbloccata)
admin.site.register(abilita_prerequisito)

@admin.register(Manifesto)
class ManifestoAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome'); readonly_fields = ('id', 'data_creazione'); summernote_fields = ['testo']

@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione'); readonly_fields = ('id', 'data_creazione'); summernote_fields = ['testo']

@admin.register(Oggetto)
class OggettoAdmin(SModelAdmin):
    list_display = ('id', 'data_creazione', 'nome', 'livello'); readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    fieldsets = (
        ('Info', {'fields': ('nome', 'aura', 'testo', ('id', 'data_creazione', 'livello'))}),
        ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)})
    )
    # OGGETTO HA ENTRAMBE
    inlines = [PunteggioOggettoInline, OggettoStatisticaBaseInline, OggettoStatisticaInline]
    exclude = ('elementi', 'statistiche', 'statistiche_base'); summernote_fields = ['testo']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = Statistica.get_help_text_parametri()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'

@admin.register(Attivata)
class AttivataAdmin(SModelAdmin):
    # LEGACY
    list_display = ('id', 'data_creazione', 'nome'); readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    inlines = [AttivataStatisticaBaseInline, PunteggioAttivataInline]
    exclude = ('statistiche_base', 'elementi'); summernote_fields = ['testo']
    fieldsets = (('Info', {'fields': ('nome', 'testo', ('id', 'data_creazione', 'livello'))}), ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)}))
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
             form.base_fields['testo'].help_text = Statistica.get_help_text_parametri()
        return form
    def mostra_testo_formattato(self, obj): return format_html("{}", mark_safe(obj.TestoFormattato))

@admin.register(Infusione)
class InfusioneAdmin(SModelAdmin):
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'aura_infusione'); search_fields = ['nome']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    # SOLO BASE
    inlines = [InfusioneMattoneInline, InfusioneStatisticaBaseInline]
    exclude = ('statistiche_base', 'statistiche', 'mattoni'); summernote_fields = ['testo']; autocomplete_fields = ['aura_richiesta', 'aura_infusione']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields:
             form.base_fields['testo'].help_text = Statistica.get_help_text_parametri()
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

@admin.register(Tessitura)
class TessituraAdmin(SModelAdmin):
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'elemento_principale'); search_fields = ['nome']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    # SOLO BASE
    inlines = [TessituraMattoneInline, TessituraStatisticaBaseInline]
    exclude = ('statistiche_base', 'statistiche', 'mattoni'); summernote_fields = ['testo', 'formula']; autocomplete_fields = ['aura_richiesta', 'elemento_principale']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        extras = [('{elem}', 'Elemento Principale'), ('{rango}', 'Rango Tessitura')]
        help_txt = Statistica.get_help_text_parametri(extras)
        
        if 'testo' in form.base_fields: form.base_fields['testo'].help_text = help_txt
        if 'formula' in form.base_fields: form.base_fields['formula'].help_text = help_txt
        return form
    
    def mostra_testo_formattato(self, obj):
        return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

@admin.register(Personaggio)
class PersonaggioAdmin(A_Admin):
    list_display = ('nome', 'proprietario', 'tipologia', 'crediti', 'punti_caratteristica')
    readonly_fields = ('id', 'data_creazione', 'crediti', 'punti_caratteristica')
    list_filter = ('tipologia',); search_fields = ('nome', 'proprietario__username'); summernote_fields = ('testo',)
    inlines = [
        PersonaggioModelloAuraInline, 
        PersonaggioInfusioneInline, 
        PersonaggioTessituraInline, 
        PersonaggioAttivataInline, 
        CreditoMovimentoInline, 
        PuntiCaratteristicaMovimentoInline, 
        PersonaggioLogInline
    ]
    fieldsets = (('Info', {'fields': ('nome', 'proprietario', 'tipologia', 'testo', ('data_nascita', 'data_morte'))}),
                 ('Valori', {'classes': ('collapse',), 'fields': (('id', 'data_creazione'), ('crediti', 'punti_caratteristica'))}))

@admin.register(Gruppo)
class GruppoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'conteggio_membri'); search_fields = ('nome',); filter_horizontal = ('membri',)
    def conteggio_membri(self, obj): return obj.membri.count()

@admin.register(Messaggio)
class MessaggioAdmin(SModelAdmin):
    list_display = ('titolo', 'tipo_messaggio', 'mittente', 'get_destinatario', 'data_invio')
    list_filter = ('tipo_messaggio', 'salva_in_cronologia', 'data_invio'); search_fields = ('titolo', 'testo', 'mittente__username'); date_hierarchy = 'data_invio'; summernote_fields = ('testo',); autocomplete_fields = ['destinatario_personaggio', 'destinatario_gruppo']
    fieldsets = (('Dettagli', {'fields': ('titolo', 'mittente', 'data_invio', 'salva_in_cronologia')}), ('Contenuto', {'fields': ('testo',)}), ('Destinazione', {'fields': ('tipo_messaggio', 'destinatario_personaggio', 'destinatario_gruppo')}))
    def get_destinatario(self, obj):
        if obj.tipo_messaggio == 'BROAD': return format_html("<b>TUTTI</b>")
        elif obj.tipo_messaggio == 'GROUP': return format_html(f"Gruppo: {obj.destinatario_gruppo}")
        return format_html(f"Pg: {obj.destinatario_personaggio}")
    def save_model(self, request, obj, form, change):
        if not obj.mittente: obj.mittente = request.user
        super().save_model(request, obj, form, change)

@admin.register(TransazioneSospesa)
class TransazioneSospesaAdmin(admin.ModelAdmin):
    list_display = ('id', 'oggetto', 'mittente', 'richiedente', 'stato', 'data_richiesta')
    list_filter = ('stato', 'data_richiesta')
    search_fields = ('oggetto__nome', 'mittente__nome', 'richiedente__nome')