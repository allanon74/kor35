from django.apps import AppConfig
from django.db.models.signals import post_save


class PersonaggiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'personaggi'
    
    def ready(self):
        import personaggi.signals
        import personaggi.sync_tombstone_signals  # noqa: F401
        from personaggi import signals as personaggi_signals

        for model in self.get_models():
            if model._meta.proxy or model._meta.abstract:
                continue
            if not model._meta.parents:
                continue
            if not any(
                p.__module__ == "personaggi.models"
                and not getattr(p._meta, "abstract", False)
                and hasattr(p, "updated_at")
                for p in model._meta.parents.keys()
            ):
                continue
            uid = f"kor35.bump_mti_parents.{model._meta.label_lower}"
            post_save.connect(
                personaggi_signals.bump_mti_personaggi_parents_updated_at,
                sender=model,
                dispatch_uid=uid,
            )
