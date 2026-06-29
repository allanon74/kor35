import React, { useMemo } from 'react';
import { hexPerColoreComponente, testoSuSfondo } from '../stivaColors.js';

function livelloRischioAnnichilamento(coppia) {
  if (!coppia?.entrambi_presenti) return 'none';
  const tick = Number(coppia.tick_coesistenza) || 0;
  const max = Number(coppia.tick_coesistenza_max) || 5;
  if (tick >= max) return 'critical';
  if (tick >= max - 1) return 'danger';
  if (tick > 0) return 'warn';
  return 'coexist';
}

function StivaColorBox({
  colore,
  mattoneId,
  indice,
  selected,
  onSelect,
  selectable,
}) {
  const qty = Number(colore?.quantita) || 0;
  const hex = hexPerColoreComponente(colore?.sigla, colore?.nome);
  const text = testoSuSfondo(hex);
  const selezionabile = selectable && qty > 0 && mattoneId;

  const className = `stiva-color-box ${qty > 0 ? 'has-stock' : 'empty'} ${selected ? 'selected' : ''} ${!selectable ? 'display-only' : ''}`;

  const inner = (
    <>
      <span className="stiva-color-box-qty">{qty}</span>
      <span className="stiva-color-box-name">{colore?.nome || '—'}</span>
      {indice != null ? (
        <span className="stiva-color-box-idx">#{indice}</span>
      ) : null}
    </>
  );

  const style = {
    '--stiva-bg': hex,
    '--stiva-fg': text,
    '--stiva-border': selected ? '#ffe066' : 'rgba(255,255,255,0.22)',
  };

  if (!selectable) {
    return (
      <div className={className} style={style} title={colore?.nome}>
        {inner}
      </div>
    );
  }

  return (
    <button
      type="button"
      className={className}
      style={style}
      disabled={!selezionabile}
      onClick={() => selezionabile && onSelect(mattoneId)}
      title={
        selezionabile
          ? 'Seleziona per compressione / decompressione / risonanza'
          : qty > 0
            ? colore?.nome
            : `${colore?.nome || 'Colore'} — assente in stiva`
      }
    >
      {inner}
    </button>
  );
}

export default function StivaCompattatoreGrid({
  stiva,
  selectedMattone,
  onSelectMattone,
  selectable = true,
}) {
  const righe = stiva?.righe || [];
  const coppie = stiva?.coppie_opposite || [];

  const coloreToMattone = useMemo(() => {
    const map = new Map();
    for (const r of righe) {
      if (!r.colore_id) continue;
      const prev = map.get(r.colore_id);
      if (!prev || Number(r.quantita) > Number(prev.quantita)) {
        map.set(r.colore_id, r);
      }
    }
    return map;
  }, [righe]);

  const indicePerColore = useMemo(() => {
    const map = new Map();
    for (const r of righe) {
      if (r.colore_id != null && r.indice_componente != null) {
        map.set(r.colore_id, r.indice_componente);
      }
    }
    return map;
  }, [righe]);

  const totaleUnita = righe.reduce((s, r) => s + (Number(r.quantita) || 0), 0);
  const coppieARischio = coppie.filter((c) => c.entrambi_presenti).length;

  if (!coppie.length && !righe.length) {
    return (
      <p className="stiva-compattatore-empty">Stiva vuota — carica componenti da staff.</p>
    );
  }

  return (
    <div className="stiva-compattatore">
      <div className="stiva-compattatore-summary">
        <span>
          {totaleUnita}
          {' '}
          unità in stiva
        </span>
        {coppieARischio > 0 ? (
          <span className="stiva-compattatore-risk-pill">
            {coppieARischio}
            {' '}
            coppia
            {coppieARischio === 1 ? '' : 'e'}
            {' '}
            a rischio annichilamento
          </span>
        ) : null}
      </div>

      <div className="stiva-pairs-grid">
        {coppie.map((c) => {
          const risk = livelloRischioAnnichilamento(c);
          const rowA = coloreToMattone.get(c.colore_a.id);
          const rowB = coloreToMattone.get(c.colore_b.id);
          const tick = Number(c.tick_coesistenza) || 0;
          const max = Number(c.tick_coesistenza_max) || 5;
          const pct = max > 0 ? Math.min(100, (tick / max) * 100) : 0;

          return (
            <div
              key={c.id}
              className={`stiva-pair-row stiva-pair-row--${risk}`}
            >
              <StivaColorBox
                colore={c.colore_a}
                mattoneId={rowA?.mattone_id}
                indice={rowA?.indice_componente ?? indicePerColore.get(c.colore_a.id)}
                selected={selectedMattone === rowA?.mattone_id}
                onSelect={onSelectMattone}
                selectable={selectable}
              />
              <div className="stiva-pair-bridge" aria-hidden="true">
                <span className="stiva-pair-bridge-icon">⟷</span>
                {c.entrambi_presenti ? (
                  <div className="stiva-pair-tick">
                    <div className="stiva-pair-tick-bar">
                      <div
                        className="stiva-pair-tick-fill"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="stiva-pair-tick-label">
                      {tick >= max ? 'Annichilamento imminente' : `Coesistenza ${tick}/${max}`}
                    </span>
                  </div>
                ) : (
                  <span className="stiva-pair-safe">opposti</span>
                )}
              </div>
              <StivaColorBox
                colore={c.colore_b}
                mattoneId={rowB?.mattone_id}
                indice={rowB?.indice_componente ?? indicePerColore.get(c.colore_b.id)}
                selected={selectedMattone === rowB?.mattone_id}
                onSelect={onSelectMattone}
                selectable={selectable}
              />
            </div>
          );
        })}
      </div>

      <p className="stiva-compattatore-hint">
        {selectable
          ? 'Clicca un box con quantità > 0 per selezionarlo nelle operazioni del compattatore.'
          : 'Inventario globale — i colori opposti coesistono al massimo'}
        {' '}
        {coppie[0]?.tick_coesistenza_max ?? 5}
        {' '}
        tick prima dell&apos;annichilamento 1:1.
      </p>
    </div>
  );
}
