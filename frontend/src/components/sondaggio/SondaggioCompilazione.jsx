import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ExternalLink, Loader2, Star } from 'lucide-react';

const campoClass =
  'w-full min-h-11 rounded-lg border border-gray-600 bg-gray-950 px-3 py-2 text-base text-white outline-none focus:border-indigo-400';

function statoIniziale(sondaggio) {
  const base = {};
  const salvate = sondaggio?.mia_risposta || {};
  for (const domanda of sondaggio?.domande || []) {
    if (!domanda.supportata || domanda.tipo === 'sezione') continue;
    const salvata = salvate[domanda.id];
    if (domanda.tipo === 'caselle') {
      base[domanda.id] = Array.isArray(salvata) ? salvata : [];
    } else {
      base[domanda.id] = salvata == null ? '' : String(salvata);
    }
  }
  return base;
}

function titoliMancanti(domande, valori) {
  const mancanti = [];
  for (const domanda of domande || []) {
    if (!domanda.supportata || !domanda.obbligatoria || domanda.tipo === 'sezione') continue;
    const valore = valori[domanda.id];
    const vuoto = domanda.tipo === 'caselle'
      ? !valore || valore.length === 0
      : !String(valore || '').trim();
    if (vuoto) mancanti.push(domanda.titolo);
  }
  return mancanti;
}

function testoRisposta(domanda, valori) {
  const valore = valori?.[domanda.id];
  if (Array.isArray(valore)) return valore.join(', ');
  if (valore == null || valore === '') return '—';
  if (domanda.tipo === 'scala') {
    const etichetta = Number(valore) === Number(domanda.scala_max)
      ? domanda.scala_max_etichetta
      : Number(valore) === Number(domanda.scala_min)
        ? domanda.scala_min_etichetta
        : '';
    return etichetta ? `${valore} · ${etichetta}` : String(valore);
  }
  if (domanda.tipo === 'valutazione') {
    const livelli = livelliValutazione(domanda);
    const indice = livelli.indexOf(String(valore));
    if (indice < 0) return String(valore);
    return `${indice + 1} su ${livelli.length}`;
  }
  return String(valore);
}

function livelliValutazione(domanda) {
  const opzioni = (domanda.opzioni || []).map((voce) => String(voce)).filter(Boolean);
  if (opzioni.length) return opzioni;
  const minimo = Number(domanda.scala_min ?? 1);
  const massimo = Number(domanda.scala_max ?? 5);
  const gradini = [];
  for (let n = minimo; n <= massimo; n += 1) gradini.push(String(n));
  return gradini.length ? gradini : ['1', '2', '3', '4', '5'];
}

function BloccoDomanda({ domanda, valore, onChange, solaLettura }) {
  if (domanda.tipo === 'sezione') {
    return (
      <div className="pt-2">
        <h3 className="text-base font-bold text-indigo-200 break-words">{domanda.titolo}</h3>
        {domanda.descrizione ? (
          <p className="mt-1 text-sm text-gray-400 break-words">{domanda.descrizione}</p>
        ) : null}
      </div>
    );
  }

  if (!domanda.supportata) {
    return (
      <div className="rounded-xl border border-amber-700/50 bg-amber-950/40 p-3">
        <p className="font-semibold text-amber-100 break-words">{domanda.titolo}</p>
        <p className="mt-1 text-sm text-amber-200/80">
          Questa domanda si compila solo sul modulo Google, quando c&apos;è connessione.
        </p>
      </div>
    );
  }

  return (
    <fieldset className="min-w-0 space-y-2">
      <legend className="text-sm font-semibold text-white break-words">
        {domanda.titolo}
        {domanda.obbligatoria ? <span className="text-rose-300"> *</span> : null}
      </legend>
      {domanda.descrizione ? (
        <p className="text-sm text-gray-400 break-words">{domanda.descrizione}</p>
      ) : null}
      {solaLettura ? (
        <p className="rounded-lg bg-gray-950 px-3 py-2 text-base text-gray-100 break-words">
          {testoRisposta(domanda, { [domanda.id]: valore })}
        </p>
      ) : (
        <Controllo domanda={domanda} valore={valore} onChange={onChange} />
      )}
    </fieldset>
  );
}

