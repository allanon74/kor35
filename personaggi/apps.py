from django.apps import AppConfig


class PersonaggiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'personaggi'
    
    def ready(self):
        import personaggi.signals
