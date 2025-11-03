from django.contrib import admin

from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin

from .models import Tabella, Punteggio, Tier, Abilita, Spell, Mattone, Statistica
from .models import abilita_tier, abilita_punteggio, abilita_requisito, abilita_sbloccata, spell_mattone, abilita_prerequisito, AbilitaStatistica

# ----------- CLASSI ASTRATTE -------------

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
class abilita_tier_inline(A_Multi_Inline):
	model = abilita_tier
	
class abilita_punteggio_inline(A_Multi_Inline):
	model = abilita_punteggio
	
class abilita_requisito_inline(A_Multi_Inline):
	model = abilita_requisito
	
class abilita_sbloccata_inline(A_Multi_Inline):
	model = abilita_sbloccata	
	
class spell_mattone_inline(A_Multi_Inline):
	model = spell_mattone

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

class StatisticaInlineAdminBase(admin.TabularInline):
    """
    Inline personalizzato che mostra TUTTE le statistiche disponibili,
    pre-popolando i valori di default per quelle non ancora impostate.
    """
    # Il campo 'statistica' non deve essere modificabile
    # readonly_fields = ('statistica_nome',)
    fields = ('statistica', 'valore')
    readonly_fields = ('statistica',)
    # Quanti form "extra" mostrare (sarà sovrascritto)
    # extra = 0 
    
    # def statistica_nome(self, instance):
    #     # Mostra il nome della statistica come testo
    #     if instance.pk:
    #         return instance.statistica.nome
    #     return "---" # In caso di errore
    # statistica_nome.short_description = "Statistica"
    
    def get_max_num(self, request, obj=None, **kwargs):
        """
        Imposta il numero totale di form consentiti pari al numero
        di statistiche totali. Questo nasconde il link "Aggiungi un altro..."
        una volta che tutte le statistiche sono visualizzate.
        """
        return Statistica.objects.count()
        
    def get_formset(self, request, obj=None, **kwargs):
        """
        Questo è il cuore della logica.
        Quando si modifica un oggetto (obj is not None),
        crea al volo le istanze "through" mancanti.
        """
        
        # --- IMPLEMENTAZIONE DELLA TUA IDEA (PRE-SAVE) ---
        if obj is not None: # Esegui solo in modalità "Modifica"
            
            # 1. Trova il nome del campo FK (es. 'abilita' o 'oggetto')
            fk_name = self.fk_name
            
            # 2. Prendi tutte le statistiche
            all_stats = Statistica.objects.all()
            
            # 3. Trova le statistiche GIÀ collegate a questo oggetto
            existing_stat_pks = self.model.objects.filter(
                **{fk_name: obj}
            ).values_list('statistica_id', flat=True)

            # 4. Trova le statistiche NON ancora collegate
            missing_stats = all_stats.exclude(pk__in=existing_stat_pks)
            
            # 5. Prepara le nuove istanze da creare
            new_instances_to_create = []
            for stat in missing_stats:
                # Crea le nuove istanze "through" con il valore predefinito
                new_instances_to_create.append(
                    self.model(
                        **{fk_name: obj},
                        statistica=stat,
                        valore=stat.valore_predefinito
                    )
                )
            
            # 6. Salva tutte le nuove istanze in un'unica query
            if new_instances_to_create:
                self.model.objects.bulk_create(new_instances_to_create)
        
        # --- FINE BLOCCO PRE-SAVE ---

        # Ora chiama il get_formset() standard.
        # Troverà automaticamente i record che abbiamo appena creato.
        return super().get_formset(request, obj, **kwargs)

    # def has_add_permission(self, request, obj=None):
    #     # Vogliamo solo modificare i valori, non aggiungere/rimuovere righe
    #     return False # Permetti di aggiungere le righe mancanti

    # def has_delete_permission(self, request, obj=None):
    #     # Impedisce all'utente di cancellare una riga di statistica
    #     return False
        
    # def get_readonly_fields(self, request, obj=None):
    #     # Se l'oggetto esiste, rendi 'statistica' readonly
    #     if obj:
    #         return ('statistica',) + self.readonly_fields
    #     return self.readonly_fields

class AbilitaStatisticaInline(StatisticaInlineAdminBase):
    model = AbilitaStatistica
    fk_name = 'abilita' # Nome del FK nel modello "through"
    
# ----------- CLASSI ADMIN -------------

class SpellAdmin(A_Admin):
	list_display = (
		'id', 
		'nome', 
		#'livello',
		)
	inlines = (spell_mattone_inline, )
	
class AbilitaAdmin(A_Admin):
	list_display = ('id', 'nome', )
	summernote_fields = ['descrizione', ]
	search_fields = ['nome', 'descrizione',]
	inlines = (
    	abilita_tier_inline, 
    	abilita_punteggio_inline, 
    	abilita_requisito_inline, 
    	abilita_sbloccata_inline, 
		abilita_prerequisiti_inline,
		abilita_abilitati_inline,
		AbilitaStatisticaInline,
    	)
	save_as = True
	exclude = ('statistiche',)

class PunteggioAdmin(A_Admin):
	list_display = ('nome', 'tipo', 'caratteristica',)
	list_filter = ('tipo', 'caratteristica',)
	search_fields = ('nome', )

class AbilitaPrerequisitoAdmin(A_Admin):
	list_display = ('abilita', 'prerequisito', )
	search_fields = ['abilita__nome', 'prerequisito__nome', ]
	autocomplete_fields = ['abilita', 'prerequisito',]

class TierAdmin(A_Admin):
	list_display = ['nome', 'descrizione', ]
	summernote_fields = ["descrizione",]
	inlines = [abilita_tier_inline, ]
	save_as = True

@admin.register(Statistica)
class StatisticaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valore_predefinito', 'tipo_modificatore')
    # Questo eredita i campi di Punteggio, potresti doverli nascondere
    exclude = ('tipo',) # Nasconde il campo 'tipo' che forziamo a 'ST'

# Register your models here.

admin.site.register(Tabella)
admin.site.register(Abilita, AbilitaAdmin)
admin.site.register(Tier, TierAdmin)
admin.site.register(Spell, SpellAdmin)
admin.site.register(Punteggio, PunteggioAdmin)
admin.site.register(abilita_tier)
admin.site.register(abilita_punteggio)
admin.site.register(abilita_requisito)
admin.site.register(abilita_sbloccata)
admin.site.register(Mattone)
admin.site.register(abilita_prerequisito, AbilitaPrerequisitoAdmin)