function Controllo({ domanda, valore, onChange }) {
  if (domanda.tipo === 'testo_lungo') {
    return (
      <textarea
        className={`${campoClass} min-h-28`}
        value={valore || ''}
        maxLength={5000}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (domanda.tipo === 'testo_breve') {
    return (
      <input
        type="text"
        className={campoClass}
        value={valore || ''}
        maxLength={500}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (domanda.tipo === 'data') {
    return (
      <input
        type="date"
        className={campoClass}
        value={valore || ''}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (domanda.tipo === 'ora') {
    return (
      <input
        type="time"
        className={campoClass}
        value={valore || ''}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (domanda.tipo === 'menu') {
    return (
      <select className={campoClass} value={valore || ''} onChange={(e) => onChange(e.target.value)}>
        <option value="">Scegli…</option>
        {(domanda.opzioni || []).map((opzione) => (
          <option key={opzione} value={opzione}>{opzione}</option>
        ))}
      </select>
    );
  }
  if (domanda.tipo === 'scelta_singola') {
    return (
      <div className="space-y-2">
        {(domanda.opzioni || []).map((opzione) => (
          <label key={opzione} className="flex min-h-11 items-center gap-3 rounded-lg border border-gray-700 bg-gray-950 px-3 text-base text-gray-100">
            <input
              type="radio"
              className="h-5 w-5 shrink-0 accent-indigo-500"
              name={domanda.id}
              value={opzione}
              checked={valore === opzione}
              onChange={() => onChange(opzione)}
            />
            <span className="break-words">{opzione}</span>
          </label>
        ))}
      </div>
    );
  }
  if (domanda.tipo === 'caselle') {
    const scelte = Array.isArray(valore) ? valore : [];
    return (
      <div className="space-y-2">
        {(domanda.opzioni || []).map((opzione) => {
          const attiva = scelte.includes(opzione);
          return (
            <label key={opzione} className="flex min-h-11 items-center gap-3 rounded-lg border border-gray-700 bg-gray-950 px-3 text-base text-gray-100">
              <input
                type="checkbox"
                className="h-5 w-5 shrink-0 accent-indigo-500"
                checked={attiva}
                onChange={() => {
                  onChange(attiva ? scelte.filter((voce) => voce !== opzione) : [...scelte, opzione]);
                }}
              />
              <span className="break-words">{opzione}</span>
            </label>
          );
        })}
      </div>
    );
  }
  if (domanda.tipo === 'valutazione') {
    const livelli = livelliValutazione(domanda);
    const selezionato = livelli.indexOf(String(valore || ''));
    return (
      <div className="space-y-2">
        <div className="flex flex-wrap gap-1" role="radiogroup" aria-label={domanda.titolo}>
          {livelli.map((etichetta, indice) => {
            const attiva = selezionato >= 0 && indice <= selezionato;
            return (
              <button
                key={etichetta}
                type="button"
                role="radio"
                aria-checked={selezionato === indice}
                aria-label={`${indice + 1} su ${livelli.length}`}
                className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg"
                onClick={() => onChange(etichetta)}
              >
                <Star
                  size={28}
                  className={attiva ? 'fill-amber-400 text-amber-400' : 'text-gray-500'}
                  aria-hidden
                />
              </button>
            );
          })}
        </div>
        {(domanda.scala_min_etichetta || domanda.scala_max_etichetta) ? (
          <p className="flex justify-between gap-3 text-xs text-gray-400">
            <span className="break-words">{domanda.scala_min_etichetta}</span>
            <span className="break-words text-right">{domanda.scala_max_etichetta}</span>
          </p>
        ) : null}
      </div>
    );
  }
  if (domanda.tipo === 'scala') {
    const minimo = Number(domanda.scala_min ?? 1);
    const massimo = Number(domanda.scala_max ?? 5);
    const gradini = [];
    for (let n = minimo; n <= massimo; n += 1) gradini.push(n);
    return (
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {gradini.map((n) => (
            <button
              key={n}
              type="button"
              className={`min-h-11 min-w-11 rounded-lg px-3 text-base font-bold ${
                String(valore) === String(n)
                  ? 'bg-indigo-600 text-white'
                  : 'border border-gray-600 bg-gray-950 text-gray-200'
              }`}
              onClick={() => onChange(String(n))}
            >
              {n}
            </button>
          ))}
        </div>
        {(domanda.scala_min_etichetta || domanda.scala_max_etichetta) ? (
          <p className="flex justify-between gap-3 text-xs text-gray-400">
            <span className="break-words">{domanda.scala_min_etichetta}</span>
            <span className="break-words text-right">{domanda.scala_max_etichetta}</span>
          </p>
        ) : null}
      </div>
    );
  }
  return null;
}

export default function SondaggioCompilazione({ sondaggio, invio = false, errore = '', onInvia }) {
  const [valori, setValori] = useState(() => statoIniziale(sondaggio));
  const [erroreLocale, setErroreLocale] = useState('');
  const solaLettura = !!(sondaggio?.gia_risposto && !sondaggio?.consenti_modifica);

  useEffect(() => {
    setValori(statoIniziale(sondaggio));
    setErroreLocale('');
  }, [sondaggio]);

  const messaggio = erroreLocale || errore;
  const domande = sondaggio?.domande || [];
  const titoloBottone = useMemo(() => {
    if (sondaggio?.gia_risposto && sondaggio?.consenti_modifica) return 'Aggiorna risposta';
    return 'Invia sondaggio';
  }, [sondaggio]);

  const invia = (evento) => {
    evento.preventDefault();
    const mancanti = titoliMancanti(domande, valori);
    if (mancanti.length) {
      setErroreLocale(`Rispondi a «${mancanti[0]}».`);
      return;
    }
    setErroreLocale('');
    onInvia?.(valori);
  };

  if (solaLettura) {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-2 rounded-xl border border-emerald-800 bg-emerald-950/40 p-3 text-emerald-100">
          <CheckCircle2 className="mt-0.5 shrink-0" size={18} />
          <p className="text-sm">Risposta registrata. Grazie.</p>
        </div>
        {domande.map((domanda) => (
          <BloccoDomanda
            key={domanda.id}
            domanda={domanda}
            valore={sondaggio.mia_risposta?.[domanda.id]}
            solaLettura
          />
        ))}
      </div>
    );
  }

  return (
    <form className="space-y-5" onSubmit={invia}>
      {sondaggio?.link_esterno ? (
        <a
          href={sondaggio.link_esterno}
          target="_blank"
          rel="noreferrer"
          className="flex min-h-11 items-center gap-2 rounded-xl border border-amber-700/60 bg-amber-950/40 px-3 py-2 text-sm text-amber-100"
        >
          <ExternalLink size={16} className="shrink-0" />
          <span className="break-words">Alcune domande restano sul modulo Google originale.</span>
        </a>
      ) : null}
      {domande.map((domanda) => (
        <BloccoDomanda
          key={domanda.id}
          domanda={domanda}
          valore={valori[domanda.id]}
          onChange={(nuovo) => setValori((corrente) => ({ ...corrente, [domanda.id]: nuovo }))}
        />
      ))}
      {messaggio ? (
        <p role="alert" className="rounded-lg border border-rose-800 bg-rose-950/50 px-3 py-2 text-sm text-rose-100 break-words">
          {messaggio}
        </p>
      ) : null}
      <div className="sticky bottom-0 z-10 -mx-4 border-t border-gray-800 bg-gray-900/95 px-4 py-3 backdrop-blur">
        <button
          type="submit"
          disabled={invio}
          className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 text-base font-bold text-white disabled:opacity-60"
        >
          {invio ? <Loader2 className="animate-spin" size={18} /> : null}
          {titoloBottone}
        </button>
      </div>
    </form>
  );
}
