import React, { useCallback, useEffect, useState } from 'react';
import { ClipboardCheck, Coins, Loader2, RefreshCw, Send, Trash2 } from 'lucide-react';
import {
  staffSondaggiAggiorna,
  staffSondaggiElimina,
  staffSondaggiGet,
  staffSondaggiImporta,
  staffSondaggiInoltra,
  staffSondaggiPatch,
  staffSondaggiPremi,
} from '../../api';
import {
  StaffToolShell,
  staffMutedClass,
  staffPageTitleClass,
  staffPanelClass,
  staffPrimaryBtnClass,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';

function messaggioErrore(errore) {
  return errore?.data?.error || errore?.message || 'Operazione non riuscita.';
}

function formattaQuando(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '';
  return data.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function etichettaRisposta(domanda, valore) {
  if (Array.isArray(valore)) return valore.join(', ');
  if (valore == null || valore === '') return '—';
  if (domanda?.tipo === 'valutazione') {
    const livelli = (domanda.opzioni || []).map((voce) => String(voce));
    const indice = livelli.indexOf(String(valore));
    if (indice >= 0) return `${indice + 1} su ${livelli.length}`;
  }
  return String(valore);
}

function vociRisposta(domanda, risposte) {
  if (domanda?.tipo === 'griglia') {
    return (domanda.righe || []).map((riga) => ({
      chiave: riga.id,
      etichetta: `${domanda.titolo} — ${riga.titolo}`,
      valore: etichettaRisposta(riga, risposte?.[riga.id]),
    }));
  }
  return [{
    chiave: domanda.id,
    etichetta: domanda.titolo,
    valore: etichettaRisposta(domanda, risposte?.[domanda.id]),
  }];
}

export default function SondaggiManager({ onLogout }) {
  const [url, setUrl] = useState('');
  const [aperto, setAperto] = useState(true);
  const [elenco, setElenco] = useState([]);
  const [dettaglio, setDettaglio] = useState(null);
  const [errore, setErrore] = useState('');
  const [info, setInfo] = useState('');
  const [occupato, setOccupato] = useState(false);

  const ricaricaLista = useCallback(async () => {
    const data = await staffSondaggiGet(onLogout);
    setElenco(data?.sondaggi || []);
  }, [onLogout]);

  const apri = useCallback(async (id) => {
    const data = await staffSondaggiGet(onLogout, id);
    setDettaglio(data);
  }, [onLogout]);

  useEffect(() => {
    let attivo = true;
    (async () => {
      try {
        const data = await staffSondaggiGet(onLogout);
        if (attivo) setElenco(data?.sondaggi || []);
      } catch (e) {
        if (attivo) setErrore(messaggioErrore(e));
      }
    })();
    return () => { attivo = false; };
  }, [onLogout]);

  const esegui = async (lavoro, messaggio) => {
    setOccupato(true);
    setErrore('');
    setInfo('');
    try {
      await lavoro();
      if (messaggio) setInfo(messaggio);
    } catch (e) {
      setErrore(messaggioErrore(e));
    } finally {
      setOccupato(false);
    }
  };

  const importa = () => esegui(async () => {
    const creato = await staffSondaggiImporta({ url, attivo: aperto }, onLogout);
    setUrl('');
    await ricaricaLista();
    await apri(creato.id);
  }, 'Modulo importato.');

  const salva = () => esegui(async () => {
    const aggiornato = await staffSondaggiPatch(dettaglio.id, {
      titolo: dettaglio.titolo,
      descrizione: dettaglio.descrizione,
      attivo: dettaglio.attivo,
      consenti_modifica: dettaglio.consenti_modifica,
      inoltra_email: dettaglio.inoltra_email,
      premio_pc: dettaglio.premio_pc,
      premio_crediti_correnti: dettaglio.premio_crediti_correnti,
      premio_crediti_deposito: dettaglio.premio_crediti_deposito,
    }, onLogout);
    setDettaglio(aggiornato);
    await ricaricaLista();
  }, 'Impostazioni salvate.');

  const aggiornaDaGoogle = () => esegui(async () => {
    const aggiornato = await staffSondaggiAggiorna(dettaglio.id, onLogout);
    setDettaglio(aggiornato);
    await ricaricaLista();
  }, 'Domande aggiornate dal modulo Google.');

  const inoltra = () => esegui(async () => {
    const aggiornato = await staffSondaggiInoltra(dettaglio.id, onLogout);
    setDettaglio(aggiornato);
    const esito = aggiornato.inoltro || {};
    setInfo(`Copiate sul foglio: ${esito.inviate || 0}. Errori: ${esito.errori || 0}. Saltate: ${esito.saltate || 0}.`);
    await ricaricaLista();
  });

  const accreditaPremi = () => esegui(async () => {
    const aggiornato = await staffSondaggiPremi(dettaglio.id, onLogout);
    setDettaglio(aggiornato);
    await ricaricaLista();
    setInfo(`Premi accreditati: ${aggiornato.premi_appena_erogati ?? 0}.`);
  });

  const elimina = () => {
    if (!dettaglio) return;
    if (!window.confirm(`Eliminare «${dettaglio.titolo}» e le risposte salvate nell'app?`)) return;
    esegui(async () => {
      await staffSondaggiElimina(dettaglio.id, onLogout);
      setDettaglio(null);
      await ricaricaLista();
    }, 'Sondaggio eliminato.');
  };

  return (
    <StaffToolShell>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4">
        <header className="min-w-0">
          <h2 className={`${staffPageTitleClass} flex items-center gap-2`}>
            <ClipboardCheck size={22} className="text-indigo-300" />
            Sondaggi
          </h2>
          <p className={`${staffMutedClass} mt-1 max-w-3xl`}>
            In Google Moduli apri Invia e incolla il link pubblico. I giocatori compilano il sondaggio
            con il layout dell&apos;app. Le risposte restano su KOR35 anche offline e, quando il master è online,
            vengono copiate nel foglio Google.
          </p>
        </header>

        <section className={`${staffPanelClass} space-y-3`}>
          <label className="block text-sm font-semibold text-gray-200" htmlFor="sondaggio-url">
            Link del modulo
          </label>
          <input
            id="sondaggio-url"
            type="url"
            inputMode="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://docs.google.com/forms/d/e/…/viewform"
            className="w-full min-h-11 rounded-lg border border-gray-600 bg-gray-950 px-3 text-base text-white outline-none focus:border-indigo-400"
          />
          <label className="flex min-h-11 items-center gap-3 text-sm text-gray-200">
            <input
              type="checkbox"
              className="h-5 w-5 accent-indigo-500"
              checked={aperto}
              onChange={(e) => setAperto(e.target.checked)}
            />
            Aprilo subito ai giocatori
          </label>
          <button type="button" className={`${staffPrimaryBtnClass} min-h-11`} disabled={occupato || !url.trim()} onClick={importa}>
            {occupato ? <Loader2 size={16} className="animate-spin" /> : null}
            Importa modulo
          </button>
        </section>

        {errore ? (
          <p role="alert" className="rounded-lg border border-rose-800 bg-rose-950/50 px-3 py-2 text-sm text-rose-100 break-words">
            {errore}
          </p>
        ) : null}
        {info ? (
          <p className="rounded-lg border border-emerald-800 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-100 break-words">
            {info}
          </p>
        ) : null}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
          <div className="space-y-2">
            {elenco.length === 0 ? (
              <p className={staffMutedClass}>Nessun sondaggio in questa campagna.</p>
            ) : elenco.map((riga) => (
              <button
                key={riga.id}
                type="button"
                onClick={() => esegui(() => apri(riga.id))}
                className={`w-full min-h-11 rounded-xl border px-3 py-2 text-left ${
                  dettaglio?.id === riga.id
                    ? 'border-indigo-500 bg-indigo-950/40'
                    : 'border-gray-700 bg-gray-900/60'
                }`}
              >
                <span className="block font-semibold text-white break-words">{riga.titolo}</span>
                <span className="text-xs text-gray-400">
                  {riga.attivo ? 'Aperto' : 'Chiuso'} · {riga.risposte_totali} risposte
                </span>
              </button>
            ))}
          </div>

          {dettaglio ? (
            <section className={`${staffPanelClass} min-w-0 space-y-4`}>
              <label className="block space-y-1">
                <span className="text-sm font-semibold text-gray-200">Titolo in app</span>
                <input
                  className="w-full min-h-11 rounded-lg border border-gray-600 bg-gray-950 px-3 text-base text-white"
                  value={dettaglio.titolo}
                  onChange={(e) => setDettaglio({ ...dettaglio, titolo: e.target.value })}
                />
              </label>
              <label className="block space-y-1">
                <span className="text-sm font-semibold text-gray-200">Testo introduttivo</span>
                <textarea
                  className="min-h-24 w-full rounded-lg border border-gray-600 bg-gray-950 px-3 py-2 text-base text-white"
                  value={dettaglio.descrizione}
                  onChange={(e) => setDettaglio({ ...dettaglio, descrizione: e.target.value })}
                />
              </label>
              <div className="space-y-2 rounded-xl border border-gray-700 bg-gray-950 p-3">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Coins size={16} className="shrink-0 text-amber-300" />
                  Premio al primo invio
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {[
                    ['premio_pc', 'PC', '1'],
                    ['premio_crediti_correnti', 'Crediti correnti', '0.01'],
                    ['premio_crediti_deposito', 'Crediti di deposito', '0.01'],
                  ].map(([campo, etichetta, step]) => (
                    <label key={campo} className="block min-w-0 space-y-1">
                      <span className="text-sm text-gray-300">{etichetta}</span>
                      <input
                        type="number"
                        min="0"
                        step={step}
                        inputMode="decimal"
                        className="min-h-11 w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-base text-white"
                        value={dettaglio[campo] ?? 0}
                        onChange={(e) => setDettaglio({ ...dettaglio, [campo]: e.target.value })}
                      />
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-500 break-words">
                  Zero su una voce significa nessun premio di quel tipo. Chi ha già compilato prima di salvare gli importi non lo riceve da solo.
                </p>
                {(dettaglio.premi_mancanti || 0) > 0 ? (
                  <button type="button" className={`${staffSecondaryBtnClass} min-h-11`} disabled={occupato} onClick={accreditaPremi}>
                    Accredita a chi ha già risposto ({dettaglio.premi_mancanti})
                  </button>
                ) : null}
              </div>
              <div className="flex flex-col gap-2">
                {[
                  ['attivo', 'Visibile ai giocatori'],
                  ['consenti_modifica', 'Consenti di modificare la risposta'],
                  ['inoltra_email', 'Copia l\'email dell\'account nel foglio Google'],
                ].map(([campo, etichetta]) => (
                  <label key={campo} className="flex min-h-11 items-center gap-3 text-sm text-gray-200">
                    <input
                      type="checkbox"
                      className="h-5 w-5 accent-indigo-500"
                      checked={!!dettaglio[campo]}
                      onChange={(e) => setDettaglio({ ...dettaglio, [campo]: e.target.checked })}
                    />
                    <span className="break-words">{etichetta}</span>
                  </label>
                ))}
              </div>
              <p className="text-xs text-gray-500 break-words">
                Se consenti la modifica, il foglio Google riceve una nuova riga: Google non aggiorna quella precedente.
                Risposte nell&apos;app: {dettaglio.risposte_totali}. Già copiate: {dettaglio.risposte_inoltrate}. In sospeso: {dettaglio.risposte_in_sospeso}.
              </p>
              {(dettaglio.avvisi || []).length ? (
                <ul className="list-disc space-y-1 pl-5 text-sm text-amber-200">
                  {dettaglio.avvisi.map((voce) => <li key={voce} className="break-words">{voce}</li>)}
                </ul>
              ) : null}
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <button type="button" className={`${staffPrimaryBtnClass} min-h-11`} disabled={occupato} onClick={salva}>Salva</button>
                <button type="button" className={`${staffSecondaryBtnClass} min-h-11`} disabled={occupato} onClick={aggiornaDaGoogle}>
                  <RefreshCw size={16} /> Aggiorna da Google
                </button>
                <button type="button" className={`${staffSecondaryBtnClass} min-h-11`} disabled={occupato} onClick={inoltra}>
                  <Send size={16} /> Copia in sospeso sul foglio
                </button>
                <button type="button" className={`${staffSecondaryBtnClass} min-h-11 text-rose-200`} disabled={occupato} onClick={elimina}>
                  <Trash2 size={16} /> Elimina
                </button>
              </div>
              <div className="space-y-2">
                <h3 className="text-sm font-bold uppercase tracking-wide text-gray-400">Domande</h3>
                <ol className="space-y-1 text-sm text-gray-200">
                  {(dettaglio.domande || []).filter((d) => d.tipo !== 'sezione').map((domanda, indice) => (
                    <li key={domanda.id} className="break-words">
                      {indice + 1}. {domanda.titolo}
                      {!domanda.supportata ? ' (solo Google)' : ''}
                    </li>
                  ))}
                </ol>
              </div>
              <div className="space-y-2">
                <h3 className="text-sm font-bold uppercase tracking-wide text-gray-400">Risposte</h3>
                {(dettaglio.risposte || []).length === 0 ? (
                  <p className={staffMutedClass}>Ancora nessuna risposta.</p>
                ) : (dettaglio.risposte || []).map((riga) => (
                  <article key={riga.id} className="rounded-lg border border-gray-700 bg-gray-950 p-3">
                    <p className="font-semibold text-white break-words">
                      {riga.personaggio || riga.utente || 'Giocatore'}
                      <span className="ml-2 text-xs font-normal text-gray-400">{formattaQuando(riga.creata_il)}</span>
                    </p>
                    <p className="text-xs text-gray-500">
                      {riga.google_inviato_il ? `Sul foglio dal ${formattaQuando(riga.google_inviato_il)}` : 'Non ancora sul foglio Google'}
                      {riga.google_errore ? ` · ${riga.google_errore}` : ''}
                      {riga.premio_erogato ? ` · Premio: ${riga.premio.pc} PC, ${riga.premio.crediti_correnti} CR correnti, ${riga.premio.crediti_deposito} CR deposito` : ''}
                    </p>
                    <dl className="mt-2 space-y-1">
                      {(dettaglio.domande || []).filter((d) => d.supportata && d.tipo !== 'sezione').flatMap((domanda) => (
                        vociRisposta(domanda, riga.risposte).map((voce) => (
                          <div key={voce.chiave} className="grid grid-cols-1 gap-0.5 sm:grid-cols-[10rem_minmax(0,1fr)]">
                            <dt className="text-xs text-gray-500 break-words">{voce.etichetta}</dt>
                            <dd className="text-sm text-gray-100 break-words">{voce.valore}</dd>
                          </div>
                        ))
                      ))}
                    </dl>
                  </article>
                ))}
              </div>
            </section>
          ) : (
            <p className={staffMutedClass}>Seleziona un sondaggio per vedere le risposte.</p>
          )}
        </div>
      </div>
    </StaffToolShell>
  );
}
