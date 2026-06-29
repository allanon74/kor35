import React from 'react';
import { hexPerColoreComponente, testoSuSfondo } from '../stivaColors.js';

export default function CompattatoreElementPicker({
  righe = [],
  selectedMattone,
  onSelectMattone,
}) {
  const disponibili = righe.filter((r) => Number(r.quantita) > 0);

  if (!disponibili.length) {
    return (
      <div className="comp-element-picker comp-element-picker--empty">
        <span className="comp-element-picker-label">Sorgente</span>
        <p className="comp-element-picker-empty">Nessun componente in stiva — carica da staff.</p>
      </div>
    );
  }

  return (
    <div className="comp-element-picker">
      <span className="comp-element-picker-label">Sorgente componente</span>
      <div className="comp-element-grid">
        {disponibili.map((r) => {
          const hex = hexPerColoreComponente(r.colore_sigla, r.colore_nome);
          const fg = testoSuSfondo(hex);
          const selected = selectedMattone === r.mattone_id;
          return (
            <button
              key={r.mattone_id}
              type="button"
              className={`comp-element-chip ${selected ? 'selected' : ''}`}
              style={{
                '--chip-bg': hex,
                '--chip-fg': fg,
              }}
              onClick={() => onSelectMattone(r.mattone_id)}
            >
              <span className="comp-element-chip-qty">{r.quantita}</span>
              <span className="comp-element-chip-meta">
                <span className="comp-element-chip-idx">#{r.indice_componente}</span>
                <span className="comp-element-chip-name">{r.colore_nome || r.nome}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
