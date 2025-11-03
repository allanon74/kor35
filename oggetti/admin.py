from django.contrib import admin
from .models import QrCode, Oggetto, Manifesto
from personaggi.models import Punteggio, punteggi_tipo, AURA, ELEMENTO


class PunteggioOggettoInline(admin.TabularInline):
    # Questo ora punta correttamente al modello 'OggettoElemento'
    model = Oggetto.elementi.through 
    extra = 1
    # Aggiungiamo verbose_name per chiarezza nell'admin
    verbose_name = "Elemento"
    verbose_name_plural = "Elementi dell'Oggetto"




@admin.register(Manifesto)
class ManifestoAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione', 'nome', 'autore')
    readonly_fields = ('id', 'data_creazione',)

@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione',)
    readonly_fields = ('id', 'data_creazione',) 
    
@admin.register(Oggetto)
class OggettoAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'data_creazione', 'nome', 'livello')
    readonly_fields = ('id', 'data_creazione','livello',) 

    inlines = [PunteggioOggettoInline]
    # filter_vertical = [Oggetto.elementi.through]
    exclude = ('elementi',)
    
    
