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

function GlyphFrame({ children }) {
  return (
    <svg className="comms-color-glyph" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <circle cx="32" cy="32" r="30" fill="rgba(0,0,0,0.34)" stroke="rgba(255,255,255,0.9)" strokeWidth="2.25" />
      {children}
    </svg>
  );
}

/** Icona distinta per colore: leggibile a distanza sulla console radio. */
function AlarmGlyph({ id }) {
  const ink = '#f4f7fb';
  const mark = '#0b0f16';
  switch (id) {
    case 'giallo':
      // Triangolo allerta
      return (
        <GlyphFrame>
          <path fill={ink} d="M32 11L53 51H11L32 11z" />
          <rect x="29" y="26" width="6" height="14" rx="2" fill={mark} />
          <circle cx="32" cy="45.5" r="3.2" fill={mark} />
        </GlyphFrame>
      );
    case 'rosso':
      // Mirino combattimento
      return (
        <GlyphFrame>
          <path
            fill={ink}
            fillRule="evenodd"
            d="M32 14a18 18 0 1 1 0 36 18 18 0 0 1 0-36zm0 7a11 11 0 1 0 0 22 11 11 0 0 0 0-22zm0 6a5 5 0 1 1 0 10 5 5 0 0 1 0-10z"
          />
          <rect x="29.5" y="8" width="5" height="9" rx="1.5" fill={ink} />
          <rect x="29.5" y="47" width="5" height="9" rx="1.5" fill={ink} />
          <rect x="8" y="29.5" width="9" height="5" rx="1.5" fill={ink} />
          <rect x="47" y="29.5" width="9" height="5" rx="1.5" fill={ink} />
        </GlyphFrame>
      );
    case 'nero':
      // Stella esotica / anomalia
      return (
        <GlyphFrame>
          <path
            fill={ink}
            d="M32 9l5.2 15.2H53l-12.5 9.2 4.8 15.2L32 39.8 18.7 48.6l4.8-15.2L11 24.2h15.8L32 9z"
          />
        </GlyphFrame>
      );
    case 'blu':
      // Freccia manovra / rotta
      return (
        <GlyphFrame>
          <path fill={ink} d="M32 10l17 29H39v15H25V39h-10L32 10z" />
        </GlyphFrame>
      );
    case 'ambra':
      // Chiave inglese riparazione
      return (
        <GlyphFrame>
          <path
            fill={ink}
            d="M44 13.2a10 10 0 0 0-14.1 0l-2 2 7 7-3.6 3.6-7-7-1.6 1.6 7 7-10.2 10.2a4.6 4.6 0 0 0 0 6.5l1.7 1.7a4.6 4.6 0 0 0 6.5 0L38 35.6l7 7 1.6-1.6-7-7 3.6-3.6 7 7 2-2a10 10 0 0 0 0-14.1l-4.2 4.2a4.4 4.4 0 1 1-6.2-6.2L44 13.2z"
          />
        </GlyphFrame>
      );
    case 'viola':
      // Scudo sicurezza / invasione
      return (
        <GlyphFrame>
          <path
            fill={ink}
            d="M32 9c9 5 17.5 6 17.5 6V30c0 13.5-9.5 22-17.5 25.5C24 52 14.5 43.5 14.5 30V15S23 14 32 9z"
          />
          <path
            fill={mark}
            d="M29.2 22h5.6v7.2H42v5.6h-7.2V42h-5.6v-7.2H22v-5.6h7.2V22z"
          />
        </GlyphFrame>
      );
    case 'bianco':
      // Croce medica
      return (
        <GlyphFrame>
          <path fill={ink} d="M25 13h14v12h12v14H39v12H25V39H13V25h12V13z" />
        </GlyphFrame>
      );
    case 'crociera':
    default:
      // Check crociera / ok
      return (
        <GlyphFrame>
          <path fill={ink} d="M16 33.5l10.2 10.2L49.5 18l-5.4-4.8L26 33.2l-4.8-4.8L16 33.5z" />
        </GlyphFrame>
      );
  }
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
              <AlarmGlyph id={c.id} />
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
