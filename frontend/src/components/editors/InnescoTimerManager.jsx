import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import { StaffToolShell } from '../../staff/StaffToolShell';
import { StaffModalTabs } from '../../staff/StaffCrudUi';
import StaffEditorModal from './StaffEditorModal';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffQrBadge from './StaffQrBadge';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import StaffMinigiocoPageToolbar from './StaffMinigiocoPageToolbar';
import StaffMinigiocoUsaDefaultToggle from './StaffMinigiocoUsaDefaultToggle';
import SearchableSelect from './SearchableSelect';
import useStaffMinigiocoQr from '../../hooks/useStaffMinigiocoQr';
import { useDebounce } from '../../hooks/useDebounce';
import {
  applyDefaultMinigiocoToQr,
  MINIGIOCO_PAGE_KEYS,
  patchStaffListMinigiocoDefault,
  unwrapStaffList,
} from '../../utils/staffMinigiocoDefaults';
import {
  associaQrDiretto,
  staffGetInnescoTimers,
  staffCreateInnescoTimer,
  staffUpdateInnescoTimer,
  staffDeleteInnescoTimer,
  staffAggiungiIstanzeInnescoTimer,
  staffInnescoTimerEventi,
  staffGetEre,
  staffGetRegioni,
  staffGetKorps,
  staffGetPersonaggi,
} from '../../api';

const TARGET_LABEL = {
  globale: 'A tutti',
  evento: 'Presenti all\'evento',
  korp: 'Solo KORP',
  personaggi: 'Lista PG',
  filtri: 'Filtri avanzati',
};

const emptyForm = () => ({
  nome: '',
  testo: '',
  modalita_target: 'globale',
  durata_secondi: 60,
  max_cariche: 1,
  rigenera_cariche_ogni_secondi: '',
  segnale_luminoso: true,
  target_evento_id: null,
  target_ere_ids: [],
  target_regioni_ids: [],
  target_korps_ids: [],
  target_personaggi: [],
  numero_istanze: 1,
});

