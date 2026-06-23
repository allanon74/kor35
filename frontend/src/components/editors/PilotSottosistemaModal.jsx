import React from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

const TIPO_OPTS = [
  'standard',
  'generatore',
  'batteria',
  'serbatoio',
  'motore',
  'portale',
  'manovra',
];

const EFFETTO_TIPI = [
  'none',
  'guasto_altro_percent',
  'guasto_random_percent',
  'riduci_carburante_percent',
  'riduci_batterie_percent',
  'allunga_distanza_percent',
  'naufragio',
];

const PilotSottosistemaModal = ({
  open,
  mode,
  draft,
  setDraft,
  effettoBuilder,
  setEffettoBuilder,
  effettoValidation,
  generaEffettoGuastoJson,
  onSave,
  onClose,
  saving = false,
  serbatoioFuel = null,
  serbatoioFuelDraft = '',
  setSerbatoioFuelDraft,
  serbatoioFuelBusy = false,
  onApplySerbatoioFuel,
  onFillSerbatoioFuel,
  onRefreshSerbatoioFuel,
}) => {
  if (!open) return null;

  const title = mode === 'edit' ? 'Modifica sottosistema' : 'Nuovo sottosistema';

  return createPortal(
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center p-3 sm:p-4 bg-black/85 backdrop-blur-sm"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-gray-800 rounded-2xl w-full max-w-4xl max-h-[min(94vh,920px)] flex flex-col border border-indigo-500/40 shadow-2xl"
        onClick={(ev) => ev.stopPropagation()}
      >
        <div className="shrink-0 flex justify-between items-center gap-3 px-5 py-4 border-b border-gray-700">
          <h3 className="text-lg font-bold text-indigo-300">{title}</h3>
          <button
            type="button"
            className="px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:bg-gray-700 border border-gray-600"
            onClick={onClose}
          >
            <X size={14} className="inline mr-1" />
            Chiudi
          </button>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 px-5 py-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
            <label className="block">
              <span className="text-xs text-gray-400">Codice (1 carattere)</span>
              <input
                className="bg-gray-900 rounded px-2 py-1.5 w-16 mt-1 border border-gray-600 uppercase"
                maxLength={1}
                value={draft.codice}
                onChange={(e) => setDraft((p) => ({ ...p, codice: e.target.value }))}
                placeholder="A"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="text-xs text-gray-400">Nome sottosistema</span>
              <input
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.nome}
                onChange={(e) => setDraft((p) => ({ ...p, nome: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Gruppo sistema</span>
              <input
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.gruppo}
                onChange={(e) => setDraft((p) => ({ ...p, gruppo: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Ordine colonna (gruppo)</span>
              <input
                type="number"
                min={0}
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.ordine_gruppo ?? 0}
                onChange={(e) => setDraft((p) => ({ ...p, ordine_gruppo: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Ordine nel gruppo</span>
              <input
                type="number"
                min={0}
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.ordine ?? 0}
                onChange={(e) => setDraft((p) => ({ ...p, ordine: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Tipo sottosistema</span>
              <select
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.tipo}
                onChange={(e) => setDraft((p) => ({ ...p, tipo: e.target.value }))}
              >
                {TIPO_OPTS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Produzione energia / livello</span>
              <input
                type="number"
                step="0.1"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.coeff_produzione}
                onChange={(e) => setDraft((p) => ({ ...p, coeff_produzione: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Consumo energia / livello</span>
              <input
                type="number"
                step="0.1"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.coeff_consumo_energia}
                onChange={(e) => setDraft((p) => ({ ...p, coeff_consumo_energia: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Consumo carburante / livello</span>
              <input
                type="number"
                step="0.1"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.coeff_consumo_carburante}
                onChange={(e) => setDraft((p) => ({ ...p, coeff_consumo_carburante: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Coeff. effetto speciale</span>
              <input
                type="number"
                step="0.01"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.coeff_effetto_speciale ?? 1}
                onChange={(e) => setDraft((p) => ({ ...p, coeff_effetto_speciale: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Rampa livelli / tick</span>
              <input
                type="number"
                min={1}
                max={9}
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.rampa_livelli_per_tick ?? 1}
                onChange={(e) => setDraft((p) => ({ ...p, rampa_livelli_per_tick: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Capacità batterie</span>
              <input
                type="number"
                step="0.1"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.capacita_storage ?? 0}
                onChange={(e) => setDraft((p) => ({ ...p, capacita_storage: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Coeff. ricarica batterie</span>
              <input
                type="number"
                step="0.01"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.coeff_ricarica_storage ?? 0.5}
                onChange={(e) => setDraft((p) => ({ ...p, coeff_ricarica_storage: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Capacità serbatoio</span>
              <input
                type="number"
                step="0.1"
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600"
                value={draft.capacita_carburante ?? 0}
                onChange={(e) => setDraft((p) => ({ ...p, capacita_carburante: e.target.value }))}
              />
            </label>
          </div>

          {mode === 'edit' && String(draft.tipo || '').toLowerCase() === 'serbatoio' ? (
            <div className="mt-4 rounded-xl border border-amber-700/40 bg-amber-950/20 p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs font-semibold text-amber-200/90 uppercase tracking-wide">
                  Carico attuale — sessione console
                </div>
                {onRefreshSerbatoioFuel ? (
                  <button
                    type="button"
                    className="text-xs px-2 py-1 rounded border border-gray-600 text-gray-300 hover:bg-gray-800"
                    onClick={onRefreshSerbatoioFuel}
                    disabled={serbatoioFuelBusy}
                  >
                    Aggiorna
                  </button>
                ) : null}
              </div>
              {serbatoioFuel?.loading ? (
                <p className="text-xs text-gray-400">Lettura carburante sessione…</p>
              ) : serbatoioFuel?.error ? (
                <p className="text-xs text-red-300">{serbatoioFuel.error}</p>
              ) : !serbatoioFuel?.sessione_attiva ? (
                <p className="text-xs text-gray-400">
                  Nessuna sessione attiva sulla console (idle o in volo). Avvia o ripristina una sessione pilota.
                </p>
              ) : (
                <>
                  <p className="text-xs text-gray-400">
                    Pilota: <span className="text-gray-200">{serbatoioFuel.pilota_nome || '—'}</span>
                    {' · '}
                    Stato: <span className="font-mono text-gray-200">{serbatoioFuel.sessione_stato}</span>
                    {' · '}
                    Attuale:{' '}
                    <span className="font-mono text-amber-200">
                      {Math.round(Number(serbatoioFuel.carburante_attuale || 0))}
                    </span>
                    {' / '}
                    <span className="font-mono text-gray-300">
                      {Math.round(Number(serbatoioFuel.carburante_massimo || 0))}
                    </span>
                  </p>
                  <label className="block">
                    <span className="text-xs text-gray-400">Imposta carico attuale</span>
                    <input
                      type="number"
                      min={0}
                      step={1}
                      className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full border border-gray-600 font-mono"
                      value={serbatoioFuelDraft}
                      onChange={(e) => setSerbatoioFuelDraft?.(e.target.value)}
                    />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 text-sm text-white disabled:opacity-50"
                      disabled={serbatoioFuelBusy}
                      onClick={onApplySerbatoioFuel}
                    >
                      Applica carico
                    </button>
                    <button
                      type="button"
                      className="px-3 py-1.5 rounded bg-gray-700 hover:bg-gray-600 text-sm text-white disabled:opacity-50"
                      disabled={serbatoioFuelBusy}
                      onClick={onFillSerbatoioFuel}
                    >
                      Riempi al massimo
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : null}

          <label className="block mt-4 text-sm">
            <span className="text-xs text-gray-400">Effetto su guasto sottosistema (JSON)</span>
            <textarea
              rows={4}
              className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full font-mono text-xs border border-gray-600"
              value={draft.effetti_guasto_json}
              onChange={(e) => setDraft((p) => ({ ...p, effetti_guasto_json: e.target.value }))}
            />
          </label>

          <div className="mt-3 border border-gray-700 rounded-lg p-3 bg-gray-900/60">
            <div className="text-xs text-gray-300 mb-2">Generatore rapido JSON effetto guasto</div>
            <div className="grid sm:grid-cols-4 gap-2">
              <select
                className="bg-gray-900 rounded px-2 py-1.5 border border-gray-600"
                value={effettoBuilder.tipo}
                onChange={(e) => setEffettoBuilder((p) => ({ ...p, tipo: e.target.value }))}
              >
                {EFFETTO_TIPI.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="0.1"
                min={0}
                max={100}
                disabled={['none', 'naufragio'].includes(effettoBuilder.tipo)}
                className="bg-gray-900 rounded px-2 py-1.5 border border-gray-600 disabled:opacity-40"
                placeholder="valore %"
                value={effettoBuilder.valore}
                onChange={(e) => setEffettoBuilder((p) => ({ ...p, valore: e.target.value }))}
              />
              <input
                className="bg-gray-900 rounded px-2 py-1.5 border border-gray-600 disabled:opacity-40"
                maxLength={1}
                disabled={effettoBuilder.tipo !== 'guasto_altro_percent'}
                placeholder="target codice"
                value={effettoBuilder.target_codice}
                onChange={(e) =>
                  setEffettoBuilder((p) => ({ ...p, target_codice: e.target.value.toUpperCase() }))
                }
              />
              <button
                type="button"
                disabled={!effettoValidation.valid}
                className="px-3 py-1.5 rounded bg-indigo-700 disabled:opacity-40 text-sm"
                onClick={() =>
                  setDraft((p) => ({
                    ...p,
                    effetti_guasto_json: generaEffettoGuastoJson(effettoBuilder),
                  }))
                }
              >
                Genera JSON
              </button>
            </div>
            <div
              className={`text-xs mt-2 ${effettoValidation.valid ? 'text-emerald-300' : 'text-amber-300'}`}
            >
              {effettoValidation.message}
            </div>
          </div>

          <label className="block mt-3 text-sm">
            <span className="text-xs text-gray-400">Effetto attivazione INVERTI (JSON)</span>
            <textarea
              rows={3}
              className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full font-mono text-xs border border-gray-600"
              value={draft.effetti_inversione_json}
              onChange={(e) => setDraft((p) => ({ ...p, effetti_inversione_json: e.target.value }))}
            />
          </label>
          <label className="block mt-3 text-sm">
            <span className="text-xs text-gray-400">Effetto attivazione ESPULSIONE (JSON)</span>
            <textarea
              rows={3}
              className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full font-mono text-xs border border-gray-600"
              value={draft.effetti_espulsione_json}
              onChange={(e) => setDraft((p) => ({ ...p, effetti_espulsione_json: e.target.value }))}
            />
          </label>

          <div className="grid sm:grid-cols-3 gap-3 mt-3">
            <label className="block text-sm">
              <span className="text-xs text-gray-400">Guasto % per livello</span>
              <textarea
                rows={5}
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full font-mono text-xs border border-gray-600"
                value={draft.guasto_percent_per_livello_json}
                onChange={(e) => setDraft((p) => ({ ...p, guasto_percent_per_livello_json: e.target.value }))}
              />
            </label>
            <label className="block text-sm">
              <span className="text-xs text-gray-400">Ripristino % per livello</span>
              <textarea
                rows={5}
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full font-mono text-xs border border-gray-600"
                value={draft.ripristino_percent_per_livello_json}
                onChange={(e) => setDraft((p) => ({ ...p, ripristino_percent_per_livello_json: e.target.value }))}
              />
            </label>
            <label className="block text-sm">
              <span className="text-xs text-gray-400">Colori per livello (HEX)</span>
              <textarea
                rows={5}
                className="bg-gray-900 rounded px-2 py-1.5 mt-1 w-full font-mono text-xs border border-gray-600"
                value={draft.colori_per_livello_json}
                onChange={(e) => setDraft((p) => ({ ...p, colori_per_livello_json: e.target.value }))}
              />
            </label>
          </div>
        </div>

        <div className="shrink-0 flex justify-end gap-2 px-5 py-3 border-t border-gray-700 bg-gray-900/80">
          <button
            type="button"
            className="px-4 py-2 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700"
            onClick={onClose}
          >
            Annulla
          </button>
          <button
            type="button"
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-50"
            onClick={onSave}
          >
            {mode === 'edit' ? 'Salva modifiche' : 'Crea sottosistema'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
};

export default PilotSottosistemaModal;
