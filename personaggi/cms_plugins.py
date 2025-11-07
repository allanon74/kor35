# In /personaggi/cms_plugins.py

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import TabellaPluginModel, Tier, Abilita, Oggetto, Attivata, AbilitaPluginModel, TierPluginModel, OggettoPluginModel, AttivataPluginModel  

# --- 1. Plugin per i TIER (preso da cms_kor e adattato) ---

@plugin_pool.register_plugin
class TierPlugin(CMSPluginBase):
    model = TierPluginModel # Dobbiamo definire questo modello
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
    model = AbilitaPluginModel # Dobbiamo definire questo modello
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
    model = OggettoPluginModel # Dobbiamo definire questo modello
    name = _("Oggetto Plugin")
    render_template = "cms/plugins/oggetto.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['oggetto'] = instance.oggetto
        return context

# --- 4. Plugin per Attivata Singola ---

@plugin_pool.register_plugin
class AttivataPlugin(CMSPluginBase):
    model = AttivataPluginModel # Dobbiamo definire questo modello
    name = _("Attivata Plugin")
    render_template = "cms/plugins/attivata.html"
    cache = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['attivata'] = instance.attivata
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