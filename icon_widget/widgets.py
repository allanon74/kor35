# In icon_widget/widgets.py
from django import forms

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

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Passa il model_name al template
        context['widget']['model_name'] = attrs.get('model_name', 'personaggi.punteggio')
        return context