import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Dialog } from '@headlessui/react';
import { X, Store, Loader2, Search } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { RichTextViewer } from './RichTextDisplay';
import {
  fetchNegozioMercanteListino,
  acquistaNegozioMercante,
  vendiOggettoNegozioMercante,
  previewVenditaNegozioMercante,
} from '../api';

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
  const [slotPick, setSlotPick] = useState(null);

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

  const completePurchase = async (body) => {
    const res = await acquistaNegozioMercante(negozioId, body, onLogout);
    if (res.richiede_slot_corpo && res.slot_disponibili?.length) {
      setSlotPick({ body, slots: res.slot_disponibili });
      return;
    }
    await refreshCharacterData();
    await reload();
  };

  const handleBuy = async (voce) => {
    if (!voce.acquistabile || busy) return;
    const label = voce.nome || 'Articolo';
    if (!window.confirm(`Acquistare "${label}" per ${voce.prezzo_crediti} CR?`)) return;
    setBusy(true);
    try {
      const body = {
        char_id: selectedCharacterId,
        voce_id: voce.tipo === 'voce' ? voce.id : undefined,
        stock_id: voce.tipo === 'stock' ? voce.id : undefined,
      };
      await completePurchase(body);
    } catch (e) {
      alert(e.message || 'Acquisto fallito.');
    } finally {
      setBusy(false);
    }
  };

  const confirmSlot = async (code) => {
    if (!slotPick) return;
    setBusy(true);
    try {
      await acquistaNegozioMercante(
        negozioId,
        { ...slotPick.body, slot_corpo: code },
        onLogout,
      );
      setSlotPick(null);
      await refreshCharacterData();
      await reload();
    } catch (e) {
      alert(e.message || 'Acquisto fallito.');
    } finally {
      setBusy(false);
    }
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
      alert(`Vendita completata: ${res.offerta_crediti} CR ricevuti.`);
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

  const aperto = listino?.aperto !== false;
  const testoImmersivo =
    (listino?.descrizione_immersiva || listino?.descrizione || '').trim();

  return (
    <Dialog open onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-2xl max-h-[90vh] flex flex-col bg-gray-900 border border-amber-700/40 rounded-xl shadow-2xl">
          <div className="flex justify-between items-center p-4 border-b border-gray-700">
            <Dialog.Title className="text-lg font-bold text-amber-400 flex items-center gap-2">
              <Store size={22} />
              {listino?.nome || 'Negozio'}
            </Dialog.Title>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-yellow-400 font-mono">{char?.crediti ?? 0} CR</span>
              <span className="text-gray-500">|</span>
              <span className="text-gray-400">Cassa: {listino?.saldo_crediti ?? '—'} CR</span>
              <button type="button" onClick={onClose} className="text-gray-400 hover:text-white">
                <X size={22} />
              </button>
            </div>
          </div>

          {aperto && (
            <div className="flex border-b border-gray-700 text-sm">
              <button
                type="button"
                className={`flex-1 py-2 ${tab === 'acquista' ? 'text-amber-400 border-b-2 border-amber-500' : 'text-gray-400'}`}
                onClick={() => setTab('acquista')}
              >
                Acquista
              </button>
              <button
                type="button"
                className={`flex-1 py-2 ${tab === 'vendi' ? 'text-amber-400 border-b-2 border-amber-500' : 'text-gray-400'}`}
                onClick={() => setTab('vendi')}
              >
                Vendi
              </button>
            </div>
          )}

          <div className="p-4 overflow-y-auto flex-1 space-y-4">
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
                  <div
                    key={`${v.tipo}-${v.id}`}
                    className="flex justify-between items-start gap-2 p-3 rounded-lg border border-gray-700 bg-gray-800/80"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-white truncate">{v.nome}</div>
                      {v.messaggio_usabilita && (
                        <div
                          className={`text-xs mt-1 ${v.acquistabile ? 'text-gray-400' : 'text-amber-300'}`}
                        >
                          {v.messaggio_usabilita}
                        </div>
                      )}
                      {v.quantita_residua != null && (
                        <div className="text-xs text-gray-500">Disponibili: {v.quantita_residua}</div>
                      )}
                      {v.usato && <div className="text-xs text-emerald-500">Usato</div>}
                    </div>
                    <button
                      type="button"
                      disabled={!aperto || !v.acquistabile || busy}
                      onClick={() => handleBuy(v)}
                      className="shrink-0 px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 disabled:opacity-40 text-white text-sm font-bold"
                    >
                      {v.prezzo_crediti} CR
                    </button>
                  </div>
                ))}
                {aperto && (listino?.voci || []).length === 0 && (
                  <p className="text-gray-500 text-center py-6">Nessun articolo in vendita.</p>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 text-gray-500" size={16} />
                  <input
                    className="w-full pl-8 pr-2 py-2 bg-gray-800 border border-gray-600 rounded text-sm"
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
                        className={`w-full text-left px-3 py-2 rounded text-sm ${
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
                  className="w-full py-2 rounded-lg bg-emerald-800 hover:bg-emerald-700 disabled:opacity-40 font-semibold text-sm"
                >
                  Conferma vendita
                </button>
              </div>
            )}
          </div>

          {aperto && (
            <div className="p-4 border-t border-gray-700">
              <button
                type="button"
                onClick={reload}
                disabled={busy}
                className="w-full py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm"
              >
                Aggiorna listino
              </button>
            </div>
          )}
        </Dialog.Panel>
      </div>

      {slotPick && (
        <Dialog open onClose={() => setSlotPick(null)} className="relative z-[60]">
          <div className="fixed inset-0 bg-black/80" />
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Dialog.Panel className="bg-gray-900 border border-gray-600 rounded-xl p-4 max-w-sm w-full">
              <Dialog.Title className="font-bold text-white mb-2">Scegli slot corpo</Dialog.Title>
              <div className="flex flex-wrap gap-2">
                {slotPick.slots.map((s) => (
                  <button
                    key={s.code}
                    type="button"
                    disabled={busy}
                    onClick={() => confirmSlot(s.code)}
                    className="px-3 py-2 rounded bg-amber-800 text-sm"
                  >
                    {s.label || s.code}
                  </button>
                ))}
              </div>
            </Dialog.Panel>
          </div>
        </Dialog>
      )}
    </Dialog>
  );
};

export default NegozioMercanteModal;
