from django.contrib import admin
from django import forms
from django.forms import Media
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe 
from django.utils import timezone

# Import aggiornati dai models
from .models import (
    CARATTERISTICA, CreditoMovimento, OggettoStatisticaBase, Personaggio, 
    PersonaggioLog, QrCode, Oggetto, OggettoCaratteristica, 
    Manifesto, OggettoStatistica, 
    Attivata, AttivataStatisticaBase, TipologiaPersonaggio,
    Infusione, Tessitura, 
    # NUOVI MODELLI INTERMEDI
    InfusioneCaratteristica, TessituraCaratteristica,
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
    STATO_TRANSAZIONE_ACCETTATA, STATO_TRANSAZIONE_RIFIUTATA,
    ModelloAuraRequisitoDoppia, 
    ModelloAuraRequisitoCaratt,
    ModelloAuraRequisitoMattone,
    PropostaTecnica, 
    # NUOVO MODELLO INTERMEDIO PROPOSTA
    PropostaTecnicaCaratteristica,
    STATO_PROPOSTA_APPROVATA, STATO_PROPOSTA_IN_VALUTAZIONE, STATO_PROPOSTA_RIFIUTATA, STATO_PROPOSTA_BOZZA,
    TIPO_PROPOSTA_INFUSIONE, TIPO_PROPOSTA_TESSITURA,
    ClasseOggetto, ClasseOggettoLimiteMod,
    OggettoInInventario, Inventario,
    ForgiaturaInCorso,
    OggettoBase, OggettoStatisticaBase, OggettoBaseModificatore, OggettoBaseStatisticaBase, 
    RichiestaAssemblaggio, 
    InfusioneStatistica,
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
InfusioneStatisticaForm = create_stat_form(InfusioneStatistica, 'valore', 'valore_predefinito')


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

class InfusioneStatisticaInline(StatisticaModificatorePivotInline):
    model = InfusioneStatistica
    form = InfusioneStatisticaForm
    fk_name = 'infusione'
    verbose_name = "Modificatore Attivo (es. +1 Forza)"
    verbose_name_plural = "Modificatori Attivi"

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

# class PunteggioOggettoInline(admin.TabularInline):
#     model = Oggetto.elementi.through; extra = 1; verbose_name_plural = "Elementi dell'Oggetto"

# --- NUOVE INLINE PER CARATTERISTICHE (ex Mattoni) ---
class InfusioneCaratteristicaInline(admin.TabularInline):
    model = InfusioneCaratteristica
    extra = 1
    autocomplete_fields = ['caratteristica']
    verbose_name = "Componente (Caratteristica)"
    verbose_name_plural = "Componenti Richiesti"

class TessituraCaratteristicaInline(admin.TabularInline):
    model = TessituraCaratteristica
    extra = 1
    autocomplete_fields = ['caratteristica']
    verbose_name = "Componente (Caratteristica)"
    verbose_name_plural = "Componenti Richiesti"

class PunteggioAttivataInline(admin.TabularInline):
    model = Attivata.elementi.through; extra = 1; verbose_name = "Elemento"

class RequisitoDoppiaInline(admin.TabularInline):
    model = ModelloAuraRequisitoDoppia; extra = 1; verbose_name = "Condizione per Doppia Formula"; verbose_name_plural = "Condizioni per Doppia Formula"; autocomplete_fields = ['requisito']
    
class RequisitoMattoneInline(admin.TabularInline):
    model = ModelloAuraRequisitoMattone; extra = 1; verbose_name = "Condizione per F. Mattone"; verbose_name_plural = "Condizioni per F. Mattone"; autocomplete_fields = ['requisito']

class RequisitoCarattInline(admin.TabularInline):
    model = ModelloAuraRequisitoCaratt; extra = 1; verbose_name = "Condizione per F. Caratteristica"; verbose_name_plural = "Condizioni per F. Caratteristica"; autocomplete_fields = ['requisito']


# Helpers Testo
def get_statistica_base_help_text():
    return Statistica.get_help_text_parametri()
def get_mattone_help_text():
    extras = [('{caratt}', 'Valore Caratteristica'), ('{3*caratt}', 'Moltiplicatore (es. 3x)')]
    return Statistica.get_help_text_parametri(extras)

class PropostaCaratteristicaInline(admin.TabularInline):
    model = PropostaTecnicaCaratteristica
    extra = 0
    readonly_fields = ('caratteristica', 'valore')
    can_delete = False
    verbose_name = "Caratteristica Richiesta"
    def has_add_permission(self, request, obj=None): return False

class InfusioneCreationInline(admin.StackedInline):
    model = Infusione
    fields = ('nome', 'testo', 'formula_attacco', 'aura_richiesta', 'aura_infusione', )
    extra = 0
    verbose_name = "Crea Infusione da questa proposta"
    show_change_link = True

class TessituraCreationInline(admin.StackedInline):
    model = Tessitura
    fields = ('nome', 'testo', 'formula', 'aura_richiesta', 'elemento_principale',)
    extra = 0
    verbose_name = "Crea Tessitura da questa proposta"
    show_change_link = True

@admin.register(PropostaTecnica)
class PropostaTecnicaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'personaggio', 'stato', 'data_creazione',)
    list_filter = ('stato', 'tipo')
    inlines = [PropostaCaratteristicaInline, InfusioneCreationInline, TessituraCreationInline]
    readonly_fields = ('personaggio', 'componenti_text', 'costo_invio_pagato', 'data_invio')
    
    def componenti_text(self, obj):
        # CORREZIONE: Usa 'componenti' (related_name)
        return ", ".join([f"{c.caratteristica.nome} ({c.valore})" for c in obj.componenti.all()])
    componenti_text.short_description = "Componenti Richiesti"

    def get_inline_instances(self, request, obj=None):
        instances = super().get_inline_instances(request, obj)
        if not obj: return instances
        filtered_instances = []
        for inline in instances:
            if isinstance(inline, InfusioneCreationInline) and obj.tipo == TIPO_PROPOSTA_TESSITURA: continue
            if isinstance(inline, TessituraCreationInline) and obj.tipo == TIPO_PROPOSTA_INFUSIONE: continue
            filtered_instances.append(inline)
        return filtered_instances
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'stato' in form.changed_data and obj.stato in (STATO_PROPOSTA_RIFIUTATA, STATO_PROPOSTA_BOZZA):
            motivo = obj.note_staff if obj.note_staff else "Nessuna motivazione specifica fornita."
            Messaggio.objects.create(
                mittente=request.user,
                destinatario_personaggio=obj.personaggio,
                tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
                titolo=f"Esito Proposta: {obj.nome}",
                testo=f"La tua proposta '{obj.nome}' è stata valutata e RIFIUTATA.\n\nMOTIVAZIONE STAFF:\n{motivo}",
                salva_in_cronologia=True
            )
            obj.personaggio.aggiungi_log(f"Proposta '{obj.nome}' rifiutata dallo staff.")
    
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        tecnica_creata = None
        tipo_tecnica = None
        
        # Rimosso il try-except silenzioso per vedere eventuali errori
        if hasattr(obj, 'infusione_generata') and obj.infusione_generata:
            tecnica_creata = obj.infusione_generata; tipo_tecnica = 'infusione'
        elif hasattr(obj, 'tessitura_generata') and obj.tessitura_generata:
            tecnica_creata = obj.tessitura_generata; tipo_tecnica = 'tessitura'

        if tecnica_creata and obj.stato != STATO_PROPOSTA_APPROVATA:
            has_componenti = False
            # CORREZIONE: Usa 'componenti' (related_name), valido per entrambi
            has_componenti = tecnica_creata.componenti.exists()

            if not has_componenti:
                # CORREZIONE: Usa 'componenti' anche per la proposta
                componenti_proposta = obj.componenti.all()
                for cp in componenti_proposta:
                    if tipo_tecnica == 'infusione':
                        InfusioneCaratteristica.objects.create(
                            infusione=tecnica_creata, 
                            caratteristica=cp.caratteristica, 
                            valore=cp.valore
                        )
                    elif tipo_tecnica == 'tessitura':
                        TessituraCaratteristica.objects.create(
                            tessitura=tecnica_creata, 
                            caratteristica=cp.caratteristica, 
                            valore=cp.valore
                        )
                obj.note_staff = (obj.note_staff or "") + f"\n[System] Componenti copiati automaticamente su {tecnica_creata.nome}."

            obj.stato = STATO_PROPOSTA_APPROVATA
            if not obj.note_staff: obj.note_staff = f"Approvata automaticamente con la creazione di: {tecnica_creata.nome}"
            obj.save()
            
            # --- LOGICA PAGAMENTO ATTIVATA ---
            # Scala i crediti per la creazione (costo acquisto tecnica personale)
            costo = tecnica_creata.costo_crediti
            if costo > 0:
                obj.personaggio.modifica_crediti(-costo, f"Approvazione e creazione tecnica: {tecnica_creata.nome}")
                obj.personaggio.aggiungi_log(f"Ha speso {costo} CR per la creazione della tecnica '{tecnica_creata.nome}'.")
            # --------------------------------

            pg = obj.personaggio
            if tipo_tecnica == 'infusione':
                if not pg.infusioni_possedute.filter(id=tecnica_creata.id).exists():
                    PersonaggioInfusione.objects.create(personaggio=pg, infusione=tecnica_creata, data_acquisizione=timezone.now())
                    pg.aggiungi_log(f"Proposta accettata! Ha ottenuto l'infusione '{tecnica_creata.nome}'.")
            elif tipo_tecnica == 'tessitura':
                if not pg.tessiture_possedute.filter(id=tecnica_creata.id).exists():
                    PersonaggioTessitura.objects.create(personaggio=pg, tessitura=tecnica_creata, data_acquisizione=timezone.now())
                    pg.aggiungi_log(f"Proposta accettata! Ha ottenuto la tessitura '{tecnica_creata.nome}'.")

            Messaggio.objects.create(
                mittente=request.user,
                destinatario_personaggio=obj.personaggio,
                tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
                titolo=f"Esito Proposta: {obj.nome}",
                testo=f"La tua proposta '{obj.nome}' è stata valutata e ACCETTATA!\n\nHai ottenuto la tecnica '{tecnica_creata.nome}'.",
                salva_in_cronologia=True
            )
                    
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
    list_display = ('nome','icona_html', 'icona_cerchio_html','icona_cerchio_inverted_html', 'tipo', 'ordine', 'colore')
    list_filter = ('tipo',)
    list_editable = ('ordine','tipo')
    search_fields = ('nome',)
    summernote_fields = ('descrizione',)
    save_as = True
    
    fieldsets = (
        ('Dati Generali', {
            'fields': (('nome', 'sigla'), ('tipo', 'ordine'), ('icona', 'colore'), 'descrizione')
        }),
        ('Configurazione Aura (Solo se Tipo = Aura)', {
            'classes': ('collapse',),
            'description': "Definisci le statistiche da usare per calcolare costi e tempi. Se vuoto, usa i default (100cr / 60s).",
            'fields': (
                ('stat_costo_creazione_infusione', 'stat_costo_creazione_tessitura'),
                ('stat_costo_acquisto_infusione', 'stat_costo_acquisto_tessitura'),
                ('stat_costo_invio_proposta_infusione', 'stat_costo_invio_proposta_tessitura'),
                ('stat_costo_forgiatura', 'stat_tempo_forgiatura'),
                'aure_infusione_consentite'
            )
        }),
    )

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
    filter_horizontal = ('aure_infusione_consentite',)
    inlines = [MattoneInlineForAura]
    def get_queryset(self, request): return super().get_queryset(request).filter(tipo=AURA)
    def get_exclude(self, request, obj=None): return ('tipo', 'descrizione', 'caratteristica_relativa')

