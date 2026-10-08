import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Dialog } from '@headlessui/react';
import { X, Store, Loader2, Search } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { RichTextViewer } from './RichTextDisplay';
import NegozioVoceRow from './negozio/NegozioVoceRow';
import NegozioVoceDetailModal from './negozio/NegozioVoceDetailModal';
import {
  fetchNegozioMercanteListino,
  acquistaNegozioMercante,
  vendiOggettoNegozioMercante,
  restituisciPrestitoNegozioMercante,
  previewVenditaNegozioMercante,
  searchPersonaggi,
  getBodySlots,
} from '../api';

const BODY_SLOTS = getBodySlots();

const fmtCr = (n) => {
  const v = Number(n);
  if (Number.isNaN(v)) return '0.00';
  return v.toFixed(2);
};

const NegozioMercanteModal = ({ negozioId, listinoIniziale, onClose, onLogout }) => {
  const { selectedCharacterId, selectedCharacterData: char, refreshCharacterData } = useCharacter();
  const [listino, setListino] = useState(listinoIniziale || null);
  const [loading, setLoading] = useState(!listinoIniziale);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('acquista');
  const [sellSearch, setSellSearch] = useState('');
  const [sellPreview, setSellPreview] = useState(null);
  const [sellItemId, setSellItemId] = useState(null);
  const [checkout, setCheckout] = useState(null);
  const [voceAperta, setVoceAperta] = useState(null);
  const [destQuery, setDestQuery] = useState('');
  const [destResults, setDestResults] = useState([]);
  const [destLoading, setDestLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!negozioId || !selectedCharacterId) return;
    setLoading(true);
    try {
      const data = await fetchNegozioMercanteListino(negozioId, selectedCharacterId, onLogout);
      setListino(data);
      setError('');
    } catch (e) {
      setError(e.message || 'Errore caricamento negozio.');
    } finally {
      setLoading(false);
    }
  }, [negozioId, selectedCharacterId, onLogout]);

  useEffect(() => {
    if (!listinoIniziale) reload();
  }, [listinoIniziale, reload]);

  const oggettiVendibili = useMemo(() => {
    const items = char?.oggetti || [];
    return items.filter((o) => !o.ospitato_su);
  }, [char?.oggetti]);

  const oggettiFiltrati = useMemo(() => {
    const q = sellSearch.trim().toLowerCase();
    if (!q) return oggettiVendibili;
    return oggettiVendibili.filter(
      (o) =>
        (o.nome || '').toLowerCase().includes(q) ||
        String(o.id).toLowerCase().includes(q),
    );
  }, [oggettiVendibili, sellSearch]);

  const duale = !!(listino?.economia?.modulo_attivo || char?.economia?.modulo_attivo);
  const creditiCorrente = Number(
    listino?.economia?.crediti_corrente ?? char?.crediti_corrente ?? char?.crediti ?? 0,
  );
  const creditiDeposito = Number(
    listino?.economia?.crediti_deposito ?? char?.crediti_deposito ?? char?.riserva ?? 0,
  );

  useEffect(() => {
    if (!sellItemId || !negozioId || !selectedCharacterId) {
      setSellPreview(null);
      return;
    }
    let cancelled = false;
    previewVenditaNegozioMercante(negozioId, selectedCharacterId, sellItemId, onLogout)
      .then((data) => {
        if (!cancelled) setSellPreview(data);
      })
      .catch((e) => {
        if (!cancelled) setSellPreview({ error: e.message || 'Anteprima non disponibile.' });
      });
    return () => {
      cancelled = true;
    };
  }, [sellItemId, negozioId, selectedCharacterId, onLogout]);

  useEffect(() => {
    if (!checkout?.voce?.richiede_montaggio || !selectedCharacterId) {
      setDestResults([]);
      return undefined;
    }
    const q = destQuery.trim();
    if (q && q.length < 2) {
      setDestResults([]);
      return undefined;
    }
    let cancelled = false;
    setDestLoading(true);
    searchPersonaggi(q, selectedCharacterId, checkout.voce.infusione_id || null)
      .then((rows) => {
        if (!cancelled) setDestResults(Array.isArray(rows) ? rows : []);
      })
      .catch(() => {
        if (!cancelled) setDestResults([]);
      })
      .finally(() => {
        if (!cancelled) setDestLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [checkout, destQuery, selectedCharacterId]);

  const slotOptionsForCheckout = useMemo(() => {
    if (!checkout) return [];
    const permessi = checkout.voce?.slot_corpo_permessi;
    const allowed = Array.isArray(permessi) && permessi.length ? permessi : BODY_SLOTS.map((s) => s.code);
    const isSelf = String(checkout.destinatarioId) === String(selectedCharacterId);
    const occupati = isSelf
      ? new Set()
      : new Set(checkout.destinatario?.slots_occupati || []);
    const liberiSelf = new Set((checkout.voce?.slot_disponibili || []).map((s) => s.code));
    return BODY_SLOTS.filter((s) => allowed.includes(s.code)).map((s) => ({
      ...s,
      libero: isSelf ? liberiSelf.has(s.code) : !occupati.has(s.code),
    }));
  }, [checkout, selectedCharacterId]);

  const openCheckout = (voce) => {
    const depositoOk = duale && voce.deposito_ammesso;
    setCheckout({
      voce,
      conto: 'CORRENTE',
      destinatarioId: selectedCharacterId,
      destinatario: { id: selectedCharacterId, nome: char?.nome || 'Tu', is_mine: true },
      slot: (voce.slot_disponibili || []).length === 1 ? voce.slot_disponibili[0].code : '',
      depositoOk,
    });
    setDestQuery('');
  };

  const handleBuy = (voce) => {
    if (!voce.acquistabile || busy) return;
    if (duale || voce.richiede_montaggio) {
      openCheckout(voce);
      return;
    }
    const label = voce.nome || 'Articolo';
    const isPrestito = !!listino?.negozio_prestiti;
    const prezzo = Number(voce.prezzo_crediti) || 0;
    const azione = isPrestito
      ? prezzo > 0
        ? `Prendere in prestito "${label}" (noleggio ${prezzo} CR)? Va restituito a fine evento.`
        : `Prendere in prestito "${label}" (gratuito)? Va restituito a fine evento.`
      : `Acquistare "${label}" per ${prezzo} CR?`;
    if (!window.confirm(azione)) return;
    submitPurchase(voce, { conto: 'CORRENTE' });
  };

  const submitPurchase = async (voce, extras) => {
    setBusy(true);
    try {
      const body = {
        char_id: selectedCharacterId,
        voce_id: voce.tipo === 'voce' ? voce.id : undefined,
        stock_id: voce.tipo === 'stock' ? voce.id : undefined,
        bundle_id: voce.tipo === 'bundle' ? voce.id : undefined,
        conto: extras.conto || 'CORRENTE',
      };
      if (voce.richiede_montaggio) {
        body.slot_corpo = extras.slot;
        if (extras.destinatarioId && String(extras.destinatarioId) !== String(selectedCharacterId)) {
          body.destinatario_id = extras.destinatarioId;
        }
      }
      const res = await acquistaNegozioMercante(negozioId, body, onLogout);
      setCheckout(null);
      await refreshCharacterData();
      await reload();
      if (res?.prestito) {
        alert(
          Number(res.prezzo) > 0
            ? `Prestito effettuato (noleggio ${res.prezzo_pagato || res.prezzo} CR). Restituisci a fine evento.`
            : 'Prestito effettuato (gratuito). Restituisci a fine evento.',
        );
      }
    } catch (e) {
      alert(
        e.message ||
          (listino?.negozio_prestiti
            ? 'Prestito fallito. Nessun credito è stato addebitato.'
            : 'Acquisto fallito. Nessun credito è stato addebitato.'),
      );
    } finally {
      setBusy(false);
    }
  };

  const confirmCheckout = () => {
    if (!checkout) return;
    const { voce, conto, destinatarioId, slot } = checkout;
    if (voce.richiede_montaggio && !slot) {
      alert('Scegli lo slot corpo su cui montare innesto o mutazione.');
      return;
    }
    const opt = slotOptionsForCheckout.find((s) => s.code === slot);
    if (voce.richiede_montaggio && opt && !opt.libero) {
      alert('Quello slot è occupato: l’acquisto verrebbe annullato. Scegline un altro o un altro destinatario.');
      return;
    }
    submitPurchase(voce, { conto, slot, destinatarioId });
  };

  const handleSellConfirm = async () => {
    if (!sellItemId || busy) return;
    const nome = oggettiVendibili.find((o) => String(o.id) === String(sellItemId))?.nome || 'oggetto';
    const range =
      sellPreview && !sellPreview.error
        ? `${sellPreview.offerta_min}–${sellPreview.offerta_max} CR`
        : 'importo variabile';
    if (!window.confirm(`Vendere «${nome}»? Offerta stimata: ${range}.`)) return;
    setBusy(true);
    try {
      const res = await vendiOggettoNegozioMercante(
        negozioId,
        selectedCharacterId,
        sellItemId,
        onLogout,
      );
      alert(`Vendita completata: ${res.offerta_crediti} CR ricevuti sul deposito.`);
      setSellItemId(null);
      setSellPreview(null);
      await refreshCharacterData();
      await reload();
    } catch (e) {
      alert(e.message || 'Vendita fallita.');
    } finally {
      setBusy(false);
    }
  };

  const handleRestituisci = async (prestito) => {
    if (busy || !prestito) return;
    const nome = prestito.oggetto_nome || 'articolo';
    if (!window.confirm(`Restituire «${nome}» al negozio di prestiti?`)) return;
    setBusy(true);
    try {
      await restituisciPrestitoNegozioMercante(
        negozioId,
        selectedCharacterId,
        { prestitoId: prestito.id, oggettoId: prestito.oggetto_id },
        onLogout,
      );
      await refreshCharacterData();
      await reload();
    } catch (e) {
      alert(e.message || 'Restituzione fallita.');
    } finally {
      setBusy(false);
    }
  };

  const prezzoVoce = (v) => {
    const isPrestito = !!listino?.negozio_prestiti;
    if (isPrestito) {
      const n = Number(v.prezzo_crediti) || 0;
      return n > 0 ? `Noleggio ${n} CR` : 'Prestito gratis';
    }
    if (duale && v.deposito_ammesso && v.prezzo_deposito) {
      return `${fmtCr(v.prezzo_corrente)} / ${fmtCr(v.prezzo_deposito)} dep`;
    }
    return `${v.prezzo_crediti} CR`;
  };

  const handleBuyDaScheda = (voce) => {
    setVoceAperta(null);
    handleBuy(voce);
  };

  const aperto = listino?.aperto !== false;
  const isPrestitoNegozio = !!listino?.negozio_prestiti;
  const testoImmersivo =
    (listino?.descrizione_immersiva || listino?.descrizione || '').trim();
  const prestitiMiei = listino?.prestiti_attivi || [];

  // Dopo un reload del listino la scheda aperta deve mostrare i dati freschi.
  const voceApertaAggiornata = useMemo(() => {
    if (!voceAperta) return null;
    const key = `${voceAperta.tipo}-${voceAperta.id}`;
    return (listino?.voci || []).find((v) => `${v.tipo}-${v.id}` === key) || voceAperta;
  }, [voceAperta, listino?.voci]);

  return (
    <Dialog
      open
      // Il fondale, Escape e il pointer di apertura non chiudono: solo la X.
      onClose={() => {}}
      className="relative z-50"
    >
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-end sm:items-center justify-center p-0 sm:p-4">
        <Dialog.Panel className="w-full sm:max-w-2xl h-[96dvh] sm:h-auto sm:max-h-[90vh] flex flex-col bg-gray-900 border border-amber-700/40 rounded-t-xl sm:rounded-xl shadow-2xl min-w-0">
          <div className="flex items-start justify-between gap-2 p-3 sm:p-4 border-b border-gray-700 shrink-0">
            <div className="min-w-0">
              <Dialog.Title className="text-base sm:text-lg font-bold text-amber-400 flex items-center gap-2 min-w-0">
                <Store size={20} className="shrink-0" />
                <span className="break-words">{listino?.nome || 'Negozio'}</span>
              </Dialog.Title>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-xs">
                {duale ? (
                  <span className="font-mono">
                    <span className="text-emerald-300">{fmtCr(creditiCorrente)} corr.</span>
                    <span className="text-gray-500"> · </span>
                    <span className="text-amber-300">{fmtCr(creditiDeposito)} dep.</span>
                  </span>
                ) : (
                  <span className="text-yellow-400 font-mono">{char?.crediti ?? 0} CR</span>
                )}
                <span className="text-gray-600">|</span>
                <span className="text-gray-400">Cassa: {listino?.saldo_crediti ?? '—'} CR</span>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Chiudi negozio"
              className="shrink-0 min-h-11 min-w-11 flex items-center justify-center text-gray-400 hover:text-white"
            >
              <X size={22} />
            </button>
          </div>

          {aperto && (
            <div className="flex border-b border-gray-700 text-sm shrink-0">
              <button
                type="button"
                className={`flex-1 min-h-11 ${tab === 'acquista' ? 'text-amber-400 border-b-2 border-amber-500' : 'text-gray-400'}`}
                onClick={() => setTab('acquista')}
              >
                {isPrestitoNegozio ? 'Prendi in prestito' : 'Acquista'}
              </button>
              {isPrestitoNegozio ? (
                <button
                  type="button"
                  className={`flex-1 min-h-11 ${tab === 'restituisci' ? 'text-sky-400 border-b-2 border-sky-500' : 'text-gray-400'}`}
                  onClick={() => setTab('restituisci')}
                >
                  Restituisci
                  {prestitiMiei.length > 0 ? ` (${prestitiMiei.length})` : ''}
                </button>
              ) : (
                <button
                  type="button"
                  className={`flex-1 min-h-11 ${tab === 'vendi' ? 'text-amber-400 border-b-2 border-amber-500' : 'text-gray-400'}`}
                  onClick={() => setTab('vendi')}
                >
                  Vendi
                </button>
              )}
            </div>
          )}

          <div className="p-3 sm:p-4 overflow-y-auto flex-1 space-y-4 min-w-0">
            {isPrestitoNegozio && (
              <p className="text-xs text-sky-300/90 bg-sky-950/40 border border-sky-800/60 rounded-lg px-3 py-2">
                Negozio di prestiti · max {listino?.limite_prestiti_per_personaggio || 1} oggetto
                {(listino?.limite_prestiti_per_personaggio || 1) === 1 ? '' : 'i'} per te
                {typeof listino?.prestiti_attivi_personaggio === 'number'
                  ? ` · in prestito: ${listino.prestiti_attivi_personaggio}`
                  : ''}
                . Restituzione a fine evento.
              </p>
            )}
            {testoImmersivo && (
              <div className="rounded-xl border border-amber-800/60 bg-amber-950/30 p-4 shadow-inner">
                <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-2">
                  Il mercante
                </p>
                <div className="text-amber-50/95 text-sm leading-relaxed prose prose-invert prose-amber max-w-none">
                  <RichTextViewer content={testoImmersivo} />
                </div>
              </div>
            )}
            {!aperto && (
              <p className="text-amber-300 bg-amber-950/40 border border-amber-800 rounded-lg p-3 text-sm">
                {listino?.messaggio_accesso || 'Negozio chiuso.'}
              </p>
            )}
            {error && <p className="text-red-400 text-sm">{error}</p>}
            {loading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="animate-spin text-amber-500" size={32} />
              </div>
            ) : tab === 'acquista' || !aperto ? (
              <div className="grid gap-2">
                {(listino?.voci || []).map((v) => (
                  <NegozioVoceRow
                    key={`${v.tipo}-${v.id}`}
                    voce={v}
                    prezzoLabel={prezzoVoce(v)}
                    onOpen={() => setVoceAperta(v)}
                    onBuy={() => handleBuy(v)}
                    buyDisabled={!aperto || !v.acquistabile || busy}
                    buyTone={
                      v.tipo === 'bundle' ? 'violet' : isPrestitoNegozio ? 'sky' : 'amber'
                    }
                  />
                ))}
                {aperto && (listino?.voci || []).length === 0 && (
                  <p className="text-gray-500 text-center py-6">
                    {isPrestitoNegozio
                      ? 'Nessun articolo disponibile in prestito.'
                      : 'Nessun articolo in vendita.'}
                  </p>
                )}
              </div>
            ) : tab === 'restituisci' ? (
              <div className="space-y-2">
                {prestitiMiei.length === 0 ? (
                  <p className="text-gray-500 text-center py-6">
                    Non hai oggetti in prestito da questo negozio.
                  </p>
                ) : (
                  prestitiMiei.map((p) => (
                    <div
                      key={p.id}
                      className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 p-3 rounded-lg border border-sky-800/50 bg-sky-950/30 min-w-0"
                    >
                      <div className="min-w-0">
                        <div className="font-semibold text-white break-words">{p.oggetto_nome}</div>
                        <div className="text-xs text-gray-400">
                          {p.costo_noleggio
                            ? `Noleggio pagato: ${p.costo_noleggio} CR`
                            : 'Prestito gratuito'}
                        </div>
                      </div>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleRestituisci(p)}
                        className="w-full sm:w-auto shrink-0 min-h-11 px-3 rounded bg-sky-700 hover:bg-sky-600 text-white text-sm font-bold disabled:opacity-40"
                      >
                        Restituisci
                      </button>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 text-gray-500" size={16} />
                  <input
                    className="w-full pl-8 pr-2 min-h-11 bg-gray-800 border border-gray-600 rounded text-sm"
                    placeholder="Cerca nel tuo inventario…"
                    value={sellSearch}
                    onChange={(e) => setSellSearch(e.target.value)}
                  />
                </div>
                <ul className="max-h-48 overflow-y-auto space-y-1">
                  {oggettiFiltrati.map((o) => (
                    <li key={o.id}>
                      <button
                        type="button"
                        onClick={() => setSellItemId(o.id)}
                        className={`w-full text-left px-3 min-h-11 rounded text-sm ${
                          String(sellItemId) === String(o.id)
                            ? 'bg-amber-900/60 border border-amber-600'
                            : 'bg-gray-800 hover:bg-gray-700 border border-transparent'
                        }`}
                      >
                        <span className="font-medium text-white">{o.nome}</span>
                        {o.livello != null && (
                          <span className="text-gray-500 ml-2">Lv.{o.livello}</span>
                        )}
                      </button>
                    </li>
                  ))}
                  {oggettiFiltrati.length === 0 && (
                    <li className="text-gray-500 text-sm text-center py-4">
                      Nessun oggetto vendibile (montati esclusi).
                    </li>
                  )}
                </ul>
                {sellItemId && sellPreview && (
                  <div className="text-sm border border-gray-600 rounded-lg p-3 bg-gray-800/80">
                    {sellPreview.error ? (
                      <p className="text-red-400">{sellPreview.error}</p>
                    ) : (
                      <>
                        <p className="text-gray-300">
                          Offerta stimata:{' '}
                          <span className="text-amber-300 font-mono">
                            {sellPreview.offerta_min}–{sellPreview.offerta_max} CR
                          </span>
                          <span className="text-gray-500"> (accreditati sul deposito)</span>
                        </p>
                        {!sellPreview.cassa_sufficiente && (
                          <p className="text-amber-300 text-xs mt-1">
                            La cassa del mercante potrebbe non coprire il massimo (
                            {sellPreview.saldo_negozio} CR in cassa).
                          </p>
                        )}
                      </>
                    )}
                  </div>
                )}
                <button
                  type="button"
                  disabled={!sellItemId || busy || sellPreview?.error}
                  onClick={handleSellConfirm}
                  className="w-full min-h-11 rounded-lg bg-emerald-800 hover:bg-emerald-700 disabled:opacity-40 font-semibold text-sm"
                >
                  Conferma vendita
                </button>
              </div>
            )}
          </div>

          {aperto && (
            <div className="p-3 sm:p-4 border-t border-gray-700 shrink-0 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
              <button
                type="button"
                onClick={reload}
                disabled={busy}
                className="w-full min-h-11 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm"
              >
                Aggiorna listino
              </button>
            </div>
          )}
        </Dialog.Panel>
      </div>

      {voceApertaAggiornata && (
        <NegozioVoceDetailModal
          voce={voceApertaAggiornata}
          prezzoLabel={prezzoVoce(voceApertaAggiornata)}
          onClose={() => setVoceAperta(null)}
          onAction={
            aperto && voceApertaAggiornata.acquistabile
              ? () => handleBuyDaScheda(voceApertaAggiornata)
              : undefined
          }
          actionLabel={isPrestitoNegozio ? 'Prendi in prestito' : 'Acquista'}
          actionDisabled={busy}
          actionTone={
            voceApertaAggiornata.tipo === 'bundle'
              ? 'violet'
              : isPrestitoNegozio
                ? 'sky'
                : 'amber'
          }
        />
      )}

      {checkout && (
        <Dialog open onClose={() => !busy && setCheckout(null)} className="relative z-[60]">
          <div className="fixed inset-0 bg-black/80" />
          <div className="fixed inset-0 flex items-end sm:items-center justify-center p-0 sm:p-4 overflow-y-auto">
            <Dialog.Panel className="bg-gray-900 border border-gray-600 rounded-t-xl sm:rounded-xl p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:max-w-md w-full max-h-[92dvh] overflow-y-auto space-y-3 min-w-0">
              <Dialog.Title className="font-bold text-white">
                Acquisto: {checkout.voce.nome}
              </Dialog.Title>

              {duale && (
                <div className="space-y-2">
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Paga con</p>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      className={`px-3 py-2 rounded text-sm border ${
                        checkout.conto === 'CORRENTE'
                          ? 'border-emerald-500 bg-emerald-950/60 text-emerald-200'
                          : 'border-gray-700 text-gray-300'
                      }`}
                      onClick={() => setCheckout({ ...checkout, conto: 'CORRENTE' })}
                    >
                      Corrente
                      <div className="font-mono text-xs">{fmtCr(checkout.voce.prezzo_corrente)} CR</div>
                      <div className="text-[10px] text-gray-500">saldo {fmtCr(creditiCorrente)}</div>
                    </button>
                    <button
                      type="button"
                      disabled={!checkout.voce.deposito_ammesso}
                      className={`px-3 py-2 rounded text-sm border ${
                        checkout.conto === 'DEPOSITO'
                          ? 'border-amber-500 bg-amber-950/60 text-amber-200'
                          : 'border-gray-700 text-gray-300'
                      } disabled:opacity-40`}
                      onClick={() => setCheckout({ ...checkout, conto: 'DEPOSITO' })}
                    >
                      Deposito
                      <div className="font-mono text-xs">
                        {checkout.voce.prezzo_deposito
                          ? `${fmtCr(checkout.voce.prezzo_deposito)} CR`
                          : 'non ammesso'}
                      </div>
                      <div className="text-[10px] text-gray-500">saldo {fmtCr(creditiDeposito)}</div>
                    </button>
                  </div>
                </div>
              )}

              {checkout.voce.richiede_montaggio && (
                <div className="space-y-2">
                  <p className="text-xs text-gray-400 uppercase tracking-wide">Montaggio in locazione</p>
                  <p className="text-xs text-gray-500">
                    Se il montaggio non riesce (slot occupato o destinatario incompatibile),
                    l&apos;acquisto viene annullato e non paghi nulla.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className={`px-3 py-1.5 rounded text-sm ${
                        String(checkout.destinatarioId) === String(selectedCharacterId)
                          ? 'bg-fuchsia-800 text-white'
                          : 'bg-gray-800 text-gray-300'
                      }`}
                      onClick={() =>
                        setCheckout({
                          ...checkout,
                          destinatarioId: selectedCharacterId,
                          destinatario: {
                            id: selectedCharacterId,
                            nome: char?.nome || 'Tu',
                            is_mine: true,
                          },
                          slot: (checkout.voce.slot_disponibili || [])[0]?.code || '',
                        })
                      }
                    >
                      Su di me
                    </button>
                  </div>
                  <input
                    className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                    placeholder="Cerca un altro personaggio…"
                    value={destQuery}
                    onChange={(e) => setDestQuery(e.target.value)}
                  />
                  {destLoading && <p className="text-xs text-gray-500">Ricerca…</p>}
                  {destResults.length > 0 && (
                    <ul className="max-h-28 overflow-y-auto text-sm space-y-1">
                      {destResults.map((p) => (
                        <li key={p.id}>
                          <button
                            type="button"
                            className={`w-full text-left px-2 py-1 rounded ${
                              String(checkout.destinatarioId) === String(p.id)
                                ? 'bg-fuchsia-900/70'
                                : 'hover:bg-gray-800'
                            }`}
                            onClick={() =>
                              setCheckout({
                                ...checkout,
                                destinatarioId: p.id,
                                destinatario: p,
                                slot: '',
                              })
                            }
                          >
                            {p.nome}
                            {p.is_mine ? ' (tuo PG)' : ''}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="text-xs text-gray-400">
                    Destinatario: {checkout.destinatario?.nome || '—'}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {slotOptionsForCheckout.map((s) => (
                      <button
                        key={s.code}
                        type="button"
                        disabled={!s.libero}
                        onClick={() => setCheckout({ ...checkout, slot: s.code })}
                        className={`px-3 py-2 rounded text-sm ${
                          checkout.slot === s.code
                            ? 'bg-amber-700 text-white'
                            : s.libero
                              ? 'bg-gray-800 text-gray-200'
                              : 'bg-gray-900 text-gray-600 line-through'
                        }`}
                      >
                        {s.name || s.label || s.code}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  className="flex-1 py-2 rounded bg-gray-700 text-sm"
                  disabled={busy}
                  onClick={() => setCheckout(null)}
                >
                  Annulla
                </button>
                <button
                  type="button"
                  className="flex-1 py-2 rounded bg-amber-700 font-bold text-sm disabled:opacity-40"
                  disabled={busy}
                  onClick={confirmCheckout}
                >
                  {busy ? '…' : 'Conferma acquisto'}
                </button>
              </div>
            </Dialog.Panel>
          </div>
        </Dialog>
      )}
    </Dialog>
  );
};

export default NegozioMercanteModal;
