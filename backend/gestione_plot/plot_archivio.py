"""Archivio plot: sola consultazione e risoluzione dell'evento padre."""

from django.http import Http404

from rest_framework.exceptions import NotFound, ValidationError

from .models import (
    Evento,
    EventoVocePortare,
    GiornoEvento,
    PngAssegnato,
    Quest,
    QuestFase,
    QuestMostro,
    QuestTask,
    QuestVista,
    StaffOffGame,
)

MESSAGGIO_SOLA_LETTURA = "Plot archiviato: sola consultazione."
AZIONI_ARCHIVIO = frozenset({"archivia", "ripristina"})


def evento_archiviato(evento) -> bool:
    return bool(evento is not None and getattr(evento, "archiviato_at", None))


def rifiuta_modifica_plot_archiviato(evento):
    """Blocca scritture sul plot e sui suoi giorni/quest/task."""
    if evento_archiviato(evento):
        raise ValidationError({"detail": MESSAGGIO_SOLA_LETTURA})


def evento_padre(obj):
    """Evento che contiene l'istanza di plot, se riconoscibile."""
    if obj is None:
        return None
    if isinstance(obj, Evento):
        return obj
    if isinstance(obj, (GiornoEvento, EventoVocePortare)):
        return obj.evento
    if isinstance(obj, Quest):
        return obj.giorno.evento
    if isinstance(obj, (QuestMostro, QuestVista, PngAssegnato, StaffOffGame, QuestFase)):
        return obj.quest.giorno.evento
    if isinstance(obj, QuestTask):
        return obj.fase.quest.giorno.evento
    return None


def evento_da_creazione(model, data):
    """Evento padre di un POST di creazione, prima del save."""
    if model is None or model is Evento or not data:
        return None
    if model in (GiornoEvento, EventoVocePortare):
        return Evento.objects.filter(pk=data.get("evento")).first()
    if model is Quest:
        giorno = (
            GiornoEvento.objects.filter(pk=data.get("giorno"))
            .select_related("evento")
            .first()
        )
        return giorno.evento if giorno else None
    if model in (QuestMostro, QuestVista, PngAssegnato, StaffOffGame, QuestFase):
        quest = (
            Quest.objects.filter(pk=data.get("quest"))
            .select_related("giorno__evento")
            .first()
        )
        return quest.giorno.evento if quest else None
    if model is QuestTask:
        fase = (
            QuestFase.objects.filter(pk=data.get("fase"))
            .select_related("quest__giorno__evento")
            .first()
        )
        return fase.quest.giorno.evento if fase else None
    return None


def unisci_target_plot(esistenti, target, archiviati_ids):
    """
    I collegamenti verso plot archiviati restano com'erano.

    ``esistenti`` e ``target`` mappano evento_id → attiva.
    Un id archiviato già collegato non si scollega e non cambia stato.
    Un id archiviato nuovo non viene aggiunto.
    """
    archiviati = {int(eid) for eid in (archiviati_ids or [])}
    out = {int(eid): bool(attiva) for eid, attiva in (target or {}).items()}
    presenti = {int(eid): bool(attiva) for eid, attiva in (esistenti or {}).items()}
    for eid in archiviati:
        if eid in presenti:
            out[eid] = presenti[eid]
        else:
            out.pop(eid, None)
    return out


class BloccaPlotArchiviatoMixin:
    """Rifiuta create/update/destroy e azioni mutanti se il plot è archiviato."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        action = getattr(self, "action", None)
        if action in AZIONI_ARCHIVIO:
            return
        if action == "create":
            model = self.get_queryset().model
            rifiuta_modifica_plot_archiviato(evento_da_creazione(model, request.data))
            return
        lookup = self.lookup_url_kwarg or self.lookup_field
        if lookup not in kwargs and "pk" not in kwargs:
            return
        try:
            obj = self.get_object()
        except (Http404, NotFound):
            return
        rifiuta_modifica_plot_archiviato(evento_padre(obj))
