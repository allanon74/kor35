import React, { useMemo } from 'react';
import { evaluateActivationCosts } from '../lib/activationCostUtils';

/**
 * Anteprima costi risorsa prima dell'attivazione (oggetti / tessiture).
 */
const ActivationCostPreview = ({ char, costi, compact = false, className = '' }) => {
  const evalCosts = useMemo(() => evaluateActivationCosts(char, costi), [char, costi]);

  if (!evalCosts.rows.length) return null;

  if (compact) {
    return (
      <div className={`text-xs leading-snug ${className}`}>
        <span className="text-gray-500 uppercase tracking-wide font-bold">Costo: </span>
        {evalCosts.rows.map((r, i) => (
          <span key={r.sigla}>
            {i > 0 && ', '}
            <span className={r.ok ? 'text-amber-300' : 'text-red-400 font-bold'} title={`${r.nome}: ${r.current}/${r.costo}`}>
              -{r.costo} {r.sigla}
            </span>
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className={`rounded border border-amber-500/20 bg-amber-950/20 px-2 py-1.5 space-y-0.5 ${className}`}>
      <div className="text-[9px] uppercase tracking-wider text-amber-500/80 font-bold">Costi attivazione</div>
      {evalCosts.rows.map((r) => (
        <div key={r.sigla} className="flex justify-between items-center text-[11px]">
          <span className="text-gray-300 truncate mr-2">{r.nome}</span>
          <span className={`font-mono shrink-0 ${r.ok ? 'text-amber-200' : 'text-red-400 font-bold'}`}>
            -{r.costo} ({r.current}/{r.costo})
          </span>
        </div>
      ))}
    </div>
  );
};

export default ActivationCostPreview;
