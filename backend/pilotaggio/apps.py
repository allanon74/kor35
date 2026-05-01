from django.apps import AppConfig


class PilotaggioConfig(AppConfig):
    """
    App per la console di pilotaggio nave (LARP).
    Modelli sync-safe, motore eventi/DEFCON e CRUD staff.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "pilotaggio"
    verbose_name = "Pilotaggio nave"
