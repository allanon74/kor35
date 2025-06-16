from django.db import models
from cms.models import CMSPlugin

from personaggi.models import Tabella, Tier

# Create your models here.

# Classi CMS Plugin

class TabellaPluginModel(CMSPlugin):
    tabella = models.ForeignKey(Tabella, on_delete = models.CASCADE)
    
    def __str__(self):
        return "{tabella}".format(tabella = self.tabella.nome)

class TierPluginModel(CMSPlugin):
    tier = models.ForeignKey(Tier, on_delete = models.CASCADE)
    
    def __str__(self):
        return "{tier}".format(tier = self.tier.nome)