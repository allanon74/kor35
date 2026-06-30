import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CreditCard, Loader2, Sparkles, BookOpen, Swords, X, Package, Radio, ExternalLink, SlidersHorizontal,
} from 'lucide-react';
import { useCharacter } from './CharacterContext';
import {
  carteGetCollezione,
  carteApriBustina,
  carteEquipReliquiario,
  carteGetDuelli,
  carteGetDuello,
  carteInvitaDuello,
  carteAccettaDuelloCodice,
  carteAccettaDuello,
  carteAzioneDuello,
  carteSaveMazzo,
  carteDeleteMazzo,
  carteGetAvversariDuello,
  carteApriScontro,
  cartePrematchAzione,
} from '../api';
import { RELIQUIARIO_SLOTS, MAZZO_DUELLO_SIZE, CARTA_ENERGIA_LABEL, CARTA_RARITA_LABEL, CARTA_TIPO_LABEL } from '../carte/carteConstants';
import CardFrame from '../carte/CardFrame';
import CardRulesText from '../carte/CardRulesText';
import { useDuelloLive } from '../carte/useDuelloLive';
import MazzoDuelloBuilder from '../carte/MazzoDuelloBuilder';
import {
  buildCollezioneView,
  COLLEZIONE_SORT_OPTIONS,
} from '../carte/collezioneUtils';

function CartaCard({ item, selected, onSelect, compact = false, temaEnergie, keywords }) {
  return (
    <CardFrame
      item={item}
      selected={selected}
      onClick={() => onSelect?.(item)}
      compact={compact}
      temaEnergie={temaEnergie}
      keywords={keywords}
      showRules={!compact}
    />
  );
}

function CollezioneStackCard({ stack, onSelect, temaEnergie, keywords }) {
  return (
    <div className="relative">
      <CartaCard
        item={stack.representative}
        onSelect={() => onSelect(stack)}
        temaEnergie={temaEnergie}
        keywords={keywords}
      />
      {stack.count > 1 && (
        <span
          className="pointer-events-none absolute -right-1 -top-1 z-10 flex h-6 min-w-[1.5rem] items-center justify-center rounded-full border-2 border-gray-900 bg-violet-600 px-1 text-[11px] font-black text-white shadow-md"
          title={`${stack.count} copie`}
        >
          ×{stack.count}
        </span>
      )}
      {stack.inReliquarioCount > 0 && (
        <span
          className="pointer-events-none absolute bottom-1 left-1 z-10 rounded bg-indigo-900/90 px-1 py-0.5 text-[8px] font-bold text-indigo-200"
          title="In reliquiario"
        >
          {stack.inReliquarioCount === stack.count ? 'Equip.' : `${stack.inReliquarioCount}/${stack.count} eq.`}
        </span>
      )}
    </div>
  );
}

function CartaDetailModal({ item, stack, onClose, temaEnergie, keywords }) {
  const [showLore, setShowLore] = useState(false);
  if (!item && !stack) return null;
  const displayItem = stack?.representative || item;
  const c = displayItem?.carta || displayItem;
  const copyCount = stack?.count ?? 1;

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/70 p-4 sm:items-center" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-lg flex-col gap-4 rounded-xl border border-gray-600 bg-gray-950 p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <h3 className="text-lg font-bold text-white">Dettaglio carta</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-white">
            <X size={22} />
          </button>
        </div>
        <div className="flex justify-center">
          <CardFrame item={displayItem} size="lg" temaEnergie={temaEnergie} showRules={false} />
        </div>
        {copyCount > 1 && (
          <p className="text-center text-sm font-bold text-violet-300">
            Possiedi {copyCount} copie di questa carta
          </p>
        )}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setShowLore(false)}
            className={`rounded px-3 py-1 text-xs font-bold ${!showLore ? 'bg-indigo-700 text-white' : 'bg-gray-800 text-gray-400'}`}
          >
            <Swords size={12} className="mr-1 inline" />
            Gioco
          </button>
          <button
            type="button"
            onClick={() => setShowLore(true)}
            className={`rounded px-3 py-1 text-xs font-bold ${showLore ? 'bg-amber-800 text-white' : 'bg-gray-800 text-gray-400'}`}
          >
            <BookOpen size={12} className="mr-1 inline" />
            Lore
          </button>
        </div>
        <div className="max-h-40 overflow-y-auto rounded border border-gray-700 bg-gray-900/80 p-3 text-sm text-gray-200">
          <p className="whitespace-pre-wrap">
            {showLore ? (
              c.testo_lore || 'Nessun testo lore.'
            ) : (
              <CardRulesText text={c.testo_gioco || 'Nessun effetto di gioco.'} keywords={keywords} />
            )}
          </p>
        </div>
        {c.codice && (
          <p className="text-center text-[10px] text-gray-500">{c.codice}</p>
        )}
      </div>
    </div>
  );
}

