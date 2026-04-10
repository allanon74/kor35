# In icon_widget/fields.py
from django.db import models
from .widgets import CustomIconWidget

class CustomIconField(models.CharField):
    
    def __init__(self, *args, **kwargs):
        # Impostiamo valori predefiniti per un CharField
        kwargs.setdefault('max_length', 255)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        # Dice a Django: "Quando crei un form per questo campo,
        # usa il nostro CustomIconWidget di default."
        kwargs.setdefault('widget', CustomIconWidget)
        return super().formfield(**kwargs)