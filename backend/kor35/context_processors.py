from .build_info import get_build_info
from gestione_plot.models import ConfigurazioneSito


def build_info(_request):
    """
    Rende disponibile `KOR35_BUILD` in tutti i template (inclusa Django admin).
    """
    return {"KOR35_BUILD": get_build_info()}


def maintenance_context(_request):
    config = ConfigurazioneSito.get_config()
    return {
        "KOR35_MAINTENANCE_MODE": bool(config.maintenance_mode),
        "KOR35_MAINTENANCE_ADMIN_NOTE": config.maintenance_admin_note,
    }

