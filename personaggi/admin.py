from django.contrib import admin

from django_summernote.admin import SummernoteModelAdmin as SModelAdmin
from django_summernote.admin import SummernoteInlineModelAdmin as SInlineModelAdmin

from .models import Tabella, Punteggio, Tier, Abilita, Spell, Mattone
from .models import abilita_tier, abilita_punteggio, abilita_requisito, abilita_sbloccata, spell_mattone, abilita_prerequisito

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
    	)
	save_as = True


class PunteggioAdmin(A_Admin):
	list_display = ('nome', 'tipo', 'caratteristica',)
	list_filter = ('tipo', 'caratteristica',)
	search_fields = ('nome', )

class AbilitaPrerequisitoAdmin(A_Admin):
	list_display = ('abilita', 'prerequisito', )
	search_fields = ['abilita__nome', 'prerequisito__nome', ]
	autocomplete_fields = ['abilita', 'prereeeeeequisito',]

class TierAdmin(A_Admin):
	list_display = ['nome', 'descrizione', ]
	summernote_fields = ["descrizione",]
	inlines = [abilita_tier_inline, ]
	save_as = True

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
