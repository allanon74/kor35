import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';

/** Ordine di default se lo staff non ha ancora salvato un protocollo. */
const COLORI = [
  { id: 'giallo', label: 'Giallo', hint: 'Allerta', className: 'alarm-giallo', ordine: 10 },
  { id: 'rosso', label: 'Rosso', hint: 'Combattimento', className: 'alarm-rosso', ordine: 20 },
  { id: 'nero', label: 'Nero', hint: 'Esotico', className: 'alarm-nero', ordine: 30 },
  { id: 'blu', label: 'Blu', hint: 'Manovra', className: 'alarm-blu', ordine: 40 },
  { id: 'ambra', label: 'Ambra', hint: 'Riparazione', className: 'alarm-ambra', ordine: 50 },
  { id: 'viola', label: 'Viola', hint: 'Invasione', className: 'alarm-viola', ordine: 60 },
  { id: 'bianco', label: 'Bianco', hint: 'Medico', className: 'alarm-bianco', ordine: 70 },
  { id: 'crociera', label: 'Verde', hint: 'Crociera', className: 'alarm-verde', ordine: 80 },
];

function AlarmGlyph() {
  return (
    <svg className="comms-color-glyph" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <circle cx="32" cy="32" r="28" fill="rgba(0,0,0,0.22)" stroke="rgba(255,255,255,0.75)" strokeWidth="3" />
      <path
        d="M32 14c-7.2 0-13 5.8-13 13v8.2l-4.4 6.6c-.7 1-.1 2.4 1.1 2.4h32.6c1.2 0 1.8-1.4 1.1-2.4L46 35.2V27c0-7.2-5.8-13-13-13z"
        fill="currentColor"
        opacity="0.95"
      />
      <rect x="26" y="46" width="12" height="5" rx="2.5" fill="currentColor" />
    </svg>
  );
}

function secondiRimanenti(iso) {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (!Number.isFinite(ms)) return null;
  return Math.max(0, Math.ceil(ms / 1000));
}

/**
 * Radio di bordo: dichiara il colore, la plancia lo legge ad alta voce
 * e il dipartimento associato riceve il testo.
 */
const PREVIEW_QUADRO = {
  sessione_attiva: true,
  allarme: 'crociera',
  evento: {
    nome: 'Contatto distorto',
    descrizione: 'Un segnale irregolare occupa il canale di bordo.',
    in_reazione: true,
    reazione_fino_at: null,
  },
  sottosistemi_guasti: ['Propulsore'],
  protocolli: [
    { colore: 'ambra', dipartimento: 'Ingegneria', ha_testo: true, ordine: 50 },
    { colore: 'viola', dipartimento: 'Sicurezza', ha_testo: true, ordine: 60 },
    { colore: 'bianco', dipartimento: 'Medica', ha_testo: true, ordine: 70 },
  ],
};