@admin.register(ModelloAura)
class ModelloAuraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'aura', 'usa_doppia_formula', 'usa_formula_per_caratteristica')
    list_filter = ('aura',)
    search_fields = ('nome',)
    filter_horizontal = ('mattoni_proibiti', 'mattoni_obbligatori')
    autocomplete_fields = ['aura', 'elemento_secondario']
    fieldsets = (
        (None, {'fields': ('nome', 'aura', 'descrizione',)}),
        ('Limitazioni Mattoni', {'fields': ('mattoni_proibiti', 'mattoni_obbligatori')}),
        ('Doppia Formula', {'fields': ('usa_doppia_formula', 'elemento_secondario', 'usa_condizione_doppia'), 'description': "Impostazioni per mostrare una seconda formula fissa.", 'classes': ('anchor-doppia',)}),
        ('Formula per Mattone', {'fields': ('usa_formula_per_mattone', 'usa_condizione_mattone'), 'description': "Formule dinamiche basate sugli elementi dei mattoni.", 'classes': ('anchor-mattone',)}),
        ('Formula per Caratteristica', {'fields': ('usa_formula_per_caratteristica', 'usa_condizione_caratt'), 'description': "Formule dinamiche basate sulle caratteristiche.", 'classes': ('anchor-caratt',)}),
    )
    inlines = [RequisitoDoppiaInline, RequisitoMattoneInline, RequisitoCarattInline]
    class Media:
        js = ('admin/js/move_inlines.js',); css = {'all': ('admin/css/nascondi-inline-header.css',)}

