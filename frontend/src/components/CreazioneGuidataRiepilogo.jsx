import React, { useState } from 'react';
import { ChevronDown, ChevronUp, User } from 'lucide-react';

function Row({ label, value, hint }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className="flex justify-between gap-2 text-sm py-0.5">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span className="text-gray-200 text-right">
        {value}
        {hint ? <span className="block text-[10px] text-gray-500 font-normal">{hint}</span> : null}
      </span>
    </div>
  );
}

export default function CreazioneGuidataRiepilogo({ riepilogo, loading }) {
  const [open, setOpen] = useState(false);
  if (!riepilogo && !loading) return null;

  const r = riepilogo || {};
  const compactLine = [
    r.nome,
    r.era_nome,
    r.prefettura_nome,
    r.punti_caratteristica != null ? `${r.punti_caratteristica} PC` : null,
    r.crediti != null ? `${r.crediti} CR` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="border-b border-gray-800 bg-gray-950/90 shrink-0">
      <div className="px-3 py-2 flex items-start gap-2">
        <User size={16} className="text-indigo-400 shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <p className="text-[10px] uppercase tracking-wider text-gray-500">Personaggio</p>
          {loading ? (
            <p className="text-xs text-gray-400 animate-pulse">Aggiornamento riepilogo...</p>
          ) : (
            <p className="text-xs text-gray-200 truncate" title={compactLine}>
              {compactLine || '—'}
            </p>
          )}
          {r.anteprima_attiva && !loading ? (
            <p className="text-[10px] text-amber-500/90 mt-0.5">
              Bozza percorso (non ancora in scheda)
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 p-1.5 rounded hover:bg-gray-800 text-gray-400"
          aria-expanded={open}
          aria-label={open ? 'Chiudi dettagli' : 'Apri dettagli personaggio'}
        >
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {open && riepilogo && !loading && (
        <div className="px-3 pb-3 space-y-3 max-h-56 overflow-y-auto border-t border-gray-800/80">
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
            <Row label="Tipologia" value={r.tipologia_nome} />
            <Row label="Segno" value={r.segno_zodiacale_nome} />
            <Row label="Era" value={r.era_nome} />
            <Row
              label="Prefettura"
              value={
                r.prefettura_esterna
                  ? 'Esterna'
                  : [r.prefettura_nome, r.prefettura_regione].filter(Boolean).join(' · ')
              }
            />
          </div>

          <div className="rounded-lg bg-gray-900/80 border border-gray-700/80 p-2">
            <p className="text-[10px] uppercase text-emerald-600 font-bold mb-1">Risorse</p>
            <Row label="Punti caratteristica" value={r.punti_caratteristica} />
            <Row
              label="PC stimati dopo percorso"
              value={r.pc_residui_stimati}
              hint={r.costo_percorso_pc ? `costo percorso: ${r.costo_percorso_pc} PC` : null}
            />
            <Row label="Crediti" value={r.crediti} />
            <Row
              label="CR stimati dopo percorso"
              value={r.crediti_residui_stimati}
              hint={
                r.costo_percorso_crediti && r.costo_percorso_crediti !== '0'
                  ? `costo percorso: ${r.costo_percorso_crediti} CR${
                      r.sconto_abilita_percent > 0
                        ? ` (sconto abilità ${r.sconto_abilita_percent}%)`
                        : ''
                    }`
                  : r.sconto_abilita_percent > 0
                    ? `sconto abilità attivo: ${r.sconto_abilita_percent}%`
                    : null
              }
            />
          </div>

          {(r.caratteristiche || []).length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-500 mb-1">Caratteristiche (anteprima)</p>
              <ul className="text-xs space-y-0.5">
                {r.caratteristiche.map((c) => (
                  <li key={c.nome} className="flex justify-between text-gray-300">
                    <span>{c.nome}</span>
                    <span>
                      {c.valore_anteprima}
                      {c.delta ? (
                        <span className="text-emerald-500 ml-1">(+{c.delta})</span>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(r.abilita_possedute || []).length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-500 mb-1">
                Abilità già sul personaggio ({r.abilita_possedute.length})
              </p>
              <ul className="text-xs text-gray-300 list-disc pl-4 max-h-20 overflow-y-auto">
                {r.abilita_possedute.map((a) => (
                  <li key={a.id}>
                    {a.nome}
                    {a.origine && a.origine !== 'acquisto' ? (
                      <span className="text-gray-500"> ({a.origine})</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(r.abilita_scelte || r.abilita_nel_percorso || []).length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-violet-400 mb-1">
                Scelte nel percorso ({(r.abilita_scelte || r.abilita_nel_percorso).length})
              </p>
              <ul className="text-xs text-violet-200 list-disc pl-4 max-h-20 overflow-y-auto">
                {(r.abilita_scelte || r.abilita_nel_percorso).map((a) => (
                  <li key={a.sync_id || a.id}>
                    {a.nome}
                    {(a.costo_pc > 0 || Number(a.costo_crediti) > 0) && (
                      <span className="text-gray-500">
                        {' '}
                        ({a.costo_pc > 0 ? `${a.costo_pc} PC` : ''}
                        {a.costo_pc > 0 && Number(a.costo_crediti) > 0 ? ', ' : ''}
                        {Number(a.costo_crediti) > 0 ? (
                          <>
                            {a.costo_crediti_base &&
                            a.costo_crediti_base !== a.costo_crediti ? (
                              <span className="line-through opacity-60 mr-0.5">
                                {a.costo_crediti_base}
                              </span>
                            ) : null}
                            {a.costo_crediti} CR
                          </>
                        ) : (
                          ''
                        )}
                        )
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(r.abilita_da_acquistare || []).length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-amber-500 mb-1">Da acquistare (fondi insufficienti)</p>
              <ul className="text-xs text-amber-100 list-disc pl-4">
                {r.abilita_da_acquistare.map((a) => (
                  <li key={a.id}>{a.nome}</li>
                ))}
              </ul>
            </div>
          )}

          {(r.modelli_aura || []).length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-500 mb-1">Modelli di aura</p>
              <ul className="text-xs text-gray-300 list-disc pl-4">
                {r.modelli_aura.map((m, i) => (
                  <li key={`${m.nome}-${i}`}>
                    {m.nome}
                    {m.aura ? <span className="text-gray-500"> ({m.aura})</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