const TargetCheckboxGroup = ({ title, options, selectedIds, onChange }) => {
  const normalizedSelected = Array.isArray(selectedIds) ? selectedIds : [];
  return (
    <div className="text-sm border border-gray-700 rounded p-2 bg-gray-900/30">
      <div className="flex items-center justify-between mb-2 gap-2">
        <span className="font-semibold text-gray-200">{title}</span>
        <div className="flex gap-2 text-[10px]">
          <button
            type="button"
            className="min-h-11 px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
            onClick={() => onChange(options.map((o) => o.id))}
          >
            Tutti
          </button>
          <button
            type="button"
            className="min-h-11 px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
            onClick={() => onChange([])}
          >
            Nessuno
          </button>
        </div>
      </div>
      {options.length === 0 ? (
        <p className="text-xs text-gray-500">Nessuna opzione disponibile.</p>
      ) : (
        <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
          {options.map((row) => {
            const checked = normalizedSelected.includes(row.id);
            return (
              <label key={row.id} className="flex items-center gap-2 min-h-11 text-xs text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...normalizedSelected, row.id]);
                    } else {
                      onChange(normalizedSelected.filter((id) => id !== row.id));
                    }
                  }}
                />
                <span className="break-words">{row.nome}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
};

const PersonaggiTargetPicker = ({ selected, onChange, onLogout }) => {
  const [query, setQuery] = useState('');
  const debounced = useDebounce(query, 250);
  const [hits, setHits] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const q = (debounced || '').trim();
    if (q.length < 2) {
      setHits([]);
      return undefined;
    }
    let cancelled = false;
    setBusy(true);
    staffGetPersonaggi({ q, tipo: 'pg', morto: 'vivo' }, onLogout)
      .then((data) => {
        if (cancelled) return;
        const rows = Array.isArray(data) ? data : (data?.results || []);
        setHits(rows);
      })
      .catch(() => {
        if (!cancelled) setHits([]);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced, onLogout]);

  const selectedIds = new Set((selected || []).map((p) => p.id));

  return (
    <div className="space-y-2">
      <label className="block text-sm">
        Cerca personaggio
        <input
          className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
          value={query}
          placeholder="Nome PG o giocatore (almeno 2 lettere)"
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      {busy && <p className="text-xs text-gray-500">Ricerca…</p>}
      {hits.length > 0 && (
        <ul className="max-h-40 overflow-y-auto border border-gray-700 rounded divide-y divide-gray-800">
          {hits.filter((row) => !selectedIds.has(row.id)).map((row) => {
            const giocatore = row.proprietario_nome || row.proprietario_username || '';
            return (
              <li key={row.id}>
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 min-h-11 hover:bg-gray-800"
                  onClick={() => onChange([
                    ...(selected || []),
                    { id: row.id, nome: row.nome, giocatore },
                  ])}
                >
                  <div className="font-semibold text-sm break-words">{row.nome}</div>
                  {giocatore ? <div className="text-[11px] text-gray-400 break-words">{giocatore}</div> : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <ul className="space-y-1">
        {(selected || []).map((pg) => (
          <li key={pg.id} className="flex items-center justify-between gap-2 rounded border border-gray-700 px-3 py-2">
            <div className="min-w-0">
              <div className="font-semibold text-sm break-words">{pg.nome}</div>
              {pg.giocatore ? <div className="text-[11px] text-gray-400 break-words">{pg.giocatore}</div> : null}
            </div>
            <button
              type="button"
              className="min-h-11 shrink-0 px-3 text-xs bg-red-900 rounded"
              onClick={() => onChange((selected || []).filter((row) => row.id !== pg.id))}
            >
              Togli
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

const InnescoTimerManager = ({ onBack, onLogout }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [scanningId, setScanningId] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const [msg, setMsg] = useState('');
  const [modalTab, setModalTab] = useState('dati');
  const [ereOptions, setEreOptions] = useState([]);
  const [regioniOptions, setRegioniOptions] = useState([]);
  const [korpOptions, setKorpOptions] = useState([]);
  const [eventiOptions, setEventiOptions] = useState([]);
  const [quanteByGruppo, setQuanteByGruppo] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetInnescoTimers(onLogout);
      setItems(unwrapStaffList(data));
    } catch (e) {
      setMsg(e.message || 'Errore caricamento');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const loadTargets = async () => {
      try {
        const [ere, regioni, korps, eventi] = await Promise.all([
          staffGetEre(onLogout),
          staffGetRegioni(onLogout),
          staffGetKorps(onLogout),
          staffInnescoTimerEventi(onLogout),
        ]);
        setEreOptions(Array.isArray(ere) ? ere : (ere?.results || []));
        setRegioniOptions(Array.isArray(regioni) ? regioni : (regioni?.results || []));
        setKorpOptions(Array.isArray(korps) ? korps : (korps?.results || []));
        setEventiOptions(Array.isArray(eventi) ? eventi : (eventi?.results || []));
      } catch (_e) {
        /* opzionali: il form resta usabile in modalità «A tutti» */
      }
    };
    loadTargets();
  }, [onLogout]);

  const gruppi = useMemo(() => {
    const map = new Map();
    items.forEach((row) => {
      const gid = row.gruppo_id || `solo-${row.id}`;
      if (!map.has(gid)) map.set(gid, []);
      map.get(gid).push(row);
    });
    return [...map.values()].map((list) => {
      const istanze = [...list].sort((a, b) => (a.ordine_istanza || 0) - (b.ordine_istanza || 0) || a.id - b.id);
      return { gruppoId: istanze[0].gruppo_id || `solo-${istanze[0].id}`, head: istanze[0], istanze };
    });
  }, [items]);

  const toPayload = (f, { includeCount } = {}) => {
    const rig = f.rigenera_cariche_ogni_secondi;
    const body = {
      nome: f.nome,
      testo: f.testo || '',
      modalita_target: f.modalita_target,
      durata_secondi: parseInt(f.durata_secondi, 10) || 60,
      max_cariche: parseInt(f.max_cariche, 10) || 0,
      rigenera_cariche_ogni_secondi: rig === '' || rig == null ? null : parseInt(rig, 10),
      segnale_luminoso: !!f.segnale_luminoso,
      target_evento_id: f.target_evento_id || null,
      target_ere_ids: f.target_ere_ids || [],
      target_regioni_ids: f.target_regioni_ids || [],
      target_korps_ids: f.target_korps_ids || [],
      target_personaggi_ids: (f.target_personaggi || []).map((p) => p.id),
      applica_al_gruppo: true,
    };
    if (includeCount) {
      body.numero_istanze = Math.max(1, Math.min(20, parseInt(f.numero_istanze, 10) || 1));
    }
    return body;
  };

  const save = async () => {
    if (!editing?.nome?.trim()) {
      setMsg('Il nome è obbligatorio');
      return;
    }
    if (editing.modalita_target === 'evento' && !editing.target_evento_id) {
      setMsg('Seleziona l\'evento');
      return;
    }
    if (editing.modalita_target === 'korp' && !(editing.target_korps_ids || []).length) {
      setMsg('Seleziona almeno una KORP');
      return;
    }
    if (editing.modalita_target === 'personaggi' && !(editing.target_personaggi || []).length) {
      setMsg('Aggiungi almeno un personaggio');
      return;
    }
    try {
      const body = toPayload(editing, { includeCount: !editing.id });
      if (editing.id) {
        await staffUpdateInnescoTimer(editing.id, body, onLogout);
      } else {
        await staffCreateInnescoTimer(body, onLogout);
      }
      setEditing(null);
      setMsg('Salvato. Le modifiche valgono per tutte le istanze del timer.');
      load();
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio');
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Eliminare questa istanza del timer? Il QR collegato si stacca.')) return;
    try {
      await staffDeleteInnescoTimer(id, onLogout);
      load();
    } catch (e) {
      setMsg(e.message || 'Errore eliminazione');
    }
  };

  const aggiungiIstanze = async (head) => {
    const raw = quanteByGruppo[head.gruppo_id] || '1';
    const quante = Math.max(1, Math.min(20, parseInt(raw, 10) || 1));
    try {
      await staffAggiungiIstanzeInnescoTimer(head.id, quante, onLogout);
      setMsg(`Aggiunte ${quante} istanze. Associa un QR a ciascuna.`);
      load();
    } catch (e) {
      setMsg(e.message || 'Errore creazione istanze');
    }
  };

  const salvaEtichetta = async (istanza, valore) => {
    if ((istanza.etichetta_istanza || '') === valore) return;
    try {
      await staffUpdateInnescoTimer(
        istanza.id,
        { etichetta_istanza: valore, applica_al_gruppo: false },
        onLogout,
      );
      load();
    } catch (e) {
      setMsg(e.message || 'Errore etichetta');
    }
  };

  const korpRimasti = korpOptions.filter((k) => !(editing?.target_korps_ids || []).includes(k.id));

  return (
    <StaffToolShell maxWidth="4xl" className="space-y-4">
      {msg && <div className="text-xs text-amber-200 border border-amber-800/40 rounded px-2 py-1 break-words">{msg}</div>}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold">Innesco timer (QR)</h2>
        <button
          type="button"
          className="min-h-11 px-3 py-2 bg-indigo-600 rounded text-sm"
          onClick={() => { setModalTab('dati'); setEditing(emptyForm()); }}
        >
          Nuovo
        </button>
      </div>
      <p className="text-xs text-gray-400">
        Alla scansione parte il countdown sui telefoni dei destinatari. Puoi creare più istanze identiche:
        ognuna ha il suo QR e il suo countdown, le modifiche al timer valgono per tutto il gruppo.
      </p>
      <StaffMinigiocoPageToolbar
        pageKey={MINIGIOCO_PAGE_KEYS.innescoTimer}
        pageLabel="Innesco timer"
        onLogout={onLogout}
      />
      {loading ? (
        <p className="text-gray-400">Caricamento…</p>
      ) : (
        <ul className="space-y-3">
          {gruppi.map((gruppo) => (
            <li key={gruppo.gruppoId} className="border border-gray-700 rounded-lg p-3 space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="font-semibold break-words">{gruppo.head.nome}</div>
                  <div className="text-[11px] text-gray-400">
                    {gruppo.head.durata_secondi}s · {TARGET_LABEL[gruppo.head.modalita_target] || gruppo.head.modalita_target}
                    {' '}· {gruppo.istanze.length} {gruppo.istanze.length === 1 ? 'istanza' : 'istanze'}
                  </div>
                </div>
                <button
                  type="button"
                  className="min-h-11 text-xs px-3 py-2 bg-gray-700 rounded shrink-0"
                  onClick={() => {
                    setModalTab('dati');
                    setEditing({ ...emptyForm(), ...gruppo.head, numero_istanze: 1 });
                  }}
                >
                  Modifica gruppo
                </button>
              </div>
              <ul className="space-y-2">
                {gruppo.istanze.map((ist) => (
                  <li key={ist.id} className="rounded border border-gray-800 bg-gray-900/40 p-2 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <StaffQrBadge hasQr={ist.has_qrcode} />
                      <input
                        className="min-h-11 flex-1 min-w-[8rem] px-2 py-1 rounded bg-gray-800 border border-gray-600 text-sm"
                        defaultValue={ist.etichetta_istanza || `Istanza ${ist.ordine_istanza || 1}`}
                        aria-label="Etichetta istanza"
                        onBlur={(e) => salvaEtichetta(ist, e.target.value.trim())}
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <StaffMinigiocoUsaDefaultToggle
                        qrcodeId={ist.qrcode_id}
                        usaDefault={ist.minigioco_usa_default}
                        pageKey={MINIGIOCO_PAGE_KEYS.innescoTimer}
                        onLogout={onLogout}
                        compact
                        onChange={(val) => patchStaffListMinigiocoDefault(setItems, ist.id, val)}
                      />
                      <button
                        type="button"
                        className="min-h-11 text-xs px-3 py-1 bg-indigo-800 rounded"
                        onClick={() => openMinigioco(ist.qrcode_id, ist.nome)}
                        disabled={!ist.qrcode_id}
                        title={ist.qrcode_id ? 'Configura minigioco QR' : 'Associa prima un QR'}
                      >
                        Minigioco
                      </button>
                      <button
                        type="button"
                        className="min-h-11 text-xs px-3 py-1 bg-violet-800 rounded"
                        onClick={() => setScanningId(ist.id)}
                      >
                        Associa QR
                      </button>
                      <button
                        type="button"
                        className="min-h-11 text-xs px-3 py-1 bg-red-900 rounded"
                        onClick={() => remove(ist.id)}
                      >
                        Elimina
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap items-end gap-2">
                <label className="text-xs text-gray-300">
                  Istanze da aggiungere
                  <input
                    type="number"
                    min="1"
                    max="20"
                    className="mt-1 block w-24 min-h-11 px-2 rounded bg-gray-800 border border-gray-600"
                    value={quanteByGruppo[gruppo.gruppoId] ?? '1'}
                    onChange={(e) => setQuanteByGruppo((prev) => ({ ...prev, [gruppo.gruppoId]: e.target.value }))}
                  />
                </label>
                <button
                  type="button"
                  className="min-h-11 text-xs px-3 py-2 bg-amber-800 rounded"
                  onClick={() => aggiungiIstanze(gruppo.head)}
                >
                  Crea istanze
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {editing && (
        <StaffEditorModal
          title={editing.id ? `Innesco: ${editing.nome || 'senza nome'}` : 'Nuovo innesco'}
          size="lg"
          onClose={() => setEditing(null)}
          onSave={save}
          saveLabel="Salva"
        >
          <StaffModalTabs
            tabs={[
              { id: 'dati', label: 'Dati timer' },
              { id: 'minigioco', label: 'Minigioco' },
            ]}
            active={modalTab}
            onChange={setModalTab}
          />
          {modalTab === 'dati' && (
          <div className="space-y-3">
          <label className="block text-sm">
            Nome (mostrato sul timer)
            <input
              className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
              value={editing.nome}
              onChange={(e) => setEditing({ ...editing, nome: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Descrizione (opzionale)
            <textarea
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600 text-sm min-h-[60px]"
              value={editing.testo || ''}
              onChange={(e) => setEditing({ ...editing, testo: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <label className="text-sm">
              Durata (sec)
              <input
                type="number"
                className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
                value={editing.durata_secondi}
                onChange={(e) => setEditing({ ...editing, durata_secondi: e.target.value })}
              />
            </label>
            <label className="text-sm">
              Max cariche (0 = illimitato)
              <input
                type="number"
                className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
                value={editing.max_cariche}
                onChange={(e) => setEditing({ ...editing, max_cariche: e.target.value })}
              />
            </label>
          </div>
          {!editing.id && (
            <label className="block text-sm">
              Quante istanze creare (ognuna avrà il proprio QR)
              <input
                type="number"
                min="1"
                max="20"
                className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
                value={editing.numero_istanze}
                onChange={(e) => setEditing({ ...editing, numero_istanze: e.target.value })}
              />
            </label>
          )}
          <label className="block text-sm">
            Rigenera cariche ogni (sec, vuoto = no)
            <input
              type="number"
              className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
              value={editing.rigenera_cariche_ogni_secondi ?? ''}
              onChange={(e) => setEditing({ ...editing, rigenera_cariche_ogni_secondi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Chi riceve il timer
            <select
              className="w-full mt-1 min-h-11 px-2 py-2 rounded bg-gray-800 border border-gray-600"
              value={editing.modalita_target}
              onChange={(e) => setEditing({ ...editing, modalita_target: e.target.value })}
            >
              <option value="globale">A tutti!</option>
              <option value="evento">Solo giocatori presenti all&apos;evento</option>
              <option value="korp">Solo KORP</option>
              <option value="personaggi">Lista di personaggi</option>
              <option value="filtri">Filtri avanzati (era, regione e KORP insieme)</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm min-h-11">
            <input
              type="checkbox"
              checked={!!editing.segnale_luminoso}
              onChange={(e) => setEditing({ ...editing, segnale_luminoso: e.target.checked })}
            />
            Segnale luminoso in-app
          </label>
          {editing.modalita_target === 'evento' && (
            <div className="space-y-1">
              <span className="text-sm">Evento</span>
              <SearchableSelect
                options={eventiOptions}
                value={editing.target_evento_id}
                onChange={(id) => setEditing({ ...editing, target_evento_id: id })}
                labelKey="titolo"
                placeholder="Seleziona l'evento…"
              />
              <p className="text-[11px] text-gray-400">
                Ricevono il timer i personaggi iscritti tra i partecipanti di questo evento.
              </p>
            </div>
          )}
          {editing.modalita_target === 'korp' && (
            <div className="space-y-2">
              <span className="text-sm">KORP</span>
              <SearchableSelect
                options={korpRimasti}
                value={null}
                onChange={(id) => {
                  if (id == null) return;
                  const ids = editing.target_korps_ids || [];
                  if (ids.includes(id)) return;
                  setEditing({ ...editing, target_korps_ids: [...ids, id] });
                }}
                placeholder="Aggiungi una KORP…"
              />
              <ul className="flex flex-wrap gap-2">
                {(editing.target_korps_ids || []).map((id) => {
                  const row = korpOptions.find((k) => k.id === id);
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        className="min-h-11 px-3 rounded-full bg-gray-800 border border-gray-600 text-xs"
                        onClick={() => setEditing({
                          ...editing,
                          target_korps_ids: (editing.target_korps_ids || []).filter((x) => x !== id),
                        })}
                      >
                        {row?.nome || id} ×
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          {editing.modalita_target === 'personaggi' && (
            <PersonaggiTargetPicker
              selected={editing.target_personaggi || []}
              onChange={(list) => setEditing({ ...editing, target_personaggi: list })}
              onLogout={onLogout}
            />
          )}
          {editing.modalita_target === 'filtri' && (
            <div className="space-y-2">
              <p className="text-xs text-amber-200/90 bg-amber-950/40 border border-amber-800/40 rounded p-2">
                Il personaggio riceve il timer solo se rispetta tutti i filtri che hai compilato.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <TargetCheckboxGroup
                  title="Ere target"
                  options={ereOptions}
                  selectedIds={editing.target_ere_ids}
                  onChange={(ids) => setEditing({ ...editing, target_ere_ids: ids })}
                />
                <TargetCheckboxGroup
                  title="Regioni target"
                  options={regioniOptions}
                  selectedIds={editing.target_regioni_ids}
                  onChange={(ids) => setEditing({ ...editing, target_regioni_ids: ids })}
                />
                <TargetCheckboxGroup
                  title="KORP target"
                  options={korpOptions}
                  selectedIds={editing.target_korps_ids}
                  onChange={(ids) => setEditing({ ...editing, target_korps_ids: ids })}
                />
              </div>
            </div>
          )}
          </div>
          )}
          {modalTab === 'minigioco' && (
            <div className="space-y-3">
              {!editing.id || !editing.qrcode_id ? (
                <p className="text-sm text-gray-400">
                  Salva l&apos;innesco e associa un QR all&apos;istanza per configurare il minigioco.
                </p>
              ) : (
                <StaffMinigiocoQrSection qrcodeId={editing.qrcode_id} onLogout={onLogout} />
              )}
            </div>
          )}
        </StaffEditorModal>
      )}

      {scanningId && (
        <div className="fixed inset-0 z-[160] bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center gap-2 bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a questa istanza</span>
            <button type="button" onClick={() => setScanningId(null)} className="min-h-11 px-4 py-2 bg-red-600 rounded">
              Chiudi
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                try {
                  await associaQrDiretto(scanningId, qr_id, onLogout);
                  await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.innescoTimer, qr_id, onLogout);
                  setScanningId(null);
                  setMsg('QR associato a questa istanza.');
                  load();
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    setPendingQrConflict({
                      targetId: scanningId,
                      qrId: qr_id,
                      errorData: error.data,
                    });
                    setScanningId(null);
                  } else {
                    setMsg(error.message || 'Errore');
                  }
                }
              }}
              onLogout={onLogout}
            />
          </div>
        </div>
      )}

      {minigiocoModal}

      <ConfirmDialog
        open={Boolean(pendingQrConflict)}
        title="QR già associato"
        message=""
        confirmLabel="Sostituisci associazione"
        confirmTone="warning"
        onCancel={() => setPendingQrConflict(null)}
        onConfirm={async () => {
          const p = pendingQrConflict;
          if (!p?.qrId || !p?.targetId) return;
          try {
            await associaQrDiretto(p.targetId, p.qrId, onLogout, true);
            await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.innescoTimer, p.qrId, onLogout);
            setPendingQrConflict(null);
            setScanningId(null);
            setMsg('QR associato (forzato).');
            load();
          } catch (e) {
            setMsg(e.message || 'Errore');
          }
        }}
      >
        {pendingQrConflict?.errorData ? (
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questa istanza del timer" />
        ) : null}
      </ConfirmDialog>
    </StaffToolShell>
  );
};

export default memo(InnescoTimerManager);