@admin.register(Mattone)
class MattoneAdmin(A_Admin):
    form = PunteggioAdminForm
    list_display = ('nome', 'aura', 'tipo', 'caratteristica_associata','ordine', )
    list_editable = ('tipo', 'ordine',)
    list_filter = ('aura', 'caratteristica_associata'); search_fields = ('nome',); summernote_fields = ('descrizione_mattone', 'descrizione_metatalento', 'testo_addizionale')
    inlines = [MattoneStatisticaInline]
    
    fieldsets = (
        ('Dati Mattone', {'fields': ('nome', 'aura', 'tipo', 'ordine', 'sigla', 'caratteristica_associata', 'descrizione_mattone', 'icona', 'colore', 'dichiarazione')}),
        ('Metatalento', {'fields': ('funzionamento_metatalento', 'descrizione_metatalento', 'testo_addizionale')}),
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
    list_editable = ('is_primaria',)
    exclude = ('tipo',)
    summernote_fields = ('descrizione',)
    search_fields = ['nome', 'parametro']

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

# @admin.register(Attivata)
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
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'aura_infusione', 'statistica_cariche')
    search_fields = ['nome', 'testo']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    
    # AGGIUNTO InfusioneStatisticaInline ALLA LISTA
    inlines = [
        InfusioneCaratteristicaInline,   # Componenti (Livello/Costo)
        InfusioneStatisticaBaseInline,   # Statistiche Base (Danno, Peso)
        InfusioneStatisticaInline        # Modificatori (Bonus/Malus)
    ]
    
    # Rimuovi 'statistiche' dagli esclusi per permettere la gestione inline corretta
    exclude = ('statistiche_base', 'caratteristiche', 'statistiche')
    
    summernote_fields = ['testo']
    autocomplete_fields = ['aura_richiesta', 'aura_infusione', 'statistica_cariche']
    
    fieldsets = (
        ('Dati Base', {'fields': ('nome', 'testo', 'formula_attacco', 'aura_richiesta', 'aura_infusione', 'proposta_creazione')}),
        ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)}),
        ('Configurazione Oggetto Generato', {
            'fields': ('slot_corpo_permessi',), 
            'description': "Definisci dove può essere installato l'oggetto (solo per Innesti/Mutazioni)."
        }),
        ('Logica Ricarica & Durata', {'fields': ('statistica_cariche', 'metodo_ricarica', 'costo_ricarica_crediti', 'durata_attivazione'), 'description': "Definisci qui come l'oggetto generato gestisce le cariche."}),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields: form.base_fields['testo'].help_text = Statistica.get_help_text_parametri()
        return form
    
    def mostra_testo_formattato(self, obj): return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

