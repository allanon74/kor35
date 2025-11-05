from django.contrib import admin
from .models import OggettoStatisticaBase, QrCode, Oggetto, Manifesto, OggettoStatistica, Attivata, AttivataStatisticaBase
from personaggi.models import Punteggio, punteggi_tipo, AURA, ELEMENTO
from personaggi.admin import StatisticaPivotInlineBase
from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin


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
    readonly_fields = ('id', 'data_creazione','livello',) 

    inlines = [
        PunteggioOggettoInline, 
        OggettoStatisticaInline,
        OggettoStatisticaBaseInline,
        ]
    # filter_vertical = [Oggetto.elementi.through]
    exclude = ('elementi', 'statistiche', 'statistiche_base')  # Escludi i campi ManyToMany originali  
    summernote_fields = ['testo', ]
    
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
    readonly_fields = ('id', 'data_creazione',)
    inlines = [AttivataStatisticaBaseInline]
    exclude = ('statistiche_base',) 
    summernote_fields = ['testo', ]   
