from django import forms

class CustomIconWidget(forms.TextInput):
    template_name = 'admin/widgets/custom_icon_widget.html'

    class Media:
        js = ('admin/js/custom_icon_picker.js',)

    # Questo metodo ci permette di passare dati extra
    # dall'admin (come il nome del modello) al template
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # 'model_name' sarà impostato dal formfield_for_dbfield
        context['widget']['model_name'] = attrs.get('model_name', '')
        return context