export default function ComunicazioniScreen({ onLogout, onBack, preview = false, compact = false }) {
  const [quadro, setQuadro] = useState(preview ? {
    ...PREVIEW_QUADRO,
    evento: {
      ...PREVIEW_QUADRO.evento,
      reazione_fino_at: new Date(Date.now() + 8 * 60 * 1000).toISOString(),
    },
  } : null);
  const [error, setError] = useState('');
  const [esito, setEsito] = useState('');
  const [busy, setBusy] = useState(false);
  const [nowTick, setNowTick] = useState(Date.now());

  const load = useCallback(async () => {
    if (preview) return;
    try {
      const data = await api.comunicazioniQuadro();
      setQuadro(data);
      setError('');
    } catch (err) {
      setError(err?.message || 'Quadro radio non disponibile.');
    }
  }, [preview]);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 3000);
    const clock = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => {
      window.clearInterval(id);
      window.clearInterval(clock);
    };
  }, [load]);

  const protocolli = quadro?.protocolli || [];
  const protocolloDi = (colore) => protocolli.find((p) => p.colore === colore);
  const coloriOrdinati = useMemo(() => {
    const ordineDi = (c) => {
      const proto = protocolli.find((p) => p.colore === c.id);
      const n = proto != null ? Number(proto.ordine) : NaN;
      if (Number.isFinite(n) && n > 0) return n;
      return c.ordine;
    };
    return COLORI.slice().sort((a, b) => {
      const d = ordineDi(a) - ordineDi(b);
      if (d !== 0) return d;
      return String(a.id).localeCompare(String(b.id));
    });
  }, [protocolli]);
  const evento = quadro?.evento;
  const reazione = evento?.in_reazione ? secondiRimanenti(evento.reazione_fino_at) : null;
  void nowTick;

  const dichiara = async (colore) => {
    if (busy) return;
    setBusy(true);
    setError('');
    if (preview) {
      const proto = protocolloDi(colore);
      setQuadro((prev) => ({ ...(prev || {}), allarme: colore }));
      setEsito(proto?.dipartimento
        ? `Messaggio a ${proto.dipartimento}. Audio in plancia.`
        : 'Allarme dichiarato. Audio in plancia.');
      setBusy(false);
      return;
    }
    try {
      const res = await api.setAllarmeEquipaggio(colore);
      const parti = [];
      if (res?.dipartimento) {
        parti.push(`Messaggio a ${res.dipartimento} (${res.inviati || 0}).`);
      }
      if (res?.grazia_ca) parti.push('Primo controllo di catastrofe soppresso.');
      if (res?.announcement) parti.push('Audio in plancia.');
      setEsito(parti.join(' ') || 'Allarme dichiarato.');
      await load();
    } catch (err) {
      setError(err?.message || 'Allarme non inviato.');
    } finally {
      setBusy(false);
    }
  };

  const guasti = quadro?.sottosistemi_guasti || [];
  const statoCompatto = !quadro?.sessione_attiva
    ? 'Nessun volo in corso'
    : evento
      ? `${evento.nome}${evento.in_reazione ? ` · reazione ${reazione == null ? '…' : `${reazione}s`}` : ' · reazione chiusa'}`
      : 'Nessun evento';

  return (
    <div className={`comms-console${compact ? ' is-kiosk800' : ''}`}>
      <header className="comms-head">
        <div>
          <div className="comms-kicker">KOR-35 // RADIO</div>
          <h1>Comunicazioni</h1>
        </div>
        <div className="comms-head-actions">
          {onBack ? (
            <button type="button" className={compact ? 'btn kiosk800-back' : 'btn'} onClick={onBack}>
              {compact ? 'Scelta' : 'Stazione'}
            </button>
          ) : null}
          <button type="button" className={compact ? 'btn kiosk800-back' : 'btn'} onClick={onLogout}>Esci</button>
        </div>
      </header>

      {compact ? (
        <p className="comms-statusline">
          {statoCompatto}
          {guasti.length ? ` · guasti ${guasti.join(', ')}` : ''}
        </p>
      ) : null}

      <section className="comms-event" hidden={compact}>
        {!quadro?.sessione_attiva ? (
          <p>Nessun volo in corso. Gli allarmi partono quando la nave è in missione.</p>
        ) : evento ? (
          <>
            <strong>{evento.nome}</strong>
            {evento.descrizione ? <p>{evento.descrizione}</p> : null}
            <p className="comms-note">
              {evento.in_reazione
                ? `Finestra di reazione: ${reazione == null ? '…' : `${reazione}s`}. Il colore giusto salta il primo controllo di catastrofe.`
                : 'Reazione chiusa: il colore accende la sala e avvisa il dipartimento.'}
            </p>
          </>
        ) : (
          <p>Nessun evento in corso. Puoi comunque dichiarare un allarme al dipartimento.</p>
        )}
        {guasti.length ? (
          <p className="comms-faults">Guasti: {guasti.join(', ')}</p>
        ) : null}
      </section>

      <div className="comms-grid" role="group" aria-label="Allarmi cromatici">
        {coloriOrdinati.map((c) => {
          const proto = protocolloDi(c.id);
          const attivo = quadro?.allarme === c.id;
          const sotto = proto?.dipartimento || c.hint;
          return (
            <button
              key={c.id}
              type="button"
              className={`comms-color ${c.className} ${attivo ? 'active' : ''}`}
              disabled={busy}
              onClick={() => dichiara(c.id)}
              aria-label={`Allarme ${c.label}${sotto ? `, ${sotto}` : ''}`}
            >
              <AlarmGlyph />
              <span className="comms-color-label">{c.label}</span>
              <span className="comms-color-hint">{sotto}</span>
            </button>
          );
        })}
      </div>

      {esito ? <p className="comms-esito">{esito}</p> : null}
      {error ? <p className="comms-error">{error}</p> : null}
    </div>
  );
}
