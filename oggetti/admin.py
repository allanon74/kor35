from django.contrib import admin
from django.utils.html import format_html
from .models import OggettoStatisticaBase, QrCode, Oggetto, Manifesto, OggettoStatistica, Attivata, AttivataStatisticaBase
from personaggi.models import Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica
from personaggi.admin import StatisticaPivotInlineBase
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin


# def get_statistica_base_help_text():
#     """
#     Funzione di test per forzare l'aggiornamento.
#     """
#     # Restituisce una stringa semplice senza database o try/except
#     return format_html("<b>Test di ricarica: Funziona!</b>") 

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
        variabili = [f"&bull; <b>{{{s.parametro}}}</b>: {s.nome}" for s in stats]
        
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
    readonly_fields = ('id', 'data_creazione','livello', 'TestoFormattato', ) 

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
    readonly_fields = ('id', 'data_creazione', 'livello', 'TestoFormattato', )
    inlines = [AttivataStatisticaBaseInline]
    exclude = ('statistiche_base',) 
    summernote_fields = ['testo', ]   


    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Imposta l'help_text per il campo 'testo' (che viene da A_vista)
        if 'testo' in form.base_fields:
            form.base_fields['testo'].help_text = get_statistica_base_help_text()
        return form