from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import (
    TabellaPluginModel, Tier, Abilita, Oggetto, Attivata, 
    Infusione, Tessitura,
    AbilitaPluginModel, TierPluginModel, OggettoPluginModel, AttivataPluginModel,
    InfusionePluginModel, TessituraPluginModel
)  

# --- 1. Plugin per i TIER ---

@plugin_pool.register_plugin
class TierPlugin(CMSPluginBase):
    model = TierPluginModel
    name = _("Tier Plugin")
    render_template = "cms/plugins/tier.html"
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['tier'] = instance.tier
        context['abilita_del_tier'] = instance.tier.abilita_tier_set.all()
        return context

# --- 2. Plugin per Abilità Singola ---

@plugin_pool.register_plugin
class AbilitaPlugin(CMSPluginBase):
    model = AbilitaPluginModel
    name = _("Abilità Plugin")
    render_template = "cms/plugins/abilita.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['abilita'] = instance.abilita
        return context

# --- 3. Plugin per Oggetto Singolo ---

@plugin_pool.register_plugin
class OggettoPlugin(CMSPluginBase):
    model = OggettoPluginModel
    name = _("Oggetto Plugin")
    render_template = "cms/plugins/oggetto.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['oggetto'] = instance.oggetto
        return context

# --- 4. Plugin per Attivata Singola (Legacy) ---

@plugin_pool.register_plugin
class AttivataPlugin(CMSPluginBase):
    model = AttivataPluginModel
    name = _("Attivata Plugin")
    render_template = "cms/plugins/attivata.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['attivata'] = instance.attivata
        return context

# --- 5. Plugin per Infusione Singola (Nuovo) ---

@plugin_pool.register_plugin
class InfusionePlugin(CMSPluginBase):
    model = InfusionePluginModel
    name = _("Infusione Plugin")
    # Possiamo riutilizzare il template di attivata se la struttura HTML è simile
    # o crearne uno nuovo. Per sicurezza qui assumiamo l'uso di quello attivata o uno nuovo.
    render_template = "cms/plugins/attivata.html" 
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        # Passiamo 'attivata' al contesto perché il template attivata.html probabilmente usa {{ attivata.nome }}
        context['attivata'] = instance.infusione 
        return context

# --- 6. Plugin per Tessitura Singola (Nuovo) ---

@plugin_pool.register_plugin
class TessituraPlugin(CMSPluginBase):
    model = TessituraPluginModel
    name = _("Tessitura Plugin")
    render_template = "cms/plugins/attivata.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['attivata'] = instance.tessitura
        return context
    
#@plugin_pool.register_plugin
class TabellaPluginPublisher(CMSPluginBase):
    model = TabellaPluginModel
    module = "Kor"
    name = "Plugin Tabella"
    render_template = "cms/plugins/PI_tabella.html"
    
    def render(self, context, instance, placeholder):
        context.update({"instance": instance})
        return context

plugin_pool.register_plugin(TabellaPluginPublisher)

@plugin_pool.register_plugin
class TierPluginPublisher(CMSPluginBase):
    model = TierPluginModel
    module = "Kor"
    name = "Plugin Tier"
    render_template = "cms/plugins/PI_tier.html"

    def render(self, context, instance, placeholder):
        context.update({"instance": instance})
        return context