from django.contrib import admin

from .models import TabellaPluginModel, TierPluginModel


@admin.register(TabellaPluginModel)
class TabellaPluginModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'tabella')
    search_fields = ('tabella__nome',)
    autocomplete_fields = ('tabella',)
    ordering = ('tabella__nome',)


@admin.register(TierPluginModel)
class TierPluginModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'tier')
    list_filter = ('tier__tipo',)
    search_fields = ('tier__nome', 'tier__descrizione')
    autocomplete_fields = ('tier',)
    ordering = ('tier__nome',)