@admin.register(Tessitura)
class TessituraAdmin(SModelAdmin):
    list_display = ('id', 'nome', 'aura_richiesta', 'livello', 'elemento_principale'); search_fields = ['nome']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    # MODIFICA: Usiamo TessituraCaratteristicaInline
    inlines = [TessituraCaratteristicaInline, TessituraStatisticaBaseInline]
    exclude = ('statistiche_base', 'statistiche', 'caratteristiche'); summernote_fields = ['testo', 'formula']; autocomplete_fields = ['aura_richiesta', 'elemento_principale']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        extras = [('{elem}', 'Elemento Principale'), ('{liv}', 'Livello Tessitura'), ('aura}', 'Aura Richiesta')]
        help_txt = Statistica.get_help_text_parametri(extras)
        if 'testo' in form.base_fields: form.base_fields['testo'].help_text = help_txt
        if 'formula' in form.base_fields: form.base_fields['formula'].help_text = help_txt
        return form
    
    def mostra_testo_formattato(self, obj): return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo'

@admin.register(Personaggio)
class PersonaggioAdmin(A_Admin):
    list_display = ('nome', 'proprietario', 'tipologia', 'crediti', 'punti_caratteristica')
    readonly_fields = ('id', 'data_creazione', 'crediti', 'punti_caratteristica')
    list_filter = ('tipologia',); search_fields = ('nome', 'proprietario__username'); summernote_fields = ('testo',)
    inlines = [
        PersonaggioModelloAuraInline, PersonaggioInfusioneInline, PersonaggioTessituraInline, PersonaggioAttivataInline, 
        CreditoMovimentoInline, PuntiCaratteristicaMovimentoInline, PersonaggioLogInline
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
    
class ClasseOggettoLimiteModInline(admin.TabularInline):
    model = ClasseOggettoLimiteMod
    extra = 1
    autocomplete_fields = ['caratteristica']
    verbose_name = "Limite Mod per Caratteristica"
    verbose_name_plural = "Limiti Mod per Caratteristica"

@admin.register(ClasseOggetto)
class ClasseOggettoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'max_mod_totali', 'get_permessi_materia']
    search_fields = ['nome']
    inlines = [ClasseOggettoLimiteModInline]
    filter_horizontal = ['mattoni_materia_permessi']
    def get_permessi_materia(self, obj): return ", ".join([p.nome for p in obj.mattoni_materia_permessi.all()])
    get_permessi_materia.short_description = "Mattoni Materia Permessi"

