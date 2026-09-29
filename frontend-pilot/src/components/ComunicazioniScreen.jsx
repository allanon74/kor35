import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';

const COLORI = [
  { id: 'giallo', label: 'Giallo', hint: 'Allerta', className: 'alarm-giallo' },
  { id: 'rosso', label: 'Rosso', hint: 'Combattimento', className: 'alarm-rosso' },
  { id: 'nero', label: 'Nero', hint: 'Esotico', className: 'alarm-nero' },
  { id: 'blu', label: 'Blu', hint: 'Manovra', className: 'alarm-blu' },
  { id: 'ambra', label: 'Ambra', hint: 'Riparazione', className: 'alarm-ambra' },
  { id: 'viola', label: 'Viola', hint: 'Invasione', className: 'alarm-viola' },
  { id: 'bianco', label: 'Bianco', hint: 'Medico', className: 'alarm-bianco' },
  { id: 'crociera', label: 'Verde', hint: 'Crociera', className: 'alarm-verde' },
];

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
    { colore: 'ambra', dipartimento: 'Ingegneria', ha_testo: true },
    { colore: 'viola', dipartimento: 'Sicurezza', ha_testo: true },
    { colore: 'bianco', dipartimento: 'Medica', ha_testo: true },
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
        {COLORI.map((c) => {
          const proto = protocolloDi(c.id);
          const attivo = quadro?.allarme === c.id;
          return (
            <button
              key={c.id}
              type="button"
              className={`comms-color ${c.className} ${attivo ? 'active' : ''}`}
              disabled={busy}
              onClick={() => dichiara(c.id)}
            >
              <span className="comms-color-label">{c.label}</span>
              <span className="comms-color-hint">{proto?.dipartimento || c.hint}</span>
            </button>
          );
        })}
      </div>

      {esito ? <p className="comms-esito">{esito}</p> : null}
      {error ? <p className="comms-error">{error}</p> : null}
    </div>
  );
}
