from django.contrib import admin
from .models import QrCode, Oggetto, Manifesto, OggettoStatistica
from personaggi.models import Punteggio, punteggi_tipo, AURA, ELEMENTO
from personaggi.admin import StatisticaInlineAdminBase


class PunteggioOggettoInline(admin.TabularInline):
    # Questo ora punta correttamente al modello 'OggettoElemento'
    model = Oggetto.elementi.through 
    extra = 1
    # Aggiungiamo verbose_name per chiarezza nell'admin
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Oggetto"

class OggettoStatisticaInline(StatisticaInlineAdminBase):
    model = OggettoStatistica
    fk_name = 'oggetto' # Nome del FK nel modello "through"


@admin.register(Manifesto)
class ManifestoAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione', 'nome', )
    readonly_fields = ('id', 'data_creazione',)

@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione',)
    readonly_fields = ('id', 'data_creazione',) 
    
@admin.register(Oggetto)
class OggettoAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'data_creazione', 'nome', 'livello')
    readonly_fields = ('id', 'data_creazione','livello',) 

    inlines = [
        PunteggioOggettoInline, 
        OggettoStatisticaInline,
        ]
    # filter_vertical = [Oggetto.elementi.through]
    exclude = ('elementi', 'statistiche',)  # Escludi i campi ManyToMany originali  
    
    