# --- INLINES PER OGGETTO ---

# class OggettoElementoInline(admin.TabularInline):
#     model = OggettoElemento; extra = 1; autocomplete_fields = ['elemento']

class OggettoCaratteristicaInline(admin.TabularInline):
    model = OggettoCaratteristica
    extra = 0 # Non mostriamo righe vuote extra di default per pulizia
    autocomplete_fields = ['caratteristica']
    verbose_name = "Caratteristica (Mattone)"
    verbose_name_plural = "Caratteristiche (Mattoni)"

class PotenziamentiInstallatiInline(admin.TabularInline):
    model = Oggetto; fk_name = 'ospitato_su'
    fields = ['nome', 'tipo_oggetto', 'cariche_attuali', 'infusione_generatrice']
    readonly_fields = ['nome', 'tipo_oggetto', 'cariche_attuali', 'infusione_generatrice']
    extra = 0; can_delete = False; show_change_link = True
    verbose_name = "Potenziamento Installato"; verbose_name_plural = "Potenziamenti Installati (Mod/Materia)"

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'id']; search_fields = ['nome']
    def get_queryset(self, request): return super().get_queryset(request).select_related()

class TracciamentoInventarioInline(admin.TabularInline):
    model = OggettoInInventario; extra = 0; readonly_fields = ['data_inizio', 'data_fine']; raw_id_fields = ['inventario']; ordering = ['-data_inizio']

