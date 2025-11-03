from django.contrib import admin
from .models import QrCode, Oggetto, Manifesto
from personaggi.models import Punteggio, punteggi_tipo, AURA, ELEMENTO


class PunteggioOggettoInline(admin.TabularInline):
    model = Oggetto.elementi.through
    extra = 1





@admin.register(Manifesto)
class ManifestoAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione', 'titolo', 'autore')
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
    filter_vertical = [Oggetto.elementi.through]
    
    
