import React, { useState, useEffect, useCallback } from 'react';
import { Puzzle, Save, Loader } from 'lucide-react';
import RequisitiListaEditor, { RegoleGruppoListaEditor } from './RequisitiAccessoEditor';
import { staffGetMinigiocoQrConfig, staffSaveMinigiocoQrConfig } from '../../api';
import useRequisitiAccessoLookup from '../../hooks/useRequisitiAccessoLookup';

const TIPO_OPTS = [
  { id: 'sliding_puzzle', label: 'Sliding puzzle' },
  { id: 'memory', label: 'Memory' },
  { id: 'rotate_tiles', label: 'Tessere rotabili' },
  { id: 'simon', label: 'Sequenza (Simon)' },
  { id: 'pattern_lock', label: 'Pattern lock' },
  { id: 'pipe_connect', label: 'Collega i tubi' },
];

const DIFFICOLTA_INFO = {
  1: 'facile',
  2: 'media',
  3: 'difficile',
  4: 'molto difficile',
};

const TIMER_AZIONE_OPTS = [
  { id: 'attiva_qr', label: 'Attiva il QR' },
  { id: 'blocca_qr', label: 'Blocca il QR (non riattivabile)' },
  { id: 'reset_minigioco', label: 'Reset minigioco' },
];

const SBLOCCO_OPTS = [
  { id: 'ogni_scansione', label: 'Minigioco a ogni scansione' },
  { id: 'permanente', label: 'Una volta risolto, per sempre' },
  { id: 'temporaneo', label: 'Sblocco temporaneo (N secondi)' },
];

const ALL_TIPI = TIPO_OPTS.map((o) => o.id);

export const emptyMinigiocoConfig = () => ({
  attivo: false,
  tipi_abilitati: [...ALL_TIPI],
  difficolta: 4,
  requisiti_attivazione: [],
  esclusioni_minigioco: [],
  regole_difficolta: [],
  messaggio_pre: '',
  messaggio_vittoria: '',
  timer_secondi: '',
  timer_scadenza_azione: 'reset_minigioco',
  usa_biblioteca_se_vuota: true,
  modalita_sblocco: 'permanente',
  sblocco_secondi: '',
  immagine_url: null,
});

const emptyConfig = emptyMinigiocoConfig;

