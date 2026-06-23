"""
Configurazione parametri sistema scommesse (per campagna, con fallback ai default).
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ScommesseConfig:
    importo_max_senza_codice_default: Decimal
    scadenza_calendario_ore: int
    commissione_allibratore_pct: Decimal
    margine_book_default: Decimal
    margine_book_min: Decimal
    riduzione_margine_per_punto_all: Decimal
    variabilita_potenza_pct: int
    max_selezioni_combinata: int
    potenza_delta_vittoria: int
    potenza_delta_sconfitta: int
    soglia_vincita_rilevante: Decimal
    max_ritiro_vincita_calendario: Decimal


POTENZA_SQUADRA_MIN = 1
POTENZA_SQUADRA_MAX = 999

# Valori di equilibrio LARP (fallback se assente record DB)
DEFAULT_SCOMMESSE_CONFIG = ScommesseConfig(
    importo_max_senza_codice_default=Decimal("15.00"),
    scadenza_calendario_ore=24,
    commissione_allibratore_pct=Decimal("0.08"),
    margine_book_default=Decimal("1.06"),
    margine_book_min=Decimal("1.02"),
    riduzione_margine_per_punto_all=Decimal("0.015"),
    variabilita_potenza_pct=10,
    max_selezioni_combinata=8,
    potenza_delta_vittoria=2,
    potenza_delta_sconfitta=2,
    soglia_vincita_rilevante=Decimal("500.00"),
    max_ritiro_vincita_calendario=Decimal("500.00"),
)


def _from_model(obj) -> ScommesseConfig:
    return ScommesseConfig(
        importo_max_senza_codice_default=obj.importo_max_senza_codice_default,
        scadenza_calendario_ore=obj.scadenza_calendario_ore,
        commissione_allibratore_pct=obj.commissione_allibratore_pct,
        margine_book_default=obj.margine_book_default,
        margine_book_min=obj.margine_book_min,
        riduzione_margine_per_punto_all=obj.riduzione_margine_per_punto_all,
        variabilita_potenza_pct=obj.variabilita_potenza_pct,
        max_selezioni_combinata=obj.max_selezioni_combinata,
        potenza_delta_vittoria=obj.potenza_delta_vittoria,
        potenza_delta_sconfitta=obj.potenza_delta_sconfitta,
        soglia_vincita_rilevante=obj.soglia_vincita_rilevante,
        max_ritiro_vincita_calendario=obj.max_ritiro_vincita_calendario,
    )


def get_config_scommesse(campagna=None) -> ScommesseConfig:
    from personaggi.models import get_default_campagna_id
    from personaggi.scommesse_models import ConfigurazioneScommesse

    campagna_id = campagna
    if campagna is not None and hasattr(campagna, "pk"):
        campagna_id = campagna.pk
    if campagna_id is None:
        campagna_id = get_default_campagna_id()

    cfg = ConfigurazioneScommesse.objects.filter(campagna_id=campagna_id, attiva=True).first()
    if cfg:
        return _from_model(cfg)
    return DEFAULT_SCOMMESSE_CONFIG


def config_to_public_dict(cfg: ScommesseConfig, personaggio=None) -> dict:
    data = {
        "importo_max_senza_codice_default": str(cfg.importo_max_senza_codice_default),
        "scadenza_calendario_ore": cfg.scadenza_calendario_ore,
        "commissione_allibratore_pct": str(cfg.commissione_allibratore_pct),
        "margine_book_default": str(cfg.margine_book_default),
        "max_selezioni_combinata": cfg.max_selezioni_combinata,
        "variabilita_potenza_pct": cfg.variabilita_potenza_pct,
        "soglia_vincita_rilevante": str(cfg.soglia_vincita_rilevante),
        "max_ritiro_vincita_calendario": str(cfg.max_ritiro_vincita_calendario),
    }
    if personaggio is not None:
        from personaggi.scommesse_evento import personaggio_in_evento_attivo
        evento = personaggio_in_evento_attivo(personaggio)
        data["evento_attivo_ritiro_riserva"] = evento is not None
        if evento:
            data["evento_attivo_titolo"] = evento.titolo
    return data
