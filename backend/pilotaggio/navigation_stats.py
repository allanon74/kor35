"""
Statistiche di accesso alle console di bordo e alle azioni QR sui sottosistemi.

Sigle configurabili in PilotRuntimeConfig (tab Runtime staff → Statistiche navigazione).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PilotRuntimeConfig

DEFAULT_NAVIGAZIONE_SIGLA = "0PI"
DEFAULT_INGEGNERIA_SIGLA = "0IN"
DEFAULT_SABOTAGGIO_SIGLA = "0SA"
DEFAULT_RIPARAZIONE_SIGLA = "0RI"
DEFAULT_SCIENTIFICA_SIGLA = "0SC"
DEFAULT_COMUNICAZIONI_SIGLA = "0CO"


def _norm_sigla(raw: Optional[str], default: str) -> str:
    s = (raw or default).strip().upper()[:3]
    return s or default


def navigazione_stat_sigla(cfg: Optional["PilotRuntimeConfig"] = None) -> str:
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    return _norm_sigla(getattr(cfg, "navigazione_stat_accesso_sigla", None), DEFAULT_NAVIGAZIONE_SIGLA)


def ingegneria_stat_sigla(cfg: Optional["PilotRuntimeConfig"] = None) -> str:
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    return _norm_sigla(getattr(cfg, "compattatore_stat_accesso_sigla", None), DEFAULT_INGEGNERIA_SIGLA)


def sabotaggio_stat_sigla(cfg: Optional["PilotRuntimeConfig"] = None) -> str:
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    return _norm_sigla(getattr(cfg, "sabotaggio_stat_sigla", None), DEFAULT_SABOTAGGIO_SIGLA)


def riparazione_stat_sigla(cfg: Optional["PilotRuntimeConfig"] = None) -> str:
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    return _norm_sigla(getattr(cfg, "riparazione_stat_sigla", None), DEFAULT_RIPARAZIONE_SIGLA)


def scientifica_stat_sigla(cfg: Optional["PilotRuntimeConfig"] = None) -> str:
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    return _norm_sigla(getattr(cfg, "scientifica_stat_accesso_sigla", None), DEFAULT_SCIENTIFICA_SIGLA)


def comunicazioni_stat_sigla(cfg: Optional["PilotRuntimeConfig"] = None) -> str:
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    return _norm_sigla(getattr(cfg, "comunicazioni_stat_accesso_sigla", None), DEFAULT_COMUNICAZIONI_SIGLA)


def _sigle_dict(cfg: "PilotRuntimeConfig") -> Dict[str, str]:
    return {
        "navigazione": navigazione_stat_sigla(cfg),
        "ingegneria": ingegneria_stat_sigla(cfg),
        "stiva_app": ingegneria_stat_sigla(cfg),
        "sabotaggio": sabotaggio_stat_sigla(cfg),
        "riparazione": riparazione_stat_sigla(cfg),
        "scientifica": scientifica_stat_sigla(cfg),
        "comunicazioni": comunicazioni_stat_sigla(cfg),
    }


def build_navigation_stats_payload(cfg: Optional["PilotRuntimeConfig"] = None) -> Dict[str, Any]:
    """Payload pubblico/staff: sigle effettive + catalogo ruoli navigazione."""
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    sigle = _sigle_dict(cfg)
    return {
        "sigle": sigle,
        "console": {
            "navigazione_abilitata": True,
            "ingegneria_abilitata": bool(cfg.compattatore_console_abilitata),
            "scientifica_abilitata": bool(getattr(cfg, "scientifica_console_abilitata", False)),
            "comunicazioni_abilitata": bool(getattr(cfg, "comunicazioni_console_abilitata", False)),
        },
        "ruoli": navigation_roles_catalog(cfg, sigle=sigle),
    }


def navigation_roles_catalog(
    cfg: Optional["PilotRuntimeConfig"] = None,
    *,
    sigle: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Elenco ruoli per la UI staff (documentazione + sigla corrente)."""
    from .models import PilotRuntimeConfig

    cfg = cfg or PilotRuntimeConfig.get_solo()
    sigle = sigle or _sigle_dict(cfg)
    return [
        {
            "id": "navigazione",
            "nome": "Console Navigazione",
            "sigla": sigle["navigazione"],
            "requisito": f"{sigle['navigazione']} ≥ 1",
            "url_console": "/pilot/",
            "implementato": True,
            "note": "Plancia di pilotaggio (schermi status/control). Login ticket o QR.",
        },
        {
            "id": "ingegneria",
            "nome": "Console Ingegneria",
            "sigla": sigle["ingegneria"],
            "requisito": f"{sigle['ingegneria']} > 0",
            "url_console": "/pilot/?screen=compattatore",
            "implementato": bool(cfg.compattatore_console_abilitata),
            "note": "Stiva nave, compressione/risonanza. Operazione quantica opzionale (flag evento).",
        },
        {
            "id": "stiva_app",
            "nome": "Tab Stiva (app giocatore)",
            "sigla": sigle["stiva_app"],
            "requisito": f"{sigle['stiva_app']} > 0",
            "url_console": None,
            "implementato": True,
            "note": "Inventario componenti nave in sola lettura nel menu personaggio.",
        },
        {
            "id": "scientifica",
            "nome": "Console Scientifica",
            "sigla": sigle["scientifica"],
            "requisito": f"{sigle['scientifica']} > 0",
            "url_console": "/pilot/?screen=scientifica",
            "implementato": bool(getattr(cfg, "scientifica_console_abilitata", False)),
            "note": "Spettrografia eventi e scan profondo (Fase 1). Matrice R/S/T in Fase 2.",
        },
        {
            "id": "sabotaggio",
            "nome": "Sabotaggio sottosistemi (QR)",
            "sigla": sigle["sabotaggio"],
            "requisito": f"{sigle['sabotaggio']} > 0",
            "url_console": None,
            "implementato": True,
            "note": "Scansione QR fisico su sottosistema — guasto immediato.",
        },
        {
            "id": "riparazione",
            "nome": "Riparazione sottosistemi (QR)",
            "sigla": sigle["riparazione"],
            "requisito": f"{sigle['riparazione']} > 0",
            "url_console": None,
            "implementato": True,
            "note": "Ripristino dopo guasto; minigioco e componenti stiva se configurati.",
        },
        {
            "id": "comunicazioni",
            "nome": "Console Comunicazioni",
            "sigla": sigle["comunicazioni"],
            "requisito": f"{sigle['comunicazioni']} > 0",
            "url_console": "/pilot/?screen=comunicazioni",
            "implementato": False,
            "note": "Riservata — uso futuro (messaggistica di bordo / prefetture / equipaggio).",
        },
    ]
