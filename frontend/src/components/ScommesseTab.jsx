import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Trophy, Ticket, Key, ChevronLeft, CheckCircle2, XCircle, Clock, X } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import {
  scommesseGeneraCodice,
  scommesseGetCalendari,
  scommesseGetCalendario,
  scommesseGetMiePuntate,
  scommesseGetMieiCodici,
  scommesseGetSquadraStorico,
  scommessePiazzaPuntata,
} from '../api';
import { esitiScommessa, formattaRisultato, labelTipoRisultato, pareggioConsentito } from '../scommesse/risultatiSport';

const ESITO_LABEL = { V: 'Vittoria', S: 'Sconfitta', P: 'Pareggio' };
const ESITO_CLASS = {
  V: 'bg-emerald-900/50 text-emerald-300',
  S: 'bg-red-900/50 text-red-300',
  P: 'bg-gray-700 text-gray-300',
};

function NomeSquadraClick({ id, nome, onClick }) {
  return (
    <button
      type="button"
      onClick={() => onClick(id, nome)}
      className="font-bold text-indigo-300 underline decoration-indigo-500/50 underline-offset-2 hover:text-indigo-200"
    >
      {nome}
    </button>
  );
}

function SquadraStoricoModal({ squadra, storico, loading, onClose, onOpenAvversario }) {
  if (!squadra) return null;
  const risultati = storico?.risultati || [];

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/70 p-4 sm:items-center" onClick={onClose}>
      <div
        className="flex max-h-[85vh] w-full max-w-md flex-col rounded-t-xl border border-gray-600 bg-gray-800 shadow-xl sm:rounded-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-gray-700 p-4">
          <div>
            <h3 className="text-lg font-bold">{storico?.squadra?.nome || squadra.nome}</h3>
            <p className="text-xs text-gray-400">
              {storico?.squadra?.sport_nome || ''}
              {storico?.squadra?.potenza != null ? ` · Potenza ${storico.squadra.potenza}` : ''}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-white" aria-label="Chiudi">
            <X size={22} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex justify-center py-8 text-gray-400">
              <Loader2 className="animate-spin" size={28} />
            </div>
          )}
          {!loading && risultati.length === 0 && (
            <p className="text-sm text-gray-500">Nessun risultato pubblicato per questa squadra.</p>
          )}
          {!loading && risultati.length > 0 && (
            <ul className="space-y-3">
              {risultati.map((r, idx) => (
                <li key={`${r.data_risoluzione}-${idx}`} className="rounded-lg border border-gray-700 bg-gray-900/60 p-3 text-sm">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-bold ${ESITO_CLASS[r.esito] || ESITO_CLASS.P}`}>
                      {ESITO_LABEL[r.esito] || r.esito}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(r.data_risoluzione).toLocaleDateString('it-IT')}
                    </span>
                  </div>
                  <p className="text-gray-200">
                    {r.in_casa ? 'Casa' : 'Trasferta'} vs{' '}
                    <button
                      type="button"
                      className="text-indigo-300 hover:underline"
                      onClick={() => onOpenAvversario(r.avversario_id, r.avversario_nome)}
                    >
                      {r.avversario_nome}
                    </button>
                  </p>
                  {r.gol_fatti != null && (
                    <p className="mt-1 text-xs text-gray-400">
                      Risultato {r.risultato_formattato || formattaRisultato(r.tipo_risultato, r.gol_fatti, r.gol_subiti)}
                      {r.calendario_titolo ? ` · ${r.calendario_titolo}` : ''}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function getValoreAllFromChar(char) {
  if (!char?.punteggi_base) return 0;
  const entries = Object.entries(char.punteggi_base);
  for (const [nome, val] of entries) {
    if (nome.toLowerCase().includes('allibr') || nome === 'ALL') {
      return Number(val) || 0;
    }
  }
  return 0;
}

const ScommesseTab = ({ onLogout }) => {
  const { selectedCharacterData: char, selectedCharacterId, refreshCharacterData } = useCharacter();
  const [view, setView] = useState('list');
  const [calendari, setCalendari] = useState([]);
  const [calendarioDetail, setCalendarioDetail] = useState(null);
  const [puntate, setPuntate] = useState([]);
  const [codici, setCodici] = useState([]);
  const [valoreAll, setValoreAll] = useState(0);
  const [config, setConfig] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [listRefreshing, setListRefreshing] = useState(false);
  const [openingCalendarioId, setOpeningCalendarioId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState('');
  const [selezioni, setSelezioni] = useState({});
  const [importo, setImporto] = useState('5');
  const [codiceInput, setCodiceInput] = useState('');
  const [squadraModal, setSquadraModal] = useState(null);
  const [squadraStorico, setSquadraStorico] = useState(null);
  const [storicoLoading, setStoricoLoading] = useState(false);

  const isAllibratore = valoreAll > 0;

  const pgId = char?.id ?? selectedCharacterId;

  const loadList = useCallback(async ({ silent = false } = {}) => {
    if (silent) setListRefreshing(true);
    else {
      setInitialLoading(true);
      setStatus('');
    }
    try {
      const calRes = await scommesseGetCalendari(onLogout);
      const calList = Array.isArray(calRes?.calendari) ? calRes.calendari : (Array.isArray(calRes) ? calRes : []);
      setCalendari(calList);
      setConfig(calRes?.config || null);

      if (pgId) {
        const [pun, codRes] = await Promise.all([
          scommesseGetMiePuntate(pgId, onLogout),
          scommesseGetMieiCodici(pgId, onLogout),
        ]);
        setPuntate(Array.isArray(pun) ? pun : []);
        setCodici(Array.isArray(codRes?.codici) ? codRes.codici : (Array.isArray(codRes) ? codRes : []));
        setValoreAll(Number(codRes?.valore_all ?? getValoreAllFromChar(char)) || 0);
      } else {
        setPuntate([]);
        setCodici([]);
        setValoreAll(0);
      }
    } catch (e) {
      setStatus(e.message);
    } finally {
      if (silent) setListRefreshing(false);
      else setInitialLoading(false);
    }
  }, [onLogout, pgId]);

  useEffect(() => { loadList(); }, [loadList]);

  const apriStoricoSquadra = async (squadraId, squadraNome) => {
    setSquadraModal({ id: squadraId, nome: squadraNome });
    setSquadraStorico(null);
    setStoricoLoading(true);
    try {
      const data = await scommesseGetSquadraStorico(squadraId, onLogout);
      setSquadraStorico(data);
    } catch (e) {
      setStatus(e.message);
      setSquadraModal(null);
    } finally {
      setStoricoLoading(false);
    }
  };

  const openCalendario = async (id) => {
    const calId = id != null ? String(id) : '';
    if (!calId || openingCalendarioId) return;
    setOpeningCalendarioId(calId);
    setStatus('');
    try {
      const data = await scommesseGetCalendario(calId, onLogout);
      if (!data?.id) {
        throw new Error('Risposta calendario non valida.');
      }
      setCalendarioDetail(data);
      setSelezioni({});
      setView('detail');
    } catch (e) {
      const msg = e?.message || 'Impossibile aprire il calendario.';
      setStatus(msg.includes('404') || msg.toLowerCase().includes('non disponibile')
        ? 'Calendario non più disponibile. Aggiorna la pagina.'
        : msg);
    } finally {
      setOpeningCalendarioId(null);
    }
  };

  const esitiPerIncontro = (inc, fallbackPareggio) => {
    const pareggioOk = inc.pareggio_consentito ?? fallbackPareggio;
    return esitiScommessa(pareggioOk);
  };

  const toggleSelezione = (incontroId, esito, puoScommettere, messaggioChiuso) => {
    if (!puoScommettere) {
      setStatus(messaggioChiuso);
      return;
    }
    setSelezioni((prev) => {
      const cur = prev[incontroId];
      if (cur === esito) {
        const next = { ...prev };
        delete next[incontroId];
        return next;
      }
      return { ...prev, [incontroId]: esito };
    });
  };

  const quotaPreview = (() => {
    if (!calendarioDetail?.incontri) return '1.00';
    const keys = Object.keys(selezioni);
    if (!keys.length) return '1.00';
    let tot = 1;
    for (const inc of calendarioDetail.incontri) {
      const esito = selezioni[inc.id];
      if (!esito) continue;
      const pareggioRiga = inc.pareggio_consentito ?? pareggioConsentito(calendarioDetail.sport_tipo_risultato);
      const q = esito === '1'
        ? Number(inc.quota_casa)
        : esito === 'X' && pareggioRiga
          ? Number(inc.quota_pareggio)
          : Number(inc.quota_trasferta);
      tot *= q;
    }
    return tot.toFixed(2);
  })();

  const handlePuntata = async () => {
    if (!selectedCharacterId || !calendarioDetail) return;
    const selezioniList = Object.entries(selezioni).map(([incontro_id, esito]) => ({ incontro_id, esito }));
    if (!selezioniList.length) {
      setStatus('Seleziona almeno un esito.');
      return;
    }
    setSubmitting(true);
    setStatus('');
    try {
      await scommessePiazzaPuntata(
        char?.id ?? selectedCharacterId,
        {
          calendario_id: calendarioDetail.id,
          importo,
          codice: codiceInput.trim() || undefined,
          selezioni: selezioniList,
        },
        onLogout,
      );
      await refreshCharacterData();
      await loadList({ silent: true });
      setSelezioni({});
      setCodiceInput('');
      setStatus('Scommessa registrata!');
    } catch (e) {
      setStatus(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleGeneraCodice = async () => {
    const pgId = char?.id ?? selectedCharacterId;
    if (!pgId) return;
    setSubmitting(true);
    try {
      const nuovo = await scommesseGeneraCodice(pgId, onLogout);
      setCodici((prev) => [nuovo, ...prev]);
      setValoreAll((v) => v || 1);
      setStatus(`Codice generato: ${nuovo.codice}`);
    } catch (e) {
      setStatus(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (initialLoading && view === 'list') {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        <Loader2 className="animate-spin" size={32} />
      </div>
    );
  }

  if (view === 'detail' && calendarioDetail) {
    const puoScommettere = !!calendarioDetail.scommesse_aperte;
    const risultatiPubblicati = !!calendarioDetail.risultati_visibili;
    const pareggioOk = calendarioDetail.sport_pareggio_consentito
      ?? pareggioConsentito(calendarioDetail.sport_tipo_risultato);
    const tipoSport = calendarioDetail.sport_tipo_risultato;
    const messaggioChiuso = risultatiPubblicati
      ? 'Scommesse chiuse: risultati già pubblicati.'
      : calendarioDetail.data_apertura
        ? `Scommesse aprono il ${new Date(calendarioDetail.data_apertura).toLocaleString('it-IT')}`
        : 'Scommesse non ancora aperte.';
    return (
      <div className="flex h-full flex-col bg-gray-900 text-gray-100">
        <SquadraStoricoModal
          squadra={squadraModal}
          storico={squadraStorico}
          loading={storicoLoading}
          onClose={() => { setSquadraModal(null); setSquadraStorico(null); }}
          onOpenAvversario={apriStoricoSquadra}
        />
        <div className="border-b border-gray-700 px-4 py-3">
          <button type="button" onClick={() => { setView('list'); setCalendarioDetail(null); loadList({ silent: true }); }} className="mb-2 flex items-center gap-1 text-sm text-indigo-400">
            <ChevronLeft size={16} /> Indietro
          </button>
          <h2 className="text-lg font-bold">{calendarioDetail.titolo || calendarioDetail.sport_nome}</h2>
          <p className="text-xs text-gray-400">
            {calendarioDetail.sport_tipo_risultato_label || labelTipoRisultato(tipoSport)}
            {pareggioOk ? '' : ' · senza pareggio'}
            {' · '}Risultati: {new Date(calendarioDetail.data_risoluzione).toLocaleString('it-IT')}
            {risultatiPubblicati ? ' (pubblicati)' : ' (nascosti)'}
          </p>
          {puoScommettere && (
            <p className="mt-2 rounded bg-indigo-950/50 px-2 py-1 text-xs text-indigo-200">
              Scommesse aperte — scegli gli esiti e inserisci l&apos;importo in basso
            </p>
          )}
          {!puoScommettere && risultatiPubblicati && (
            <p className="mt-2 rounded bg-emerald-950/40 px-2 py-1 text-xs text-emerald-300">
              Scommesse chiuse — consultazione risultati
            </p>
          )}
          {!puoScommettere && !risultatiPubblicati && (
            <p className="mt-2 rounded bg-amber-950/40 px-2 py-1 text-xs text-amber-200">
              {messaggioChiuso}
            </p>
          )}
          {status && (
            <p className="mt-2 rounded border border-amber-600/40 bg-amber-950/30 px-2 py-1 text-xs text-amber-200">
              {status}
            </p>
          )}
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {(calendarioDetail.incontri?.length ?? 0) === 0 && (
            <p className="text-center text-sm text-gray-500">Nessun incontro in questo calendario.</p>
          )}
          {calendarioDetail.incontri?.map((inc) => {
            const esitiRiga = esitiPerIncontro(inc, pareggioOk);
            return (
            <div key={inc.id} className="rounded-lg border border-gray-700 bg-gray-800 p-3">
              <div className="mb-2 text-center">
                <NomeSquadraClick
                  id={inc.squadra_casa}
                  nome={inc.squadra_casa_nome}
                  onClick={apriStoricoSquadra}
                />
                <span className="mx-2 font-bold text-gray-500">vs</span>
                <NomeSquadraClick
                  id={inc.squadra_trasferta}
                  nome={inc.squadra_trasferta_nome}
                  onClick={apriStoricoSquadra}
                />
              </div>
              {inc.esito && (
                <div className="mb-2 text-center text-sm text-emerald-400">
                  Risultato: {inc.esito} ({inc.risultato_formattato || formattaRisultato(inc.tipo_risultato || tipoSport, inc.gol_casa, inc.gol_trasferta)})
                </div>
              )}
              <div className={`grid justify-center gap-2 ${esitiRiga.length === 2 ? 'grid-cols-2 max-w-xs mx-auto' : 'grid-cols-3'}`}>
                {esitiRiga.map((e) => {
                  const quota = e.id === '1' ? inc.quota_casa : e.id === 'X' ? inc.quota_pareggio : inc.quota_trasferta;
                  const active = selezioni[inc.id] === e.id;
                  return (
                    <button
                      key={e.id}
                      type="button"
                      onClick={() => toggleSelezione(inc.id, e.id, puoScommettere, messaggioChiuso)}
                      className={`min-w-[4rem] rounded px-3 py-2 text-sm font-bold transition-colors ${
                        active ? 'bg-indigo-600 text-white' : puoScommettere ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-800 text-gray-500'
                      }`}
                    >
                      {e.label}
                      <div className="text-[10px] font-normal opacity-80">{quota}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          );})}
        </div>

        {puoScommettere && (
          <div className="border-t border-gray-700 bg-gray-800 p-4 space-y-2">
            <div className="flex gap-2">
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={importo}
                onChange={(e) => setImporto(e.target.value)}
                className="flex-1 rounded border border-gray-600 bg-gray-900 px-3 py-2 text-sm"
                placeholder="Importo CR"
              />
              <input
                type="text"
                maxLength={5}
                value={codiceInput}
                onChange={(e) => setCodiceInput(e.target.value.toUpperCase())}
                className="w-24 rounded border border-gray-600 bg-gray-900 px-2 py-2 text-sm uppercase"
                placeholder="Codice"
              />
            </div>
            <p className="text-xs text-gray-400">
              Quota combinata stimata: {quotaPreview}x · Max senza codice: {calendarioDetail.importo_max_senza_codice} CR
            </p>
            {status && <p className="text-xs text-amber-300">{status}</p>}
            <button
              type="button"
              disabled={submitting}
              onClick={handlePuntata}
              className="w-full rounded bg-indigo-600 py-2 text-sm font-bold disabled:opacity-50"
            >
              {submitting ? 'Invio…' : 'Piazza scommessa'}
            </button>
          </div>
        )}
      </div>
    );
  }

  const scommettiOra = calendari.filter((c) => c.scommesse_aperte);
  const inArrivo = calendari.filter((c) => !c.scommesse_aperte && !c.risultati_visibili);
  const conclusi = calendari.filter((c) => c.risultati_visibili);

  const renderCalendarioCard = (cal, { variant = 'active' } = {}) => {
    const calId = String(cal.id);
    const isOpening = openingCalendarioId === calId;
    const subtitle = cal.scommesse_aperte
      ? `${cal.num_incontri} eventi · Scommesse aperte — tocca per giocare`
      : cal.risultati_visibili
        ? `${cal.num_incontri} incontri · risultati pubblicati`
        : cal.data_apertura
          ? `${cal.num_incontri} eventi · apre il ${new Date(cal.data_apertura).toLocaleString('it-IT')}`
          : `${cal.num_incontri} eventi · in attesa apertura`;
    return (
      <button
        key={calId}
        type="button"
        onClick={() => openCalendario(calId)}
        className={`w-full rounded-lg border p-3 text-left transition-colors ${
          variant === 'done'
            ? 'border-gray-700 bg-gray-800/60 hover:border-indigo-500'
            : 'border-indigo-700/40 bg-gray-800 hover:border-indigo-400 hover:bg-gray-800/90'
        } ${isOpening ? 'opacity-80' : ''}`}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="font-bold text-gray-100">{cal.titolo || cal.sport_nome}</div>
          {isOpening ? <Loader2 className="animate-spin shrink-0 text-indigo-400" size={16} /> : null}
        </div>
        <div className="text-xs text-gray-400">{subtitle}</div>
        {cal.data_risoluzione && (
          <div className="mt-1 text-[11px] text-gray-500">
            Risultati: {new Date(cal.data_risoluzione).toLocaleString('it-IT')}
          </div>
        )}
      </button>
    );
  };

  return (
    <div className="flex h-full flex-col bg-gray-900 text-gray-100">
      <SquadraStoricoModal
        squadra={squadraModal}
        storico={squadraStorico}
        loading={storicoLoading}
        onClose={() => { setSquadraModal(null); setSquadraStorico(null); }}
        onOpenAvversario={apriStoricoSquadra}
      />
      <div className="border-b border-gray-700 px-4 py-3">
        <div className="flex items-center gap-2">
          <Trophy className="text-amber-400" size={22} />
          <h2 className="text-lg font-bold">Scommesse</h2>
        </div>
        <p className="mt-1 text-xs text-gray-400">
          Crediti: {char?.crediti ?? '—'} CR
          {listRefreshing ? ' · aggiornamento…' : ''}
          {config?.importo_max_senza_codice_default && (
            <> · Max senza codice: {config.importo_max_senza_codice_default} CR</>
          )}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {status && (
          <div className="rounded border border-amber-600/50 bg-amber-950/40 px-3 py-2 text-sm text-amber-200">
            {status}
          </div>
        )}

        {isAllibratore && (
          <section className="rounded-lg border border-amber-700/50 bg-amber-950/30 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm font-bold text-amber-200">
                <Key size={16} /> Allibratore (ALL {valoreAll})
                {config?.commissione_allibratore_pct && (
                  <span className="font-normal text-amber-100/70">
                    · comm. {Math.round(Number(config.commissione_allibratore_pct) * 100)}%
                  </span>
                )}
              </span>
              <button type="button" disabled={submitting} onClick={handleGeneraCodice} className="rounded bg-amber-700 px-3 py-1 text-xs font-bold">
                Genera codice
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {codici.filter((c) => !c.usato).slice(0, 8).map((c) => (
                <span key={c.id} className="rounded bg-gray-900 px-2 py-1 font-mono text-sm text-amber-100">{c.codice}</span>
              ))}
              {!codici.filter((c) => !c.usato).length && <span className="text-xs text-gray-500">Nessun codice disponibile</span>}
            </div>
          </section>
        )}

        <section>
          <h3 className="mb-2 text-sm font-bold uppercase text-emerald-400">Scommetti ora</h3>
          {scommettiOra.length === 0 && (
            <p className="text-sm text-gray-500">Nessun calendario aperto alle puntate. Controlla &quot;In arrivo&quot; sotto.</p>
          )}
          <div className="space-y-2">
            {scommettiOra.map((cal) => renderCalendarioCard(cal))}
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-sm font-bold uppercase text-gray-400">In arrivo</h3>
          {inArrivo.length === 0 && <p className="text-sm text-gray-500">Nessun calendario in programma.</p>}
          <div className="space-y-2">
            {inArrivo.map((cal) => renderCalendarioCard(cal))}
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-sm font-bold uppercase text-gray-400">Risultati recenti</h3>
          {conclusi.length === 0 && <p className="text-sm text-gray-500">Nessun risultato recente.</p>}
          <div className="space-y-2">
            {conclusi.map((cal) => renderCalendarioCard(cal, { variant: 'done' }))}
          </div>
        </section>

        <section>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase text-gray-400"><Ticket size={14} /> Le mie scommesse</h3>
          {puntate.length === 0 && <p className="text-sm text-gray-500">Nessuna puntata.</p>}
          <div className="space-y-2">
            {puntate.map((p) => (
              <button
                key={p.id}
                type="button"
                disabled={!p.calendario}
                onClick={() => p.calendario && openCalendario(String(p.calendario))}
                className="w-full rounded border border-gray-700 bg-gray-800 p-3 text-left text-sm hover:border-indigo-500 disabled:opacity-60"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold">{p.calendario_titolo}</span>
                  {p.stato === 'WON' && <CheckCircle2 className="text-emerald-400" size={18} />}
                  {p.stato === 'LOST' && <XCircle className="text-red-400" size={18} />}
                  {p.stato === 'PENDING' && <Clock className="text-amber-400" size={18} />}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {p.importo} CR · quota {p.quota_totale} · {p.tipo}
                  {p.vincita != null && p.stato === 'WON' ? ` · vincita ${p.vincita} CR` : ''}
                  {p.calendario ? ' · Tocca per dettagli' : ''}
                </div>
              </button>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default ScommesseTab;
