import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileSignature, Loader2 } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { contrattiAzione, contrattiCreaProposta, contrattiGetQr, contrattiGetScheda } from '../api';
import { anteprimaModello, renderTestoContratto } from '../lib/contrattoTesto';

const STATO_LABEL = {
  IN_ATTESA: 'In attesa',
  STIPULATO: 'Stipulato',
  SCADUTO: 'Scaduto',
  RIFIUTATO: 'Rifiutato',
  RISOLTO: 'Risolto',
  ANNULLATO: 'Annullato',
};

function formatScadenza(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export default function ContrattiTab({ onLogout }) {
  const { selectedCharacterId, selectedCharacterData, personaggiList } = useCharacter();
  const [scheda, setScheda] = useState(null);
  const [errore, setErrore] = useState('');
  const [busy, setBusy] = useState(false);
  const [modelloId, setModelloId] = useState('');
  const [parametri, setParametri] = useState({});
  const [qr, setQr] = useState(null);

  const carica = useCallback(async () => {
    if (!selectedCharacterId) return;
    setErrore('');
    try {
      const data = await contrattiGetScheda(selectedCharacterId, onLogout);
      setScheda(data);
    } catch (e) {
      setErrore(e.message || 'Scheda contratti non disponibile.');
    }
  }, [selectedCharacterId, onLogout]);

  useEffect(() => {
    carica();
  }, [carica]);

  const modello = (scheda?.modelli || []).find((m) => m.id === modelloId);
  const nomePg = selectedCharacterData?.nome
    || (personaggiList || []).find((p) => String(p?.id) === String(selectedCharacterId))?.nome
    || '';
  const testoAnteprima = useMemo(
    () => anteprimaModello(modello, { nomeProponente: nomePg, valoriProponente: parametri }),
    [modello, nomePg, parametri],
  );

  const proponi = async () => {
    if (!modello) return;
    setBusy(true);
    setErrore('');
    try {
      const creato = await contrattiCreaProposta(
        selectedCharacterId,
        { modello_id: modello.id, parametri },
        onLogout,
      );
      setQr(creato.qr_png ? { id: creato.qr_code_id, png: creato.qr_png, nome: creato.nome } : null);
      setParametri({});
      await carica();
    } catch (e) {
      setErrore(e.message || 'Proposta non creata.');
    } finally {
      setBusy(false);
    }
  };

  const azione = async (contratto, nome, extra) => {
    setBusy(true);
    setErrore('');
    try {
      await contrattiAzione(selectedCharacterId, contratto.id, nome, extra || {}, onLogout);
      await carica();
    } catch (e) {
      setErrore(e.message || 'Azione non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  const mostraQr = async (contratto) => {
    setBusy(true);
    setErrore('');
    try {
      const data = await contrattiGetQr(selectedCharacterId, contratto.id, onLogout);
      setQr({ id: data.qr_code_id, png: data.qr_png, nome: contratto.nome });
    } catch (e) {
      setErrore(e.message || 'QR non disponibile.');
    } finally {
      setBusy(false);
    }
  };

  if (!scheda) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        {errore || <Loader2 className="animate-spin" />}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 text-gray-100">
      <header className="flex items-center gap-3">
        <FileSignature className="text-amber-300" />
        <div>
          <h1 className="text-xl font-black">Contratti</h1>
          <p className="text-sm text-gray-400">
            Slot proponente: {scheda.slot_usati} / {scheda.slot_totali}
          </p>
        </div>
      </header>
      {errore ? <p className="rounded border border-red-800 bg-red-950/40 p-2 text-sm text-red-300">{errore}</p> : null}

      {scheda.modelli?.length ? (
        <section className="space-y-3 rounded border border-gray-800 bg-gray-900/60 p-4">
          <h2 className="font-semibold">Nuova proposta</h2>
          <select
            className="w-full rounded border border-gray-700 bg-gray-950 p-2"
            value={modelloId}
            onChange={(e) => {
              setModelloId(e.target.value);
              setParametri({});
            }}
          >
            <option value="">Scegli un modello della tua Korp</option>
            {scheda.modelli.map((m) => (
              <option key={m.id} value={m.id}>{m.nome}</option>
            ))}
          </select>
          {modello ? (
            <>
              <p className="whitespace-pre-wrap text-sm text-gray-300">{testoAnteprima}</p>
              {(modello.parametri || [])
                .filter((p) => p.chi_compila === 'PROPONENTE')
                .map((p) => (
                  <label key={p.chiave} className="block text-sm">
                    <span className="text-gray-400">{p.etichetta}</span>
                    <input
                      className="mt-1 w-full rounded border border-gray-700 bg-gray-950 p-2"
                      value={parametri[p.chiave] ?? ''}
                      onChange={(e) => setParametri({ ...parametri, [p.chiave]: e.target.value })}
                    />
                  </label>
                ))}
              <button
                type="button"
                disabled={busy || !scheda.puo_proporre}
                onClick={proponi}
                className="rounded bg-amber-700 px-3 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {scheda.puo_proporre ? 'Crea proposta e QR' : 'Nessuno slot libero'}
              </button>
            </>
          ) : null}
        </section>
      ) : null}

      {qr?.png ? (
        <section className="rounded border border-amber-900/50 bg-gray-900 p-4 text-center">
          <p className="mb-2 text-sm text-amber-200">QR di «{qr.nome}» — codice {qr.id}</p>
          <img alt="QR contratto" className="mx-auto h-48 w-48 bg-white p-2" src={`data:image/png;base64,${qr.png}`} />
        </section>
      ) : null}

      <section className="space-y-3">
        <h2 className="font-semibold">I tuoi contratti</h2>
        {(scheda.contratti || []).length === 0 ? <p className="text-sm text-gray-500">Nessun contratto.</p> : null}
        {(scheda.contratti || []).map((c) => (
          <article key={c.id} className="space-y-2 rounded border border-gray-800 bg-gray-900/50 p-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold">{c.nome}</h3>
              <span className="text-xs uppercase text-gray-400">
                {c.ruolo} · {STATO_LABEL[c.stato] || c.stato}
                {c.scadenza ? ` · ${formatScadenza(c.scadenza)}` : ''}
              </span>
            </div>
            <p className="text-sm text-gray-400">
              {c.proponente?.nome}
              {c.cliente ? ` → ${c.cliente.nome}` : ' → in attesa del cliente'}
            </p>
            <p className="whitespace-pre-wrap text-sm text-gray-200">
              {renderTestoContratto(c.testo, {
                proponente: c.proponente?.nome,
                cliente: c.cliente?.nome || 'il sottoscrittore',
                scadenza: formatScadenza(c.scadenza),
                parametri: c.parametri || {},
              })}
            </p>
            <div className="flex flex-wrap gap-2">
              {c.stato === 'IN_ATTESA' && c.ruolo === 'PROPONENTE' ? (
                <>
                  <button type="button" disabled={busy} className="rounded bg-gray-700 px-2 py-1 text-xs" onClick={() => mostraQr(c)}>Mostra QR</button>
                  <button type="button" disabled={busy} className="rounded bg-gray-800 px-2 py-1 text-xs" onClick={() => azione(c, 'annulla')}>Annulla</button>
                </>
              ) : null}
              {c.azioni?.attiva && c.ruolo === 'PROPONENTE' ? (
                <button type="button" disabled={busy} className="rounded bg-indigo-800 px-2 py-1 text-xs" onClick={() => azione(c, 'attiva')}>Attiva</button>
              ) : null}
              {c.azioni?.ferita ? (
                <button type="button" disabled={busy} className="rounded bg-rose-900 px-2 py-1 text-xs" onClick={() => azione(c, 'ferita')}>Segnala ferita</button>
              ) : null}
              {c.azioni?.associa_post && c.ruolo === 'PROPONENTE' ? (
                <form
                  className="flex gap-1"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const postId = new FormData(e.currentTarget).get('post_id');
                    if (postId) azione(c, 'associa-post', { post_id: postId });
                  }}
                >
                  <input name="post_id" placeholder="ID post" className="w-24 rounded border border-gray-700 bg-gray-950 px-2 py-1 text-xs" />
                  <button type="submit" disabled={busy} className="rounded bg-fuchsia-900 px-2 py-1 text-xs">Associa post</button>
                </form>
              ) : null}
              {c.azioni?.servizio && c.ruolo === 'PROPONENTE' ? (
                <button type="button" disabled={busy} className="rounded bg-sky-900 px-2 py-1 text-xs" onClick={() => azione(c, 'servizio', { quantita: 1 })}>Registra 1 servizio</button>
              ) : null}
              {(c.adempimenti || []).filter((a) => a.stato === 'IN_ATTESA').map((a) => (
                <button
                  key={a.id}
                  type="button"
                  disabled={busy}
                  className="rounded bg-emerald-900 px-2 py-1 text-xs"
                  onClick={() => azione(c, 'conferma', { adempimento_id: a.id })}
                >
                  Conferma {a.note || a.codice}
                </button>
              ))}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
