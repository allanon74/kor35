from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from .models import TabellaPluginModel, TierPluginModel

from django.utils.translation import gettext as _

#@plugin_pool.register_plugin
class TabellaPluginPublisher(CMSPluginBase):
    model = TabellaPluginModel
    module = "Kor"
    name = "Plugin Tabella"
    render_template = "PI_tabella.html"
    
    def render(self, context, instance, placeholder):
        context.update({"instance": instance})
        return context

plugin_pool.register_plugin(TabellaPluginPublisher)

@plugin_pool.register_plugin
class TierPluginPublisher(CMSPluginBase):
    model = TierPluginModel
    module = "Kor"
    name = "Plugin Tier"
    render_template = "PI_tier.html"
    
    def render(self, context, instance, placeholder):
        context.update({"instance": instance})
        return context