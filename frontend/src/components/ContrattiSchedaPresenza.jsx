import React, { useEffect, useState } from 'react';
import { FileSignature } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { contrattiGetScheda } from '../api';
import { contrattiComeCliente, numeriContratti, slotLiberi } from '../lib/contrattiRiepilogo';
import { renderTestoContratto } from '../lib/contrattoTesto';

const STATO_LABEL = {
  STIPULATO: 'Stipulato',
  SCADUTO: 'Scaduto',
  RISOLTO: 'Risolto',
};

function formatScadenza(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '';
  return data.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function useContrattiDati(personaggioId, onLogout, enabled) {
  const [dati, setDati] = useState(null);
  useEffect(() => {
    if (!enabled || !personaggioId) {
      setDati(null);
      return undefined;
    }
    let cancel = false;
    contrattiGetScheda(personaggioId, onLogout)
      .then((data) => {
        if (!cancel) setDati(data);
      })
      .catch(() => {
        if (!cancel) setDati(null);
      });
    return () => {
      cancel = true;
    };
  }, [personaggioId, onLogout, enabled]);
  return dati;
}

function ElencoCliente({ contratti, dettaglio }) {
  if (!contratti.length) {
    return <p className="text-sm text-gray-500">Nessun contratto stipulato come cliente.</p>;
  }
  return (
    <ul className="space-y-2">
      {contratti.map((c) => {
        const scadenza = formatScadenza(c.scadenza);
        const testo = renderTestoContratto(c.testo, {
          proponente: c.proponente?.nome,
          cliente: c.cliente?.nome || 'il sottoscrittore',
          scadenza,
          parametri: c.parametri || {},
        });
        return (
          <li key={c.id} className="rounded-lg border border-gray-700 bg-gray-950/50 p-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-semibold text-gray-100">{c.nome || 'Contratto'}</p>
              <p className="text-xs uppercase text-gray-400">
                {STATO_LABEL[c.stato] || c.stato}
                {scadenza ? ` · fino al ${scadenza}` : ''}
              </p>
            </div>
            <p className="text-sm text-gray-400">Offerente: {c.proponente?.nome || '—'}</p>
            {dettaglio ? (
              <p className="mt-2 whitespace-pre-wrap text-sm text-gray-200">{testo}</p>
            ) : (
              <details className="mt-1">
                <summary className="cursor-pointer text-xs text-amber-200/80">Testo del contratto</summary>
                <p className="mt-1 whitespace-pre-wrap text-sm text-gray-200">{testo}</p>
              </details>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function Contatori({ attiviCliente, attiviOfferente, liberi }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="col-span-2 rounded-md bg-gray-800 p-2">
        <p className="text-xs text-gray-400">Contratti liberi</p>
        <p className="text-2xl font-black tabular-nums text-white">{liberi}</p>
        <p className="text-[11px] text-gray-500">Slot ancora apribili come proponente.</p>
      </div>
      <div className="rounded-md bg-gray-800 p-2">
        <p className="text-xs text-gray-400">Contratti attivi (cliente)</p>
        <p className="text-2xl font-black tabular-nums text-white">{attiviCliente}</p>
      </div>
      <div className="rounded-md bg-gray-800 p-2">
        <p className="text-xs text-gray-400">Contratti attivi (offerente)</p>
        <p className="text-2xl font-black tabular-nums text-white">{attiviOfferente}</p>
      </div>
    </div>
  );
}

/**
 * Presenza dei contratti sulla scheda e nel tab Economia.
 * modo "scheda": contatori + elenco compatto come cliente.
 * modo "cliente": sottoscheda con il testo dei contratti stipulati come cliente.
 */
export default function ContrattiSchedaPresenza({ personaggioId, onLogout, modo = 'scheda' }) {
  const { canAccessModulo } = useCharacter();
  const abilitato = !!canAccessModulo?.('contratti');
  const dati = useContrattiDati(personaggioId, onLogout, abilitato);
  if (!abilitato || !dati) return null;

  const { attiviCliente, attiviOfferente } = numeriContratti(dati);
  const comeCliente = contrattiComeCliente(dati.contratti);

  if (modo === 'cliente') {
    return (
      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4">
        <h3 className="mb-1 flex items-center gap-2 font-semibold">
          <FileSignature className="h-4 w-4 text-amber-300" />
          Contratti come cliente
        </h3>
        <p className="mb-3 text-xs text-gray-500">
          Attivi: {attiviCliente}. Qui restano anche quelli scaduti o risolti.
        </p>
        <ElencoCliente contratti={comeCliente} dettaglio />
      </section>
    );
  }

  return (
    <section className="mx-auto mb-6 max-w-2xl space-y-3">
      <Contatori attiviCliente={attiviCliente} attiviOfferente={attiviOfferente} liberi={slotLiberi(dati)} />
      {comeCliente.length ? (
        <div>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-200">
            <FileSignature className="h-4 w-4 text-amber-300" />
            Contratti come cliente
          </h3>
          <ElencoCliente contratti={comeCliente} dettaglio={false} />
        </div>
      ) : null}
    </section>
  );
}
