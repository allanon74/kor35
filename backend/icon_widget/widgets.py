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
        safe_attrs = attrs or {}
        input_id = safe_attrs.get('id', '')
        # Passa il model_name al template
        context['widget']['model_name'] = safe_attrs.get('model_name', 'personaggi.punteggio')
        # URL dell'API (risolto via reverse, include eventuali prefissi come /api/)
        context['widget']['save_icon_url'] = reverse('icon_widget:save_icon')
        # Campo hidden opzionale dove salvare il nome icona originale (es: id_icona_nome_originale)
        context['widget']['icon_name_input_id'] = f"{input_id}_nome_originale" if input_id else ''
        return context