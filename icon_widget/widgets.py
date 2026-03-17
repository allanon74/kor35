# In icon_widget/widgets.py
from django import forms
from django.urls import reverse

class CustomIconWidget(forms.TextInput):
    template_name = 'admin/widgets/custom_icon_widget.html'

    def __init__(self, attrs=None):
        # Aggiungi il model_name qui
        default_attrs = {'model_name': 'personaggi.punteggio'} # Semplificazione
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        js = ('admin/js/custom_icon_picker.js',)
        css = {
            'all': ('admin/css/custom_icon_picker.css',)
        }

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Passa il model_name al template
        context['widget']['model_name'] = attrs.get('model_name', 'personaggi.punteggio')
        # URL dell'API (risolto via reverse, include eventuali prefissi come /api/)
        context['widget']['save_icon_url'] = reverse('icon_widget:save_icon')
        return context