@admin.register(Oggetto)
class OggettoAdmin(SModelAdmin):
    list_display = ['nome', 'attacco_base', 'tipo_oggetto', 'classe_oggetto', 'is_tecnologico', 'livello', 'costo_acquisto', 'cariche_attuali', 'get_inventario_attuale', ]
    list_filter = ['tipo_oggetto', 'classe_oggetto', 'is_tecnologico', 'in_vendita', 'aura']
    list_editable =['attacco_base', ]
    search_fields = ['nome', 'testo']
    autocomplete_fields = ['aura', 'infusione_generatrice', 'ospitato_su', 'classe_oggetto']
    readonly_fields = ('livello', 'mostra_testo_formattato', 'id', 'data_creazione')
    summernote_fields = ['testo']
    
    fieldsets = (
        ('Dati Generali', {'fields': ('nome', 'testo', 'aura', 'costo_acquisto', 'in_vendita')}),
        ('Classificazione & Logica', {'fields': ('tipo_oggetto', 'classe_oggetto', 'is_tecnologico', 'slot_corpo', 'attacco_base')}),
        ('Anteprima', {'classes': ('wide',), 'fields': ('mostra_testo_formattato',)}),
        ('Stato & Origine', {'fields': ('cariche_attuali', 'infusione_generatrice', 'ospitato_su')}),
    )
    inlines = [
        OggettoCaratteristicaInline, 
        TracciamentoInventarioInline, 
        PotenziamentiInstallatiInline,
        OggettoStatisticaBaseInline, 
        OggettoStatisticaInline,  
        ]
    
    def get_inventario_attuale(self, obj):
        if obj.ospitato_su: return f"Montato su: {obj.ospitato_su.nome}"
        inv = obj.inventario_corrente
        return inv.nome if inv else "Nessuno (A terra)"
    get_inventario_attuale.short_description = "Posizione Attuale"
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'testo' in form.base_fields: form.base_fields['testo'].help_text = Statistica.get_help_text_parametri()
        return form
    
    def mostra_testo_formattato(self, obj): return format_html("{}", mark_safe(obj.TestoFormattato))
    mostra_testo_formattato.short_description = 'Anteprima Testo Formattato'

@admin.register(ForgiaturaInCorso)
class ForgiaturaInCorsoAdmin(admin.ModelAdmin):
    list_display = ('personaggio', 'infusione', 'data_inizio', 'data_fine_prevista', 'completata', 'is_pronta_display')
    list_filter = ('completata', 'data_fine_prevista')
    search_fields = ('personaggio__nome', 'infusione__nome')
    
    def is_pronta_display(self, obj): return obj.is_pronta
    is_pronta_display.boolean = True
    is_pronta_display.short_description = "Pronta?"
    
class OggettoBaseStatisticaBaseInline(admin.TabularInline):
    model = OggettoBaseStatisticaBase
    extra = 1
    autocomplete_fields = ['statistica']
    verbose_name = "Statistica Base (Es. Danno)"

class OggettoBaseModificatoreInline(admin.TabularInline):
    model = OggettoBaseModificatore
    extra = 1
    autocomplete_fields = ['statistica']
    verbose_name = "Modificatore (Es. Bonus)"

@admin.register(OggettoBase)
class OggettoBaseAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_oggetto', 'classe_oggetto', 'costo', 'in_vendita')
    list_filter = ('tipo_oggetto', 'is_tecnologico', 'in_vendita')
    search_fields = ('nome',)
    autocomplete_fields = ['classe_oggetto']
    
    fieldsets = (
        ('Info Generali', {
            'fields': ('nome', 'descrizione', 'costo', 'in_vendita')
        }),
        ('Scheda Tecnica', {
            'fields': ('tipo_oggetto', 'classe_oggetto', 'is_tecnologico', 'attacco_base')
        }),
    )
    
    inlines = [OggettoBaseStatisticaBaseInline, OggettoBaseModificatoreInline]
    
@admin.register(RichiestaAssemblaggio)
class RichiestaAssemblaggioAdmin(admin.ModelAdmin):
    list_display = ('id', 'committente', 'artigiano', 'oggetto_host', 'componente', 'stato', 'offerta_crediti', 'data_creazione')
    list_filter = ('stato', 'data_creazione')
    search_fields = ('committente__nome', 'artigiano__nome', 'oggetto_host__nome')
    autocomplete_fields = ['committente', 'artigiano', 'oggetto_host', 'componente']