export default function CarteCollezionabiliTab({ onLogout }) {
  const { selectedCharacterId, selectedCharacterData } = useCharacter();
  const charId = selectedCharacterId;

  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState(null);
  const [equipMode, setEquipMode] = useState(null);
  const [lastPull, setLastPull] = useState(null);
  const [duelli, setDuelli] = useState([]);
  const [activeDuello, setActiveDuello] = useState(null);
  const [codiceInvito, setCodiceInvito] = useState('');
  const [duelBusy, setDuelBusy] = useState(false);
  const [mazzoIds, setMazzoIds] = useState([]);
  const [activeMazzoId, setActiveMazzoId] = useState(null);
  const [mazzoNome, setMazzoNome] = useState('Mazzo 1');
  const [mazzoIsDefault, setMazzoIsDefault] = useState(true);
  const [mazzoBuilderOpen, setMazzoBuilderOpen] = useState(false);
  const [savingMazzo, setSavingMazzo] = useState(false);
  const [avversari, setAvversari] = useState([]);
  const [selectedAvversarioId, setSelectedAvversarioId] = useState('');
  const [lobbyQr, setLobbyQr] = useState(null);
  const [postaInput, setPostaInput] = useState('0');
  const [colSearch, setColSearch] = useState('');
  const [colTipo, setColTipo] = useState('');
  const [colEnergia, setColEnergia] = useState('');
  const [colRarita, setColRarita] = useState('');
  const [colEspansione, setColEspansione] = useState('');
  const [colSoloLibere, setColSoloLibere] = useState(false);
  const [colSort, setColSort] = useState('nome_asc');
  const [colFiltersOpen, setColFiltersOpen] = useState(false);
  const [detailStack, setDetailStack] = useState(null);

  const onDuelloWsUpdate = useCallback((payload) => {
    setActiveDuello(payload);
    setDuelli((prev) => prev.map((d) => (d.id === payload.id ? payload : d)));
  }, []);

  useDuelloLive(
    ['LOB', 'PRE', 'COR'].includes(activeDuello?.stato) ? activeDuello?.id : null,
    onDuelloWsUpdate,
  );

  const loadMazzoIntoEditor = useCallback((m) => {
    if (m) {
      setActiveMazzoId(m.id);
      setMazzoIds(m.carte_possedute_ids || []);
      setMazzoNome(m.nome || 'Mazzo');
      setMazzoIsDefault(!!m.is_default);
    } else {
      setActiveMazzoId(null);
      setMazzoIds([]);
      setMazzoNome(`Mazzo ${(data?.mazzi?.length || 0) + 1}`);
      setMazzoIsDefault(!(data?.mazzi?.length));
    }
  }, [data?.mazzi?.length]);

  useEffect(() => {
    if (!data?.mazzi) return;
    const current = activeMazzoId
      ? data.mazzi.find((m) => m.id === activeMazzoId)
      : data.mazzi.find((m) => m.is_default) || data.mazzi[0];
    if (current && !mazzoBuilderOpen) {
      setMazzoIds(current.carte_possedute_ids || []);
      if (!activeMazzoId) {
        setActiveMazzoId(current.id);
        setMazzoNome(current.nome || 'Mazzo');
        setMazzoIsDefault(!!current.is_default);
      }
    }
  }, [data?.mazzi, activeMazzoId, mazzoBuilderOpen]);

  const handleSaveMazzo = async () => {
    if (!charId || mazzoIds.length !== MAZZO_DUELLO_SIZE) {
      setError(`Il mazzo deve avere esattamente ${MAZZO_DUELLO_SIZE} carte.`);
      return;
    }
    setSavingMazzo(true);
    setError('');
    try {
      const res = await carteSaveMazzo(charId, mazzoIds, {
        mazzoId: activeMazzoId,
        nome: mazzoNome,
        isDefault: mazzoIsDefault,
      }, onLogout);
      setData((prev) => ({ ...prev, mazzi: res.mazzi || [] }));
      if (res.saved_id) setActiveMazzoId(res.saved_id);
      setMazzoBuilderOpen(false);
    } catch (e) {
      setError(e?.message || 'Salvataggio mazzo fallito.');
    } finally {
      setSavingMazzo(false);
    }
  };

  const handleDeleteMazzo = async () => {
    if (!charId || !activeMazzoId) return;
    setSavingMazzo(true);
    setError('');
    try {
      const res = await carteDeleteMazzo(charId, activeMazzoId, onLogout);
      setData((prev) => ({ ...prev, mazzi: res.mazzi || [] }));
      const next = (res.mazzi || [])[0];
      loadMazzoIntoEditor(next || null);
      setMazzoBuilderOpen(false);
    } catch (e) {
      setError(e?.message || 'Eliminazione mazzo fallita.');
    } finally {
      setSavingMazzo(false);
    }
  };

  const load = useCallback(async () => {
    if (!charId) return;
    setLoading(true);
    setError('');
    try {
      const payload = await carteGetCollezione(charId, onLogout);
      setData(payload);
      if (payload?.puo_accedere) {
        const d = await carteGetDuelli(charId, onLogout);
        setDuelli(d?.duelli || []);
        const lobbyAttiva = (d?.duelli || []).find(
          (x) => ['LOB', 'PRE'].includes(x.stato)
            && (x.sfidante?.id === charId || x.sfidato?.id === charId),
        );
        if (lobbyAttiva) {
          setActiveDuello(lobbyAttiva);
        }
        if (payload.duello_avvio === 'lista') {
          const avv = await carteGetAvversariDuello(charId, onLogout);
          setAvversari(avv?.avversari || []);
        } else {
          setAvversari([]);
        }
      } else {
        setDuelli([]);
        setAvversari([]);
      }
    } catch (e) {
      setError(e?.message || 'Errore caricamento collezione.');
    } finally {
      setLoading(false);
    }
  }, [charId, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const openDuello = useCallback(async (duelloId) => {
    if (!charId) return;
    try {
      const d = await carteGetDuello(charId, duelloId, onLogout);
      setActiveDuello(d);
    } catch (e) {
      setError(e?.message || 'Errore caricamento duello.');
    }
  }, [charId, onLogout]);

  useEffect(() => {
    const onDuelloCarteEvent = (e) => {
      const detail = e?.detail;
      if (!charId || !detail?.duello_id) return;
      if (String(detail.destinatario_personaggio_id) !== String(charId)) return;
      openDuello(detail.duello_id);
      carteGetDuelli(charId, onLogout)
        .then((d) => setDuelli(d?.duelli || []))
        .catch(() => {});
    };
    window.addEventListener('kor35:duello-carte', onDuelloCarteEvent);
    return () => window.removeEventListener('kor35:duello-carte', onDuelloCarteEvent);
  }, [charId, onLogout, openDuello]);

  const handleApriBustina = async (bustinaId) => {
    if (!charId || opening) return;
    setOpening(true);
    setError('');
    try {
      const result = await carteApriBustina(charId, bustinaId, onLogout);
      setLastPull(result.carte || []);
      setData(result.collezione || data);
      await load();
    } catch (e) {
      setError(e?.message || 'Apertura bustina fallita.');
    } finally {
      setOpening(false);
    }
  };

  const handleEquip = async (slotIndex, cartaPossedutaId) => {
    if (!charId) return;
    try {
      const payload = await carteEquipReliquiario(charId, slotIndex, cartaPossedutaId, onLogout);
      setData((prev) => ({ ...prev, ...payload }));
      setEquipMode(null);
    } catch (e) {
      setError(e?.message || 'Equipaggiamento fallito.');
    }
  };

  const handleApriScontro = async () => {
    if (!charId) return;
    setDuelBusy(true);
    setError('');
    try {
      const lobby = await carteApriScontro(charId, onLogout);
      setLobbyQr({
        qrcode_id: lobby.qrcode_id,
        qr_image_data_uri: lobby.qr_image_data_uri,
      });
      setActiveDuello(lobby);
      setDuelli((prev) => [lobby, ...prev.filter((d) => d.id !== lobby.id)]);
    } catch (e) {
      setError(e?.message || 'Impossibile aprire lo scontro.');
    } finally {
      setDuelBusy(false);
    }
  };

  const handlePrematch = async (azione, payload = {}) => {
    if (!charId || !activeDuello?.id) return;
    setDuelBusy(true);
    setError('');
    try {
      const res = await cartePrematchAzione(charId, activeDuello.id, azione, payload, onLogout);
      setActiveDuello(res);
      setDuelli((prev) => prev.map((d) => (d.id === res.id ? res : d)));
      if (res.stato === 'COR') {
        await load();
      }
    } catch (e) {
      setError(e?.message || 'Azione pre-partita fallita.');
    } finally {
      setDuelBusy(false);
    }
  };

  const handleCreaInvito = async () => {
    if (!charId || mazzoIds.length < MAZZO_DUELLO_SIZE) {
      setError(`Servono esattamente ${MAZZO_DUELLO_SIZE} carte nel mazzo da duello.`);
      return;
    }
    if (data?.duello_avvio === 'lista' && !selectedAvversarioId) {
      setError('Seleziona un avversario dalla lista.');
      return;
    }
    setDuelBusy(true);
    try {
      const body = { mazzo_ids: mazzoIds };
      if (data?.duello_avvio === 'lista') {
        body.sfidato_id = selectedAvversarioId;
      }
      const invito = await carteInvitaDuello(charId, body, onLogout);
      setDuelli((prev) => [invito, ...prev]);
      setActiveDuello(invito);
      setError('');
    } catch (e) {
      setError(e?.message || 'Invito fallito.');
    } finally {
      setDuelBusy(false);
    }
  };

  const handleAccettaInvito = async (duelloId) => {
    if (!charId || mazzoIds.length < MAZZO_DUELLO_SIZE) {
      setError(`Servono esattamente ${MAZZO_DUELLO_SIZE} carte nel mazzo.`);
      return;
    }
    setDuelBusy(true);
    try {
      const partita = await carteAccettaDuello(
        charId,
        duelloId,
        { mazzo_ids: mazzoIds },
        onLogout,
      );
      setActiveDuello(partita);
      await load();
    } catch (e) {
      setError(e?.message || 'Accettazione fallita.');
    } finally {
      setDuelBusy(false);
    }
  };

  const handleAccettaCodice = async () => {
    if (!charId || !codiceInvito.trim()) return;
    if (mazzoIds.length < MAZZO_DUELLO_SIZE) {
      setError(`Servono esattamente ${MAZZO_DUELLO_SIZE} carte nel mazzo.`);
      return;
    }
    setDuelBusy(true);
    try {
      const partita = await carteAccettaDuelloCodice(
        charId,
        { codice_invito: codiceInvito.trim().toUpperCase(), mazzo_ids: mazzoIds },
        onLogout,
      );
      setActiveDuello(partita);
      await load();
    } catch (e) {
      setError(e?.message || 'Accettazione fallita.');
    } finally {
      setDuelBusy(false);
    }
  };

  const handleDuelloAzione = async (azione, payload = {}) => {
    if (!charId || !activeDuello?.id) return;
    setDuelBusy(true);
    try {
      const res = await carteAzioneDuello(charId, activeDuello.id, azione, payload, onLogout);
      setActiveDuello(res);
    } catch (e) {
      setError(e?.message || 'Azione non valida.');
    } finally {
      setDuelBusy(false);
    }
  };

  const isMioTurno = activeDuello?.turno_personaggio_id === charId;
  const miaMano = activeDuello?.stato_gioco?.mani?.[String(charId)] || [];
  const mioCampo = activeDuello?.stato_gioco?.campo?.[String(charId)] || {};
  const mieiEroi = mioCampo.eroi || [null, null];
  const miaEnergia = mioCampo.energia ?? 0;
  const avversarioId = activeDuello?.sfidante?.id === charId
    ? activeDuello?.sfidato?.id
    : activeDuello?.sfidante?.id;
  const campoAvversario = avversarioId
    ? (activeDuello?.stato_gioco?.campo?.[String(avversarioId)] || {})
    : {};

  const aggiornaCampoManuale = (patch) => handleDuelloAzione('aggiorna_stato', patch);

  const impostaEroeSlot = (slot, cpId) => {
    const eroi = [...mieiEroi];
    eroi[slot] = cpId;
    aggiornaCampoManuale({ eroi });
  };

  const nomeCartaDuello = (cpId) => (cpId ? (activeDuello.carte?.[cpId]?.nome || 'carta') : '—');

  const mieiOggetti = mioCampo.oggetti || {};

  const nomeOggettoSuEroe = (slot) => {
    const oid = mieiOggetti[String(slot)];
    return oid ? nomeCartaDuello(oid) : null;
  };

  const saluteEroeCampo = (campo, slot) => {
    const cpId = (campo?.eroi || [])[slot];
    if (!cpId) return null;
    const sal = (campo?.salute_eroi || [])[slot];
    return sal ?? activeDuello?.carte?.[cpId]?.salute ?? null;
  };

  const renderGiocaCartaButtons = (cpId, meta) => {
    const tipo = meta?.tipo;
    if (tipo === 'PG') {
      return [0, 1].map((slot) => (
        !mieiEroi[slot] ? (
          <button
            key={`${cpId}-slot-${slot}`}
            type="button"
            disabled={duelBusy}
            className="rounded border border-indigo-700 px-2 py-1 hover:bg-indigo-950/40"
            onClick={() => handleDuelloAzione('gioca_carta', {
              carta_posseduta_id: cpId,
              slot_eroe: slot,
            })}
          >
            {meta?.nome || 'PG'} → eroe {slot}
          </button>
        ) : null
      ));
    }
    if (tipo === 'OGG') {
      return [0, 1].map((slot) => (
        mieiEroi[slot] && !mieiOggetti[String(slot)] ? (
          <button
            key={`${cpId}-ogg-${slot}`}
            type="button"
            disabled={duelBusy}
            className="rounded border border-amber-800 px-2 py-1 hover:bg-amber-950/30"
            onClick={() => handleDuelloAzione('gioca_carta', {
              carta_posseduta_id: cpId,
              slot_eroe: slot,
            })}
          >
            {meta?.nome || 'Oggetto'} → eroe {slot}
          </button>
        ) : null
      ));
    }
    if (tipo === 'LUO') {
      if (mioCampo.luogo) return null;
      return (
        <button
          key={cpId}
          type="button"
          disabled={duelBusy}
          className="rounded border border-emerald-800 px-2 py-1 hover:bg-emerald-950/30"
          onClick={() => handleDuelloAzione('gioca_carta', { carta_posseduta_id: cpId })}
        >
          Gioca luogo: {meta?.nome || 'carta'}
        </button>
      );
    }
    return (
      <button
        key={cpId}
        type="button"
        disabled={duelBusy}
        className="rounded border border-gray-600 px-2 py-1 hover:bg-gray-800"
        onClick={() => handleDuelloAzione('gioca_carta', { carta_posseduta_id: cpId })}
      >
        Gioca {meta?.nome || 'carta'}
      </button>
    );
  };

  const reliquiarioMap = data?.reliquiario || {};
  const carteById = useMemo(() => {
    const map = new Map();
    (data?.carte || []).forEach((c) => map.set(c.id, c));
    return map;
  }, [data?.carte]);
  const cardKeywords = data?.keywords || [];
  const invitiPendenti = useMemo(
    () => (duelli || []).filter((d) => d.stato === 'ATT' && d.richiede_mia_accettazione),
    [duelli],
  );
  const duelloAvvio = data?.duello_avvio || 'off';

  const espansioniCollezione = useMemo(() => {
    const seen = new Map();
    (data?.carte || []).forEach((item) => {
      const c = item.carta;
      if (c?.espansione_id && !seen.has(c.espansione_id)) {
        seen.set(c.espansione_id, c.espansione_nome || c.espansione_slug || 'Espansione');
      }
    });
    return Array.from(seen.entries()).map(([id, nome]) => ({ id, nome }));
  }, [data?.carte]);

  const collezioneView = useMemo(
    () => buildCollezioneView(data?.carte || [], {
      search: colSearch,
      tipo: colTipo,
      energia: colEnergia,
      rarita: colRarita,
      espansioneId: colEspansione,
      soloNonEquip: colSoloLibere,
    }, colSort),
    [data?.carte, colSearch, colTipo, colEnergia, colRarita, colEspansione, colSoloLibere, colSort],
  );

  const hasColFilters = !!(colSearch || colTipo || colEnergia || colRarita || colEspansione || colSoloLibere);

  const slots = Array.from({ length: RELIQUIARIO_SLOTS }, (_, i) => {
    const cpId = reliquiarioMap[String(i)];
    return cpId ? carteById.get(cpId) : null;
  });

  if (!charId) {
    return <p className="p-4 text-gray-400">Seleziona un personaggio.</p>;
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3 pb-24 text-gray-100">
      <header className="flex items-center justify-between gap-2 border-b border-gray-700 pb-2">
        <div className="flex items-center gap-2">
          <CreditCard className="text-violet-400" />
          <div>
            <h2 className="text-lg font-bold">Cronache delle Sette Elegie</h2>
            <p className="text-xs text-gray-400">
              Collezione · Reliquiario · Bustine · Duello live
              {data?.accesso_modo === 'TEST' && (
                <span className="ml-2 rounded bg-amber-900 px-1.5 py-0.5 text-[10px] font-bold text-amber-200">
                  TESTING
                </span>
              )}
              {data?.crediti != null ? ` · ${Number(data.crediti).toFixed(0)} CR` : ''}
            </p>
          </div>
        </div>
        {data?.accesso_modo === 'OPEN' && data?.wiki_regolamento_slug && (
          <Link
            to={`/regolamento/${data.wiki_regolamento_slug}`}
            className="flex shrink-0 items-center gap-1 rounded border border-violet-800 bg-violet-950/50 px-2 py-1 text-xs font-bold text-violet-200 hover:bg-violet-900/50"
          >
            <BookOpen size={14} />
            Regolamento
            <ExternalLink size={12} className="opacity-60" />
          </Link>
        )}
      </header>

      {error && (
        <div className="rounded border border-red-800 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</div>
      )}

      {loading && (
        <div className="flex justify-center py-12 text-gray-400">
          <Loader2 className="animate-spin" size={32} />
        </div>
      )}

      {!loading && data && !data.puo_accedere && (
        <p className="text-sm text-gray-500">
          Le carte collezionabili non sono disponibili per questo personaggio.
          {data.accesso_modo === 'TEST' && ' (modalità testing: solo PNG staff.)'}
        </p>
      )}

      {!loading && data && data.puo_accedere && (
        <>
          {/* Mazzo duello */}
          <section className="rounded-lg border border-indigo-800 bg-indigo-950/20 p-3">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h3 className="flex items-center gap-1 text-sm font-bold text-indigo-300">
                <Swords size={16} /> Mazzo duello ({mazzoIds.length}/{MAZZO_DUELLO_SIZE})
              </h3>
              <button
                type="button"
                className="rounded bg-indigo-800 px-2 py-1 text-xs font-bold"
                onClick={() => setMazzoBuilderOpen((v) => !v)}
              >
                {mazzoBuilderOpen ? 'Chiudi editor' : 'Modifica mazzo'}
              </button>
            </div>
            {mazzoBuilderOpen && (
              <MazzoDuelloBuilder
                carte={data.carte || []}
                carteById={carteById}
                mazzi={data.mazzi || []}
                activeMazzoId={activeMazzoId}
                mazzoIds={mazzoIds}
                mazzoNome={mazzoNome}
                mazzoIsDefault={mazzoIsDefault}
                onMazzoIdsChange={setMazzoIds}
                onActiveMazzoChange={(m) => loadMazzoIntoEditor(m)}
                onMazzoNomeChange={setMazzoNome}
                onMazzoIsDefaultChange={setMazzoIsDefault}
                onNewMazzo={() => loadMazzoIntoEditor(null)}
                onSave={handleSaveMazzo}
                onDelete={handleDeleteMazzo}
                saving={savingMazzo}
                temaEnergie={data?.tema_energie}
                keywords={cardKeywords}
              />
            )}
            {!mazzoBuilderOpen && (data.mazzi || []).length > 0 && (
              <p className="text-xs text-gray-500">
                Mazzo attivo:{' '}
                <strong className="text-indigo-200">
                  {(data.mazzi.find((m) => m.id === activeMazzoId) || data.mazzi.find((m) => m.is_default) || data.mazzi[0])?.nome}
                </strong>
                {' '}({mazzoIds.length}/{MAZZO_DUELLO_SIZE} carte)
              </p>
            )}
          </section>

          {/* Duello live */}
          <section className="rounded-lg border border-sky-800 bg-sky-950/20 p-3">
            <h3 className="mb-2 flex items-center gap-1 text-sm font-bold text-sky-300">
              <Radio size={16} /> Partita / Duello live
            </h3>

            {invitiPendenti.length > 0 && (
              <div className="mb-3 space-y-2 rounded border border-amber-700/60 bg-amber-950/30 p-2">
                <p className="text-xs font-bold text-amber-200">Sfide in attesa della tua risposta</p>
                {invitiPendenti.map((d) => (
                  <div key={d.id} className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span>
                      <strong>{d.sfidante?.nome}</strong> ti sfida a duello
                    </span>
                    <button
                      type="button"
                      disabled={duelBusy || mazzoIds.length !== MAZZO_DUELLO_SIZE}
                      onClick={() => handleAccettaInvito(d.id)}
                      className="rounded bg-emerald-800 px-2 py-1 font-bold disabled:opacity-50"
                    >
                      Accetta partita
                    </button>
                  </div>
                ))}
                {mazzoIds.length !== MAZZO_DUELLO_SIZE && (
                  <p className="text-[10px] text-amber-400/80">
                    Configura un mazzo da {MAZZO_DUELLO_SIZE} carte prima di accettare.
                  </p>
                )}
              </div>
            )}

            {duelloAvvio === 'lista' && (
              <div className="mb-2 flex flex-wrap items-end gap-2">
                <label className="block text-xs text-gray-400">
                  Avversario (testing a distanza)
                  <select
                    className="mt-1 block min-w-[180px] rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm text-white"
                    value={selectedAvversarioId}
                    onChange={(e) => setSelectedAvversarioId(e.target.value)}
                  >
                    <option value="">— Seleziona —</option>
                    {avversari.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.nome}
                        {a.tipologia ? ` (${a.tipologia})` : ''}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  disabled={duelBusy || !selectedAvversarioId}
                  onClick={handleCreaInvito}
                  className="rounded bg-sky-800 px-3 py-1 text-xs font-bold disabled:opacity-50"
                >
                  Invia sfida
                </button>
              </div>
            )}

            {duelloAvvio === 'lobby' && (
              <div className="mb-3 space-y-2">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={duelBusy}
                    onClick={handleApriScontro}
                    className="rounded bg-sky-800 px-3 py-1 text-xs font-bold disabled:opacity-50"
                  >
                    Apri scontro
                  </button>
                </div>
                <p className="text-xs text-gray-400">
                  Mostra il <strong>QR dello scontro</strong> al tuo avversario, oppure fatti scansionare
                  dalla tab Scanner con «Unisciti allo scontro».
                </p>
                {(lobbyQr?.qr_image_data_uri || activeDuello?.stato === 'LOB') && (
                  <div className="rounded border border-sky-800/60 bg-gray-950 p-3 text-center">
                    <p className="mb-2 text-xs text-sky-200">In attesa avversario — scansiona questo QR</p>
                    {lobbyQr?.qr_image_data_uri && (
                      <img
                        src={lobbyQr.qr_image_data_uri}
                        alt="QR scontro"
                        className="mx-auto h-40 w-40 rounded bg-white p-1"
                      />
                    )}
                    {activeDuello?.qrcode_id && (
                      <p className="mt-1 font-mono text-[10px] text-gray-500">ID {activeDuello.qrcode_id}</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {duelloAvvio === 'lista' && (
              <div className="mb-2 flex flex-wrap gap-2">
                <input
                  className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-xs"
                  placeholder="Codice invito (solo testing)"
                  value={codiceInvito}
                  onChange={(e) => setCodiceInvito(e.target.value)}
                />
                <button
                  type="button"
                  disabled={duelBusy}
                  onClick={handleAccettaCodice}
                  className="rounded bg-emerald-800 px-3 py-1 text-xs font-bold disabled:opacity-50"
                >
                  Accetta codice
                </button>
              </div>
            )}

            <ul className="space-y-1 text-xs text-gray-300">
              {duelli.slice(0, 5).map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-2">
                  <span>
                    {d.sfidante?.nome} vs {d.sfidato?.nome || '?'} · {d.stato}
                    {d.codice_invito && d.stato === 'ATT' ? ` · ${d.codice_invito}` : ''}
                  </span>
                  <button type="button" className="text-sky-400 underline" onClick={() => openDuello(d.id)}>
                    Apri
                  </button>
                </li>
              ))}
            </ul>
            {activeDuello && (activeDuello.stato === 'PRE' || activeDuello.stato === 'LOB') && (
              <div className="mt-3 rounded border border-amber-700/60 bg-amber-950/20 p-3 text-xs">
                <p className="mb-2 font-bold text-amber-200">Pre-partita</p>
                {activeDuello.stato === 'LOB' && (
                  <p className="mb-2 text-gray-400">In attesa che un avversario si unisca via QR…</p>
                )}
                {activeDuello.stato === 'PRE' && (
                  <div className="space-y-2">
                    <p className="text-gray-300">
                      vs <strong>{activeDuello.sfidante?.nome}</strong>
                      {' / '}
                      <strong>{activeDuello.sfidato?.nome}</strong>
                    </p>
                    <div className="flex flex-wrap items-end gap-2">
                      <label className="text-gray-400">
                        Posta (CR)
                        <input
                          type="number"
                          min="0"
                          step="1"
                          className="ml-1 w-20 rounded border border-gray-600 bg-gray-900 px-2 py-1 text-white"
                          value={postaInput}
                          onChange={(e) => setPostaInput(e.target.value)}
                        />
                      </label>
                      <button
                        type="button"
                        disabled={duelBusy}
                        onClick={() => handlePrematch('proponi_posta', { posta_cr: Number(postaInput) || 0 })}
                        className="rounded bg-amber-900 px-2 py-1 font-bold disabled:opacity-50"
                      >
                        Proponi posta
                      </button>
                      {activeDuello.stato_prematch?.posta_ultima_proposta_da
                        && activeDuello.stato_prematch.posta_ultima_proposta_da !== activeDuello.mio_ruolo && (
                        <>
                          <button
                            type="button"
                            disabled={duelBusy}
                            onClick={() => handlePrematch('rispondi_posta', { risposta: 'accetta' })}
                            className="rounded bg-emerald-900 px-2 py-1 disabled:opacity-50"
                          >
                            Accetta posta
                          </button>
                          <button
                            type="button"
                            disabled={duelBusy}
                            onClick={() => handlePrematch('rispondi_posta', {
                              risposta: 'contro',
                              posta_cr: Number(postaInput) || 0,
                            })}
                            className="rounded bg-gray-700 px-2 py-1 disabled:opacity-50"
                          >
                            Controproponi
                          </button>
                        </>
                      )}
                    </div>
                    <p className="text-[10px] text-gray-500">
                      Posta attuale: {activeDuello.stato_prematch?.posta_cr ?? 0} CR
                      {activeDuello.stato_prematch?.posta_accettata ? ' · accettata' : ' · in negoziazione'}
                      {' · '}
                      Riserva: {Number(data?.riserva ?? selectedCharacterData?.riserva ?? 0).toFixed(0)} CR
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <select
                        className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-white"
                        defaultValue={
                          activeDuello.stato_prematch?.[activeDuello.mio_ruolo]?.posta_fonte || 'riserva'
                        }
                        onChange={(e) => handlePrematch('imposta_posta_fonte', { posta_fonte: e.target.value })}
                      >
                        <option value="riserva">Paga da riserva scommesse</option>
                        <option value="crediti">Paga da crediti</option>
                      </select>
                      <select
                        className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-white"
                        defaultValue={activeDuello.stato_prematch?.modalita_partita || 'LIV'}
                        onChange={(e) => handlePrematch('imposta_modalita', { modalita: e.target.value })}
                      >
                        <option value="LIV">Turni live</option>
                        <option value="MAN">Manuale (tavolo fisico)</option>
                      </select>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={duelBusy || mazzoIds.length !== MAZZO_DUELLO_SIZE}
                        onClick={() => handlePrematch('imposta_mazzo', { mazzo_ids: mazzoIds })}
                        className="rounded bg-indigo-900 px-2 py-1 disabled:opacity-50"
                      >
                        Conferma mazzo ({mazzoIds.length}/{MAZZO_DUELLO_SIZE})
                      </button>
                      <button
                        type="button"
                        disabled={duelBusy}
                        onClick={() => handlePrematch('segna_pronto', { pronto: true })}
                        className="rounded bg-emerald-800 px-2 py-1 font-bold disabled:opacity-50"
                      >
                        Sono pronto
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
            {activeDuello && activeDuello.stato === 'COR' && (
              <div className="mt-3 rounded border border-gray-700 bg-gray-900/80 p-3 text-xs">
                <div className="mb-2 flex justify-between font-bold">
                  <span>Influenza: {activeDuello.influenza_sfidante} — {activeDuello.influenza_sfidato}</span>
                  <span>{isMioTurno ? 'Tuo turno' : 'Turno avversario'}</span>
                </div>
                {activeDuello.effect_pending && (
                  <div className="mb-3 rounded border border-violet-700 bg-violet-950/40 p-2">
                    <p className="mb-2 font-bold text-violet-200">
                      {activeDuello.effect_pending.prompt}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {activeDuello.effect_pending.choice_kind === 'hero'
                        ? (activeDuello.effect_pending.eligible_hero_targets || []).map((row) => (
                          <button
                            key={row.target}
                            type="button"
                            disabled={duelBusy}
                            className="rounded border border-violet-600 px-2 py-1 hover:bg-violet-900/50"
                            onClick={() => handleDuelloAzione('effect_choice', {
                              choice_id: activeDuello.effect_pending.choice_id,
                              hero_target: row.target,
                            })}
                          >
                            {row.label || row.target}
                          </button>
                        ))
                        : (activeDuello.effect_pending.eligible_carta_posseduta_ids || []).map((cpId) => {
                          const meta = activeDuello.carte?.[cpId];
                          return (
                            <button
                              key={cpId}
                              type="button"
                              disabled={duelBusy}
                              className="rounded border border-violet-600 px-2 py-1 hover:bg-violet-900/50"
                              onClick={() => handleDuelloAzione('effect_choice', {
                                choice_id: activeDuello.effect_pending.choice_id,
                                carta_posseduta_id: cpId,
                              })}
                            >
                              {meta?.nome || 'carta'}
                            </button>
                          );
                        })}
                      {(activeDuello.effect_pending.min ?? 1) === 0 && (
                        <button
                          type="button"
                          disabled={duelBusy}
                          className="rounded bg-gray-700 px-2 py-1"
                          onClick={() => handleDuelloAzione('effect_choice', {
                            choice_id: activeDuello.effect_pending.choice_id,
                          })}
                        >
                          Salta
                        </button>
                      )}
                    </div>
                  </div>
                )}
                {activeDuello.modalita_partita === 'MAN' && (
                  <div className="mb-2 flex flex-wrap gap-1">
                    <button
                      type="button"
                      disabled={duelBusy}
                      className="rounded bg-gray-700 px-2 py-1"
                      onClick={() => handleDuelloAzione('imposta_influenza', {
                        influenza_sfidante: Math.max(0, activeDuello.influenza_sfidante - 1),
                      })}
                    >
                      Inf. sfidante −1
                    </button>
                    <button
                      type="button"
                      disabled={duelBusy}
                      className="rounded bg-gray-700 px-2 py-1"
                      onClick={() => handleDuelloAzione('imposta_influenza', {
                        influenza_sfidante: activeDuello.influenza_sfidante + 1,
                      })}
                    >
                      Inf. sfidante +1
                    </button>
                    <button
                      type="button"
                      disabled={duelBusy}
                      className="rounded bg-gray-700 px-2 py-1"
                      onClick={() => handleDuelloAzione('imposta_influenza', {
                        influenza_sfidato: Math.max(0, activeDuello.influenza_sfidato - 1),
                      })}
                    >
                      Inf. sfidato −1
                    </button>
                    <button
                      type="button"
                      disabled={duelBusy}
                      className="rounded bg-gray-700 px-2 py-1"
                      onClick={() => handleDuelloAzione('imposta_influenza', {
                        influenza_sfidato: activeDuello.influenza_sfidato + 1,
                      })}
                    >
                      Inf. sfidato +1
                    </button>
                  </div>
                )}
                {activeDuello.modalita_partita === 'MAN' && activeDuello.stato === 'COR' && (
                  <p className="mb-2 text-[10px] text-amber-300/80">
                    Modalità manuale: aggiorna campo e influenza come sul tavolo fisico.
                  </p>
                )}
                {activeDuello.modalita_partita === 'MAN' && activeDuello.stato === 'COR' && (
                  <div className="mb-3 rounded border border-amber-900/50 bg-amber-950/20 p-2">
                    <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-amber-300">
                      Il tuo campo
                    </p>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span>Energia: {miaEnergia}</span>
                      <button
                        type="button"
                        disabled={duelBusy}
                        className="rounded bg-gray-700 px-2 py-0.5"
                        onClick={() => aggiornaCampoManuale({ energia: Math.max(0, miaEnergia - 1) })}
                      >
                        −
                      </button>
                      <button
                        type="button"
                        disabled={duelBusy}
                        className="rounded bg-gray-700 px-2 py-0.5"
                        onClick={() => aggiornaCampoManuale({ energia: miaEnergia + 1 })}
                      >
                        +
                      </button>
                    </div>
                    <p className="mb-1 text-[10px] text-gray-400">
                      Luogo: {nomeCartaDuello(mioCampo.luogo)}
                      {mioCampo.luogo && (
                        <button
                          type="button"
                          disabled={duelBusy}
                          className="ml-2 text-amber-400 underline"
                          onClick={() => aggiornaCampoManuale({ luogo: null })}
                        >
                          rimuovi
                        </button>
                      )}
                    </p>
                    {[0, 1].map((slot) => (
                      <div key={slot} className="mb-2 border-t border-gray-800 pt-2">
                        <p className="text-[10px] text-gray-400">
                          Eroe {slot}: {nomeCartaDuello(mieiEroi[slot])}
                          {mieiEroi[slot] && (
                            <button
                              type="button"
                              disabled={duelBusy}
                              className="ml-2 text-amber-400 underline"
                              onClick={() => impostaEroeSlot(slot, null)}
                            >
                              esaurisci
                            </button>
                          )}
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {miaMano.map((cpId) => (
                            <button
                              key={`${slot}-${cpId}`}
                              type="button"
                              disabled={duelBusy}
                              className="rounded border border-gray-600 px-1 py-0.5 text-[10px]"
                              onClick={() => impostaEroeSlot(slot, cpId)}
                            >
                              {nomeCartaDuello(cpId)}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                    <p className="mt-2 text-[10px] text-gray-500">
                      Da mano → slot eroe; oppure gioca luogo:
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {miaMano.map((cpId) => (
                        <button
                          key={`luogo-${cpId}`}
                          type="button"
                          disabled={duelBusy}
                          className="rounded border border-gray-600 px-1 py-0.5 text-[10px]"
                          onClick={() => aggiornaCampoManuale({ luogo: cpId })}
                        >
                          Luogo: {nomeCartaDuello(cpId)}
                        </button>
                      ))}
                    </div>
                    {avversarioId && (
                      <p className="mt-2 text-[10px] text-gray-500">
                        Avversario — energia {campoAvversario.energia ?? 0}
                        {' · '}
                        eroi: {[0, 1].map((s) => {
                          const id = (campoAvversario.eroi || [])[s];
                          if (!id) return '—';
                          const sal = saluteEroeCampo(campoAvversario, s);
                          return `${nomeCartaDuello(id)}${sal != null ? ` (${sal})` : ''}`;
                        }).join(', ')}
                        {' · '}
                        luogo: {nomeCartaDuello(campoAvversario.luogo)}
                      </p>
                    )}
                  </div>
                )}
                {activeDuello.stato === 'COR' && activeDuello.modalita_partita !== 'MAN' && (
                  <div className="mb-2 rounded border border-gray-800 bg-gray-950/50 p-2 text-[10px] text-gray-400">
                    <p className="mb-1 font-bold uppercase tracking-wide text-gray-300">Campo</p>
                    <p>
                      Energia {miaEnergia}
                      {' · '}
                      Mazzo {mioCampo.mazzo_count ?? 0}
                      {' · '}
                      Scarto {mioCampo.scarto_count ?? 0}
                    </p>
                    <p>Luogo: {nomeCartaDuello(mioCampo.luogo)}</p>
                    {[0, 1].map((slot) => (
                      mieiEroi[slot] ? (
                        <p key={`campo-eroe-${slot}`}>
                          Eroe {slot}: {nomeCartaDuello(mieiEroi[slot])}
                          {saluteEroeCampo(mioCampo, slot) != null ? ` (${saluteEroeCampo(mioCampo, slot)} PV)` : ''}
                          {nomeOggettoSuEroe(slot) ? ` · ${nomeOggettoSuEroe(slot)}` : ''}
                        </p>
                      ) : null
                    ))}
                  </div>
                )}
                {activeDuello.stato === 'COR' && activeDuello.modalita_partita !== 'MAN' && isMioTurno && (
                  <div className="mb-2 space-y-2">
                    <div className="flex flex-wrap gap-1">
                      {miaMano.flatMap((cpId) => {
                        const meta = activeDuello.carte?.[cpId];
                        return renderGiocaCartaButtons(cpId, meta) || [];
                      })}
                      <button
                        type="button"
                        disabled={duelBusy}
                        className="rounded bg-gray-700 px-2 py-1"
                        onClick={() => handleDuelloAzione('passa')}
                      >
                        Passa
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-1 border-t border-gray-800 pt-2">
                      {[0, 1].map((slotAtk) => (
                        mieiEroi[slotAtk] ? (
                          <div key={`atk-grp-${slotAtk}`} className="flex flex-wrap gap-1">
                            <button
                              type="button"
                              disabled={duelBusy}
                              className="rounded bg-red-900 px-2 py-1"
                              onClick={() => handleDuelloAzione('attacca', { slot_eroe: slotAtk })}
                            >
                              Eroe {slotAtk} → Influenza
                            </button>
                            {[0, 1].map((slotAvv) => (
                              (campoAvversario.eroi || [])[slotAvv] ? (
                                <button
                                  key={`atk-${slotAtk}-avv-${slotAvv}`}
                                  type="button"
                                  disabled={duelBusy}
                                  className="rounded bg-red-950 px-2 py-1"
                                  onClick={() => handleDuelloAzione('attacca', {
                                    slot_eroe: slotAtk,
                                    bersaglio_eroe_slot: slotAvv,
                                  })}
                                >
                                  Eroe {slotAtk} → avv. {slotAvv}
                                  {saluteEroeCampo(campoAvversario, slotAvv) != null
                                    ? ` (${saluteEroeCampo(campoAvversario, slotAvv)} PV)`
                                    : ''}
                                </button>
                              ) : null
                            ))}
                          </div>
                        ) : null
                      ))}
                    </div>
                  </div>
                )}
                {activeDuello.stato === 'FIN' && (
                  <p className="text-emerald-300">Duello terminato.</p>
                )}
                <ul className="max-h-24 overflow-y-auto text-gray-500">
                  {(activeDuello.stato_gioco?.log || []).map((row, i) => (
                    <li key={i}>{row.msg}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* Bustine per espansione */}
          <section>
            <h3 className="mb-2 flex items-center gap-1 text-sm font-bold text-amber-300">
              <Package size={16} /> Bustine
            </h3>
            {(data.espansioni || []).length > 0 ? (
              <div className="space-y-4">
                {data.espansioni.map((esp) => (
                  <div key={esp.id || esp.slug}>
                    <h4 className="mb-1 text-xs font-bold uppercase tracking-wide text-amber-200/80">
                      {esp.nome}
                      {data.progress_espansioni?.find((p) => p.espansione_id === esp.id) && (
                        <span className="ml-2 font-normal normal-case text-gray-500">
                          {data.progress_espansioni.find((p) => p.espansione_id === esp.id).owned}
                          /
                          {data.progress_espansioni.find((p) => p.espansione_id === esp.id).total}
                        </span>
                      )}
                    </h4>
                    {esp.descrizione && (
                      <p className="mb-2 text-xs text-gray-500">{esp.descrizione}</p>
                    )}
                    <div className="grid gap-2 sm:grid-cols-2">
                      {(esp.bustine || []).map((b) => (
                        <button
                          key={b.id}
                          type="button"
                          disabled={opening}
                          onClick={() => handleApriBustina(b.id)}
                          className="rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-left hover:bg-amber-950/50 disabled:opacity-50"
                        >
                          <div className="font-bold">{b.nome}</div>
                          <div className="text-xs text-gray-400">
                            {b.carte_per_bustina} carte · {Number(b.costo_crediti).toFixed(0)} CR
                          </div>
                        </button>
                      ))}
                    </div>
                    {(esp.bustine || []).length === 0 && (
                      <p className="text-xs text-gray-600">Nessuna bustina in questa espansione.</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {(data.bustine || []).map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    disabled={opening}
                    onClick={() => handleApriBustina(b.id)}
                    className="rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-left hover:bg-amber-950/50 disabled:opacity-50"
                  >
                    <div className="font-bold">{b.nome}</div>
                    <div className="text-xs text-gray-400">
                      {b.carte_per_bustina} carte · {Number(b.costo_crediti).toFixed(0)} CR
                    </div>
                  </button>
                ))}
                {(data.bustine || []).length === 0 && (
                  <p className="text-sm text-gray-500">Nessuna bustina disponibile (configura da staff).</p>
                )}
              </div>
            )}
          </section>

          {/* Ultima apertura */}
          {lastPull?.length > 0 && (
            <section className="rounded-lg border border-violet-700 bg-violet-950/30 p-3">
              <h3 className="mb-2 text-sm font-bold text-violet-300">Ultime carte ottenute</h3>
              <div className="flex flex-wrap justify-center gap-2">
                {lastPull.map((c) => (
                  <CartaCard key={c.id} item={c} onSelect={setDetail} compact temaEnergie={data?.tema_energie} keywords={cardKeywords} />
                ))}
              </div>
            </section>
          )}

          {/* Reliquiario */}
          <section>
            <h3 className="mb-2 flex items-center gap-1 text-sm font-bold text-indigo-300">
              <Sparkles size={16} /> Reliquiario (5 slot)
            </h3>
            <div className="grid grid-cols-5 gap-2">
              {slots.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setEquipMode(idx)}
                  className="flex min-h-[72px] flex-col items-center justify-center rounded-lg border border-dashed border-gray-600 bg-gray-800/50 p-1 text-center hover:border-indigo-500"
                >
                  {item ? (
                    <span className="truncate text-[10px] font-bold">{item.carta.nome}</span>
                  ) : (
                    <span className="text-[10px] text-gray-500">Slot {idx + 1}</span>
                  )}
                </button>
              ))}
            </div>
            {(data.legami_attivi || []).length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-emerald-300">
                {data.legami_attivi.map((l) => (
                  <li key={l.id}>✦ {l.nome}: {l.descrizione}</li>
                ))}
              </ul>
            )}
          </section>

          {/* Progress espansioni */}
          {(data.progress_espansioni || []).length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-bold text-gray-300">Espansioni</h3>
              <ul className="space-y-1 text-xs">
                {data.progress_espansioni.map((s) => (
                  <li key={s.espansione_id} className="flex justify-between text-gray-400">
                    <span>{s.nome}</span>
                    <span>{s.owned}/{s.total}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Progress set legacy */}
          {(data.progress_sets || []).length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-bold text-gray-300">Cronache</h3>
              <ul className="space-y-1 text-xs">
                {data.progress_sets.map((s) => (
                  <li key={s.set_collezione} className="flex justify-between text-gray-400">
                    <span>{s.set_collezione}</span>
                    <span>{s.owned}/{s.total}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Collezione */}
          <section>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-gray-300">
                Collezione ({collezioneView.totalCopie} carte · {collezioneView.uniqueCount} uniche
                {hasColFilters ? ` · ${collezioneView.filteredCount} mostrate` : ''})
              </h3>
              <button
                type="button"
                onClick={() => setColFiltersOpen((v) => !v)}
                className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-bold ${colFiltersOpen || hasColFilters ? 'bg-violet-800 text-white' : 'bg-gray-800 text-gray-400'}`}
              >
                <SlidersHorizontal size={14} />
                Filtri
              </button>
            </div>

            {colFiltersOpen && (
              <div className="mb-3 space-y-2 rounded-lg border border-gray-700 bg-gray-900/60 p-3">
                <input
                  type="search"
                  value={colSearch}
                  onChange={(e) => setColSearch(e.target.value)}
                  placeholder="Cerca nome, codice, espansione…"
                  className="w-full rounded border border-gray-600 bg-gray-950 px-2 py-1.5 text-sm text-white placeholder:text-gray-500"
                />
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                  <select
                    value={colTipo}
                    onChange={(e) => setColTipo(e.target.value)}
                    className="rounded border border-gray-600 bg-gray-950 px-2 py-1.5 text-xs text-white"
                  >
                    <option value="">Tipo — tutti</option>
                    {Object.entries(CARTA_TIPO_LABEL).map(([k, label]) => (
                      <option key={k} value={k}>{label}</option>
                    ))}
                  </select>
                  <select
                    value={colEnergia}
                    onChange={(e) => setColEnergia(e.target.value)}
                    className="rounded border border-gray-600 bg-gray-950 px-2 py-1.5 text-xs text-white"
                  >
                    <option value="">Energia — tutte</option>
                    {Object.entries(CARTA_ENERGIA_LABEL).map(([k, label]) => (
                      <option key={k} value={k}>{label}</option>
                    ))}
                  </select>
                  <select
                    value={colRarita}
                    onChange={(e) => setColRarita(e.target.value)}
                    className="rounded border border-gray-600 bg-gray-950 px-2 py-1.5 text-xs text-white"
                  >
                    <option value="">Rarità — tutte</option>
                    {Object.entries(CARTA_RARITA_LABEL).map(([k, label]) => (
                      <option key={k} value={k}>{label}</option>
                    ))}
                  </select>
                  <select
                    value={colEspansione}
                    onChange={(e) => setColEspansione(e.target.value)}
                    className="rounded border border-gray-600 bg-gray-950 px-2 py-1.5 text-xs text-white"
                  >
                    <option value="">Espansione — tutte</option>
                    {espansioniCollezione.map((esp) => (
                      <option key={esp.id} value={esp.id}>{esp.nome}</option>
                    ))}
                  </select>
                  <select
                    value={colSort}
                    onChange={(e) => setColSort(e.target.value)}
                    className="col-span-2 rounded border border-gray-600 bg-gray-950 px-2 py-1.5 text-xs text-white sm:col-span-1"
                  >
                    {COLLEZIONE_SORT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <label className="flex items-center gap-2 text-xs text-gray-400">
                  <input
                    type="checkbox"
                    checked={colSoloLibere}
                    onChange={(e) => setColSoloLibere(e.target.checked)}
                    className="rounded border-gray-600"
                  />
                  Solo carte non tutte equipaggiate nel reliquiario
                </label>
                {hasColFilters && (
                  <button
                    type="button"
                    onClick={() => {
                      setColSearch('');
                      setColTipo('');
                      setColEnergia('');
                      setColRarita('');
                      setColEspansione('');
                      setColSoloLibere(false);
                    }}
                    className="text-xs font-bold text-violet-300 hover:text-violet-200"
                  >
                    Azzera filtri
                  </button>
                )}
              </div>
            )}

            {!colFiltersOpen && (
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <select
                  value={colSort}
                  onChange={(e) => setColSort(e.target.value)}
                  className="rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-gray-300"
                  aria-label="Ordinamento collezione"
                >
                  {COLLEZIONE_SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                {hasColFilters && (
                  <span className="text-[10px] text-violet-300">Filtri attivi — apri pannello Filtri</span>
                )}
              </div>
            )}

            <div className="flex flex-wrap justify-center gap-3">
              {collezioneView.stacks.map((stack) => (
                <CollezioneStackCard
                  key={stack.key}
                  stack={stack}
                  onSelect={setDetailStack}
                  temaEnergie={data?.tema_energie}
                  keywords={cardKeywords}
                />
              ))}
            </div>
            {collezioneView.totalCopie === 0 && (
              <p className="text-sm text-gray-500">
                Nessuna carta in collezione.
                {(data?.bustine?.length > 0 || (data?.espansioni || []).some((e) => (e.bustine || []).length > 0))
                  ? ' Scorri alla sezione Bustine e aprine una per iniziare.'
                  : ' Il catalogo demo va caricato con seed-carte-esempio; le carte si ottengono aprendo bustine.'}
              </p>
            )}
            {collezioneView.totalCopie > 0 && collezioneView.filteredCount === 0 && (
              <p className="text-sm text-gray-500">Nessuna carta corrisponde ai filtri selezionati.</p>
            )}
          </section>
        </>
      )}

      {(detail || detailStack) && (
        <CartaDetailModal
          item={detail}
          stack={detailStack}
          onClose={() => {
            setDetail(null);
            setDetailStack(null);
          }}
          temaEnergie={data?.tema_energie}
          keywords={cardKeywords}
        />
      )}

      {equipMode != null && (
        <div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/70 p-4 sm:items-center" onClick={() => setEquipMode(null)}>
          <div className="max-h-[70vh] w-full max-w-lg overflow-y-auto rounded-xl border border-gray-600 bg-gray-900 p-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-3 font-bold">Equipaggia slot {equipMode + 1}</h3>
            <button
              type="button"
              className="mb-3 w-full rounded border border-gray-600 py-2 text-sm text-gray-400 hover:bg-gray-800"
              onClick={() => handleEquip(equipMode, null)}
            >
              Svuota slot
            </button>
            <div className="flex flex-wrap justify-center gap-2">
              {(data?.carte || []).map((c) => (
                <CartaCard
                  key={c.id}
                  item={c}
                  compact
                  onSelect={() => handleEquip(equipMode, c.id)}
                  temaEnergie={data?.tema_energie}
                  keywords={cardKeywords}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