const MinigiocoQrEditor = ({
  qrId,
  onLogout,
  lookup: lookupProp = {},
  templateMode = false,
  templateConfig,
  onTemplateChange,
}) => {
  const { lookup, loading: lookupLoading } = useRequisitiAccessoLookup(onLogout, lookupProp);
  const [config, setConfigRaw] = useState(emptyConfig());

  const setConfig = useCallback(
    (updater) => {
      setConfigRaw((prev) => {
        const next = typeof updater === 'function' ? updater(prev) : updater;
        if (templateMode && onTemplateChange) {
          onTemplateChange(next);
        }
        return next;
      });
    },
    [templateMode, onTemplateChange],
  );
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [removeImage, setRemoveImage] = useState(false);

  useEffect(() => {
    if (!templateMode) return;
    const cfg = templateConfig
      ? { ...emptyConfig(), ...templateConfig }
      : emptyConfig();
    if (!Array.isArray(cfg.tipi_abilitati) || cfg.tipi_abilitati.length === 0) {
      cfg.tipi_abilitati = [...ALL_TIPI];
    }
    setConfigRaw(cfg);
  }, [templateMode, templateConfig]);

  const load = useCallback(async () => {
    if (templateMode || !qrId) return;
    setLoading(true);
    setMsg('');
    try {
      const data = await staffGetMinigiocoQrConfig(qrId, onLogout);
      const cfg = data?.config ? { ...emptyConfig(), ...data.config } : emptyConfig();
      if (!Array.isArray(cfg.tipi_abilitati) || cfg.tipi_abilitati.length === 0) {
        cfg.tipi_abilitati = [...ALL_TIPI];
      }
      if (!Array.isArray(cfg.esclusioni_minigioco)) cfg.esclusioni_minigioco = [];
      if (!Array.isArray(cfg.regole_difficolta)) cfg.regole_difficolta = [];
      if (cfg.timer_secondi == null) cfg.timer_secondi = '';
      if (cfg.sblocco_secondi == null) cfg.sblocco_secondi = '';
      if (!cfg.modalita_sblocco) cfg.modalita_sblocco = 'permanente';
      setConfig(cfg);
      setImageFile(null);
      setRemoveImage(false);
    } catch (e) {
      setMsg(e.message || 'Errore caricamento config minigioco');
    } finally {
      setLoading(false);
    }
  }, [qrId, onLogout, templateMode]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleTipo = (tipoId) => {
    setConfig((c) => {
      const set = new Set(c.tipi_abilitati || []);
      if (set.has(tipoId)) {
        if (set.size <= 1) return c;
        set.delete(tipoId);
      } else {
        set.add(tipoId);
      }
      return { ...c, tipi_abilitati: [...set] };
    });
  };

  const save = async () => {
    if (!qrId) return;
    if (!config.tipi_abilitati?.length) {
      setMsg('Seleziona almeno un tipo di gioco.');
      return;
    }
    if (config.modalita_sblocco === 'temporaneo') {
      const sec = Number(config.sblocco_secondi);
      if (!sec || sec < 1) {
        setMsg('Indica i secondi di sblocco (≥ 1) per la modalità temporanea.');
        return;
      }
    }

    setSaving(true);
    setMsg('');
    try {
      const fd = new FormData();
      fd.append('attivo', config.attivo ? 'true' : 'false');
      fd.append('usa_biblioteca_se_vuota', config.usa_biblioteca_se_vuota ? 'true' : 'false');
      fd.append('tipi_abilitati', JSON.stringify(config.tipi_abilitati));
      fd.append('difficolta', String(Number(config.difficolta) || 4));
      fd.append('messaggio_pre', config.messaggio_pre || '');
      fd.append('messaggio_vittoria', config.messaggio_vittoria || '');
      fd.append('timer_scadenza_azione', config.timer_scadenza_azione);
      fd.append('modalita_sblocco', config.modalita_sblocco || 'permanente');
      if (config.modalita_sblocco === 'temporaneo' && config.sblocco_secondi !== '') {
        fd.append('sblocco_secondi', String(config.sblocco_secondi));
      } else {
        fd.append('sblocco_secondi', '');
      }
      fd.append('requisiti_attivazione', JSON.stringify(config.requisiti_attivazione || []));
      fd.append('esclusioni_minigioco', JSON.stringify(config.esclusioni_minigioco || []));
      fd.append('regole_difficolta', JSON.stringify(config.regole_difficolta || []));
      if (config.timer_secondi !== '' && config.timer_secondi != null) {
        fd.append('timer_secondi', String(config.timer_secondi));
      } else {
        fd.append('timer_secondi', '');
      }
      if (removeImage) fd.append('rimuovi_immagine', 'true');
      if (imageFile) fd.append('immagine', imageFile);
      const data = await staffSaveMinigiocoQrConfig(qrId, fd, onLogout);
      const cfg = data?.config ? { ...emptyConfig(), ...data.config } : emptyConfig();
      if (cfg.timer_secondi == null) cfg.timer_secondi = '';
      if (cfg.sblocco_secondi == null) cfg.sblocco_secondi = '';
      if (!cfg.modalita_sblocco) cfg.modalita_sblocco = 'permanente';
      setConfig(cfg);
      setImageFile(null);
      setRemoveImage(false);
      setMsg('Configurazione salvata.');
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio');
    } finally {
      setSaving(false);
    }
  };

  if (!templateMode && !qrId) return null;

  return (
    <div className={`${templateMode ? '' : 'mt-6'} p-4 bg-gray-800/60 rounded-lg border border-indigo-700/50`}>
      {!templateMode ? (
        <div className="flex items-center gap-2 mb-3 text-indigo-300 font-bold uppercase text-sm tracking-wide">
          <Puzzle size={16} />
          Minigioco QR
        </div>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Loader className="w-4 h-4 animate-spin" /> Caricamento…
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!config.attivo}
              onChange={(e) => setConfig((c) => ({ ...c, attivo: e.target.checked }))}
            />
            <span>Attivo (puzzle/memory/rotate richiedono immagine o libreria)</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.usa_biblioteca_se_vuota !== false}
              onChange={(e) => setConfig((c) => ({ ...c, usa_biblioteca_se_vuota: e.target.checked }))}
            />
            <span>Se senza immagine dedicata, usa libreria casuale</span>
          </label>

          <div>
            <span className="text-gray-500 text-xs block mb-1">
              Giochi nel pool casuale (a ogni tentativo ne viene scelto uno)
            </span>
            <div className="flex flex-wrap gap-2">
              {TIPO_OPTS.map((o) => {
                const on = (config.tipi_abilitati || []).includes(o.id);
                return (
                  <button
                    key={o.id}
                    type="button"
                    onClick={() => toggleTipo(o.id)}
                    className={`px-2 py-1 rounded text-xs font-semibold border ${
                      on
                        ? 'bg-indigo-700 border-indigo-500 text-white'
                        : 'bg-gray-900 border-gray-600 text-gray-400'
                    }`}
                  >
                    {o.label}
                  </button>
                );
              })}
            </div>
          </div>

          <label className="block">
            <span className="text-gray-500 text-xs">Difficoltà predefinita (1–4)</span>
            <select
              className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1"
              value={Number(config.difficolta) || 4}
              onChange={(e) => setConfig((c) => ({ ...c, difficolta: Number(e.target.value) }))}
            >
              {[1, 2, 3, 4].map((n) => (
                <option key={n} value={n}>{n} — {DIFFICOLTA_INFO[n]}</option>
              ))}
            </select>
          </label>

          <div>
            <span className="text-gray-500 text-xs block mb-1">
              Regole difficoltà condizionali (se più regole matchano, vince la più facile)
            </span>
            <RegoleGruppoListaEditor
              gruppi={config.regole_difficolta || []}
              onChange={(regole_difficolta) => setConfig((c) => ({ ...c, regole_difficolta }))}
              lookup={lookup}
              lookupLoading={lookupLoading}
              addLabel="Aggiungi regola difficoltà"
              renderExtra={(gruppo, patch) => (
                <label className="flex items-center gap-1 text-xs text-gray-400">
                  → diff.
                  <select
                    className="bg-gray-800 border border-gray-600 rounded px-1"
                    value={gruppo.difficolta ?? 3}
                    onChange={(e) => patch({ difficolta: Number(e.target.value) })}
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </label>
              )}
            />
            <p className="text-[11px] text-gray-500 mt-1">
              Es.: AND aura Magica ≥1 → diff. 3; OR Magica ≥2 / Tecnologica ≥1 → diff. 3.
            </p>
          </div>

          <div>
            <span className="text-gray-500 text-xs block mb-1">
              Salta minigioco se (effetto QR diretto)
            </span>
            <RegoleGruppoListaEditor
              gruppi={config.esclusioni_minigioco || []}
              onChange={(esclusioni_minigioco) => setConfig((c) => ({ ...c, esclusioni_minigioco }))}
              lookup={lookup}
              lookupLoading={lookupLoading}
              addLabel="Aggiungi esclusione"
            />
            <p className="text-[11px] text-gray-500 mt-1">
              Es.: statistica PV ≥6 (= PV&gt;5) → nessun minigioco.
            </p>
          </div>

          <label className="block">
            <span className="text-gray-500 text-xs">Immagine (quadrata)</span>
            <input
              type="file"
              accept="image/*"
              className="w-full mt-0.5 text-xs"
              onChange={(e) => {
                setImageFile(e.target.files?.[0] || null);
                setRemoveImage(false);
              }}
            />
            {!config.immagine_url && config.usa_biblioteca_se_vuota !== false && (
              <p className="text-[11px] text-emerald-400 mt-1">
                Nessuna immagine dedicata: verrà usata un&apos;estrazione dalla libreria staff.
              </p>
            )}
            {config.immagine_url && !removeImage && (
              <div className="mt-2 flex items-center gap-2">
                <img src={config.immagine_url} alt="" className="h-16 w-16 object-cover rounded border border-gray-600" />
                <button
                  type="button"
                  className="text-xs text-red-400 underline"
                  onClick={() => setRemoveImage(true)}
                >
                  Rimuovi immagine
                </button>
              </div>
            )}
          </label>

          <label className="block">
            <span className="text-gray-500 text-xs">Messaggio pre-gioco</span>
            <textarea
              className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1 min-h-[48px]"
              value={config.messaggio_pre}
              onChange={(e) => setConfig((c) => ({ ...c, messaggio_pre: e.target.value }))}
            />
          </label>

          <label className="block">
            <span className="text-gray-500 text-xs">Messaggio vittoria</span>
            <textarea
              className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1 min-h-[48px]"
              value={config.messaggio_vittoria}
              onChange={(e) => setConfig((c) => ({ ...c, messaggio_vittoria: e.target.value }))}
            />
          </label>

          <div className="p-3 bg-gray-900/50 rounded border border-gray-700 space-y-2">
            <span className="text-gray-400 text-xs font-semibold uppercase tracking-wide">
              Dopo la vittoria
            </span>
            <label className="block">
              <span className="text-gray-500 text-xs">Quando saltare il minigioco</span>
              <select
                className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1"
                value={config.modalita_sblocco || 'permanente'}
                onChange={(e) => setConfig((c) => ({ ...c, modalita_sblocco: e.target.value }))}
              >
                {SBLOCCO_OPTS.map((o) => (
                  <option key={o.id} value={o.id}>{o.label}</option>
                ))}
              </select>
            </label>
            {config.modalita_sblocco === 'temporaneo' && (
              <label className="block">
                <span className="text-gray-500 text-xs">Durata sblocco (secondi)</span>
                <input
                  type="number"
                  min={1}
                  className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1"
                  value={config.sblocco_secondi}
                  onChange={(e) => setConfig((c) => ({ ...c, sblocco_secondi: e.target.value }))}
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  Dopo questo intervallo il PG dovrà rifare il minigioco alla prossima scansione.
                </p>
              </label>
            )}
            {config.modalita_sblocco === 'ogni_scansione' && (
              <p className="text-[11px] text-gray-500">
                Ogni nuova scansione richiede un minigioco (salvo partita già in corso).
              </p>
            )}
            {config.modalita_sblocco === 'permanente' && (
              <p className="text-[11px] text-gray-500">
                Comportamento predefinito: una vittoria vale per sempre su questo QR (per PG).
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="text-gray-500 text-xs">Timer (secondi, vuoto = off)</span>
              <input
                type="number"
                min={1}
                className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1"
                value={config.timer_secondi}
                onChange={(e) => setConfig((c) => ({ ...c, timer_secondi: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-gray-500 text-xs">Se scade il timer</span>
              <select
                className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded px-2 py-1"
                value={config.timer_scadenza_azione}
                onChange={(e) => setConfig((c) => ({ ...c, timer_scadenza_azione: e.target.value }))}
              >
                {TIMER_AZIONE_OPTS.map((o) => (
                  <option key={o.id} value={o.id}>{o.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <span className="text-gray-500 text-xs">Richiedi minigioco solo se (vuoto = sempre)</span>
            <RequisitiListaEditor
              requisiti={config.requisiti_attivazione || []}
              onChange={(requisiti_attivazione) => setConfig((c) => ({ ...c, requisiti_attivazione }))}
              lookup={lookup}
              lookupLoading={lookupLoading}
            />
          </div>

          {!templateMode ? (
            <button
              type="button"
              disabled={saving}
              onClick={save}
              className="flex items-center justify-center gap-2 w-full py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-bold disabled:opacity-50"
            >
              {saving ? <Loader className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Salva minigioco
            </button>
          ) : null}

          {msg && <p className="text-xs text-center text-amber-300">{msg}</p>}
        </div>
      )}
    </div>
  );
};

export default MinigiocoQrEditor;
