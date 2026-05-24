import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Ticket, X } from 'lucide-react';
import {
  fetchAuthenticated,
  getIscrizioniEventoEligibility,
  postIscrizioneEventoAnnulla,
  postIscrizioneEventoCattura,
  postIscrizioneEventoCreaOrdine,
} from '../api';
import { RichTextViewer } from './RichTextDisplay';

function EventSinossi({ content }) {
  const trimmed = String(content || '').trim();
  if (!trimmed) return null;
  return (
    <div className="max-w-full min-w-0 overflow-hidden rounded-lg border border-indigo-800/40 bg-indigo-950/25 px-3 py-2.5 text-sm">
      <RichTextViewer content={trimmed} />
    </div>
  );
}

function loadPayPalScript(clientId, currency, sandbox, uiFlags = {}) {
  const host = sandbox ? 'https://www.sandbox.paypal.com' : 'https://www.paypal.com';
  const disabled = ['bancontact', 'blik', 'eps', 'giropay', 'ideal', 'p24', 'sepa', 'sofort', 'venmo'];
  if (!uiFlags.showCard) disabled.push('card');
  if (!uiFlags.showMybank) disabled.push('mybank');
  const src = `${host}/sdk/js?client-id=${encodeURIComponent(clientId)}&currency=${encodeURIComponent(
    currency || 'EUR'
  )}&intent=capture&components=buttons&disable-funding=${encodeURIComponent(disabled.join(','))}`;
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-kor35-paypal-sdk="1"]');
    if (existing) {
      existing.remove();
    }
    const s = document.createElement('script');
    s.src = src;
    s.async = true;
    s.dataset.kor35PaypalSdk = '1';
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Impossibile caricare PayPal SDK'));
    document.body.appendChild(s);
  });
}

function calcImporto(ev, selectedSyncIds, modalTipo) {
  const selected = new Set(selectedSyncIds || []);
  const base = parseFloat(ev.costo_base_euro ?? ev.costo_euro ?? 0) || 0;
  const opzioni = Array.isArray(ev.opzioni) ? ev.opzioni : [];

  if (modalTipo === 'integra') {
    let tot = 0;
    for (const op of opzioni) {
      if (!op.scelta_giocatore || op.gia_acquistata || op.esaurita) continue;
      if (selected.has(op.sync_id)) tot += parseFloat(op.costo_euro) || 0;
    }
    return tot;
  }

  let tot = base;
  for (const op of opzioni) {
    if (!op.scelta_giocatore) {
      tot += parseFloat(op.costo_euro) || 0;
    } else if (op.obbligatoria && selected.has(op.sync_id)) {
      tot += parseFloat(op.costo_euro) || 0;
    } else if (!op.obbligatoria && selected.has(op.sync_id)) {
      tot += parseFloat(op.costo_euro) || 0;
    }
  }
  return tot;
}

function initialSelectedOpzioni(ev, modalTipo) {
  const opzioni = Array.isArray(ev?.opzioni) ? ev.opzioni : [];
  if (modalTipo === 'integra') return [];
  return opzioni
    .filter((op) => op.scelta_giocatore && op.obbligatoria && !op.gia_acquistata && !op.esaurita)
    .map((op) => op.sync_id);
}

/**
 * Blocco start page: iscrizione eventi con PayPal (finestra date + condizioni Arcana/password/PG).
 */
export default function EventSubscriptionStartPanel({ onLogout }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [modalEvent, setModalEvent] = useState(null);
  const [modalTipo, setModalTipo] = useState('iscrizione');
  const [modalChars, setModalChars] = useState([]);
  const [selectedPgId, setSelectedPgId] = useState('');
  const [selectedOpzioni, setSelectedOpzioni] = useState([]);
  const [paypalUiErr, setPaypalUiErr] = useState('');
  const currentOrderIdRef = useRef('');
  const paypalHostRef = useRef(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setErr('');
    try {
      const j = await getIscrizioniEventoEligibility(onLogout);
      setData(j && typeof j === 'object' ? j : null);
    } catch (e) {
      setData(null);
      setErr(e?.message || 'Errore caricamento iscrizioni');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!modalEvent) {
      setModalChars([]);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchAuthenticated(
          '/api/personaggi/api/gestione-personaggi/?mine=1',
          { method: 'GET', headers: { 'X-Campagna': 'kor35' } },
          onLogout
        );
        if (!cancelled) setModalChars(Array.isArray(list) ? list : []);
      } catch {
        if (!cancelled) setModalChars([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [modalEvent, onLogout]);

  useEffect(() => {
    if (modalTipo === 'integra' && modalEvent?.already_registered?.personaggio_id) {
      setSelectedPgId(String(modalEvent.already_registered.personaggio_id));
    }
  }, [modalEvent, modalTipo]);

  const eligibleCharacters = useMemo(() => {
    if (!Array.isArray(modalChars)) return [];
    return modalChars.filter((c) => {
      if (c.data_morte) return false;
      if (c.tipologia_giocante === false) return false;
      return true;
    });
  }, [modalChars]);

  const importoTotale = useMemo(() => {
    if (!modalEvent) return 0;
    return calcImporto(modalEvent, selectedOpzioni, modalTipo);
  }, [modalEvent, selectedOpzioni, modalTipo]);

  const openModal = (ev, tipo = 'iscrizione') => {
    setModalTipo(tipo);
    setModalEvent(ev);
    setSelectedOpzioni(initialSelectedOpzioni(ev, tipo));
    setSelectedPgId(tipo === 'integra' && ev.already_registered?.personaggio_id ? String(ev.already_registered.personaggio_id) : '');
    setPaypalUiErr('');
  };

  const closeModal = () => {
    setModalEvent(null);
    setModalTipo('iscrizione');
    setSelectedPgId('');
    setSelectedOpzioni([]);
    setPaypalUiErr('');
    currentOrderIdRef.current = '';
    if (paypalHostRef.current) {
      paypalHostRef.current.innerHTML = '';
    }
  };

  const toggleOpzione = (syncId) => {
    setSelectedOpzioni((prev) => {
      if (prev.includes(syncId)) return prev.filter((id) => id !== syncId);
      return [...prev, syncId];
    });
  };

  useEffect(() => {
    if (!modalEvent || !selectedPgId) return undefined;
    if (importoTotale <= 0) return undefined;
    const clientId = String(modalEvent.paypal_client_id || '').trim();
    if (!clientId) {
      setPaypalUiErr('PayPal non configurato (client id mancante).');
      return undefined;
    }
    const sandbox = !!modalEvent.paypal_uses_sandbox;
    let cancelled = false;
    const run = async () => {
      setPaypalUiErr('');
      currentOrderIdRef.current = '';
      if (paypalHostRef.current) paypalHostRef.current.innerHTML = '';
      try {
        const uiFlags = {
          showCard: !!modalEvent?.paypal_show_card,
          showMybank: !!modalEvent?.paypal_show_mybank,
        };
        await loadPayPalScript(clientId, 'EUR', sandbox, uiFlags);
        if (cancelled || !window.paypal) throw new Error('SDK PayPal non disponibile');
        const buttonsConfig = {
          style: { layout: 'vertical', shape: 'rect', label: 'pay' },
          createOrder: async () => {
            const res = await postIscrizioneEventoCreaOrdine(
              {
                evento_id: modalEvent.id,
                personaggio_id: parseInt(selectedPgId, 10),
                tipo: modalTipo,
                opzione_sync_ids: selectedOpzioni,
              },
              onLogout
            );
            const oid = res?.paypal_order_id;
            if (!oid) throw new Error(res?.error || res?.errori?.[0] || 'Ordine PayPal non creato');
            currentOrderIdRef.current = String(oid);
            return oid;
          },
          onApprove: async (d) => {
            try {
              await postIscrizioneEventoCattura({ paypal_order_id: d.orderID }, onLogout);
              closeModal();
              navigate('/app/iscrizione-esito?esito=ok');
            } catch {
              closeModal();
              navigate('/app/iscrizione-esito?esito=rifiutato');
            }
          },
          onCancel: async (d) => {
            const orderToCancel = String(d?.orderID || currentOrderIdRef.current || '').trim();
            if (orderToCancel) {
              try {
                await postIscrizioneEventoAnnulla({ paypal_order_id: orderToCancel }, onLogout);
              } catch {
                /* best effort */
              }
            }
            closeModal();
            navigate('/app/iscrizione-esito?esito=cancellato');
          },
          onError: () => {
            closeModal();
            navigate('/app/iscrizione-esito?esito=rifiutato');
          },
        };
        if (!uiFlags.showCard && !uiFlags.showMybank) {
          buttonsConfig.fundingSource = window.paypal.FUNDING.PAYPAL;
        }
        const buttons = window.paypal.Buttons(buttonsConfig);
        if (paypalHostRef.current) await buttons.render(paypalHostRef.current);
      } catch (e) {
        if (!cancelled) setPaypalUiErr(e?.message || 'Errore PayPal');
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [modalEvent, selectedPgId, selectedOpzioni, modalTipo, importoTotale, navigate, onLogout]);

  const events = Array.isArray(data?.events) ? data.events : [];
  if (!loading && events.length === 0 && !err) {
    return null;
  }

  const renderOpzioniModal = () => {
    const opzioni = Array.isArray(modalEvent?.opzioni) ? modalEvent.opzioni : [];
    const visibili =
      modalTipo === 'integra'
        ? opzioni.filter((op) => op.scelta_giocatore && !op.gia_acquistata && !op.esaurita)
        : opzioni;

    if (visibili.length === 0 && modalTipo === 'iscrizione') {
      const autoOnly = opzioni.filter((op) => !op.scelta_giocatore);
      if (autoOnly.length === 0) return null;
    }

    return (
      <div className="space-y-2">
        <p className="text-xs font-bold text-gray-400 uppercase">Opzioni</p>
        {visibili.length === 0 ? (
          <p className="text-sm text-gray-500">Nessuna opzione aggiuntiva selezionabile.</p>
        ) : (
          <ul className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {visibili.map((op) => {
              const checked = selectedOpzioni.includes(op.sync_id);
              const disabled =
                modalTipo === 'iscrizione' &&
                op.obbligatoria &&
                !op.gia_acquistata &&
                !op.esaurita;
              const postiLabel =
                op.posti_limite != null
                  ? `Posti: ${op.posti_disponibili ?? 0}/${op.posti_limite}`
                  : null;
              return (
                <li
                  key={op.sync_id}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    op.esaurita ? 'border-gray-700 opacity-50' : 'border-gray-600 bg-gray-800/60'
                  }`}
                >
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={checked || disabled}
                      disabled={disabled || op.esaurita || op.gia_acquistata}
                      onChange={() => toggleOpzione(op.sync_id)}
                    />
                    <span className="flex-1">
                      <span className="font-semibold text-white">{op.nome}</span>
                      {op.descrizione ? (
                        <span className="block text-gray-400 text-xs mt-0.5">{op.descrizione}</span>
                      ) : null}
                      <span className="block text-emerald-300 text-xs mt-1">
                        {parseFloat(op.costo_euro) > 0 ? `${op.costo_euro} €` : 'Gratuito'}
                        {op.obbligatoria && op.scelta_giocatore ? ' · Obbligatoria' : null}
                        {!op.scelta_giocatore ? ' · Inclusa automaticamente' : null}
                        {postiLabel ? ` · ${postiLabel}` : null}
                        {op.esaurita ? ' · Esaurita' : null}
                        {op.gia_acquistata ? ' · Già acquistata' : null}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
        {modalTipo === 'iscrizione' &&
          opzioni.some((op) => !op.scelta_giocatore) && (
            <p className="text-[11px] text-indigo-200/80">
              Le opzioni senza scelta sono incluse automaticamente nel totale.
            </p>
          )}
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-indigo-800/80 bg-indigo-950/40 p-4 md:p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Ticket className="text-indigo-300 shrink-0" size={22} />
        <h2 className="text-lg font-black text-indigo-200">Iscrizione evento</h2>
      </div>
      {loading && <p className="text-sm text-gray-400">Caricamento…</p>}
      {err && <p className="text-sm text-red-300">{err}</p>}
      {!loading &&
        events.map((ev) => {
          if (ev.cta_kind === 'registered') {
            const nomePg = ev.already_registered?.personaggio_nome || 'Personaggio';
            return (
              <div key={ev.id} className="space-y-2">
                <EventSinossi content={ev.sinossi} />
                <div className="rounded-lg border border-emerald-800/70 bg-emerald-950/30 px-4 py-3 text-emerald-100 text-center text-base font-semibold">
                  {nomePg} già iscritto all&apos;evento «{ev.titolo}»
                </div>
              </div>
            );
          }
          if (ev.cta_kind === 'integra') {
            const blocked = !ev.paypal_ready || (ev.blocking_reasons || []).length > 0;
            const reasons = [];
            if (!ev.paypal_ready) reasons.push('PayPal non configurato in amministrazione (credenziali mancanti).');
            (ev.blocking_reasons || []).forEach((r) => reasons.push(r));
            return (
              <div key={ev.id} className="space-y-2">
                <EventSinossi content={ev.sinossi} />
                <div className="rounded-lg border border-emerald-800/70 bg-emerald-950/30 px-4 py-2 text-emerald-100 text-center text-sm">
                  {ev.already_registered?.personaggio_nome} iscritto a «{ev.titolo}»
                </div>
                <button
                  type="button"
                  disabled={blocked}
                  onClick={() => {
                    if (blocked) return;
                    openModal(ev, 'integra');
                  }}
                  className={`w-full rounded-xl px-5 py-3 text-base font-black text-center transition ${
                    blocked
                      ? 'bg-red-950/70 border-2 border-red-700 text-red-100 cursor-not-allowed'
                      : 'bg-indigo-800 hover:bg-indigo-700 text-white border border-indigo-500'
                  }`}
                >
                  Aggiungi opzioni — {ev.titolo}
                </button>
                {blocked && reasons.length > 0 && (
                  <ul className="text-xs text-red-200/90 list-disc pl-5 space-y-0.5">
                    {reasons.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          }
          const blocked = ev.cta_kind === 'blocked' || !ev.paypal_ready;
          const reasons = [];
          if (!ev.paypal_ready) reasons.push('PayPal non configurato in amministrazione (credenziali mancanti).');
          (ev.blocking_reasons || []).forEach((r) => reasons.push(r));
          const label = ev.is_test ? `[TEST] Iscriviti: ${ev.titolo}` : `Iscriviti all'evento ${ev.titolo}`;
          const minCost = ev.costo_minimo_euro || ev.costo_euro;
          return (
            <div key={ev.id} className="space-y-2">
              <EventSinossi content={ev.sinossi} />
              <button
                type="button"
                disabled={blocked}
                onClick={() => {
                  if (blocked) return;
                  openModal(ev, 'iscrizione');
                }}
                className={`w-full rounded-xl px-5 py-4 text-lg md:text-xl font-black text-center transition ${
                  blocked
                    ? 'bg-red-950/70 border-2 border-red-700 text-red-100 cursor-not-allowed'
                    : 'bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg'
                }`}
              >
                {label}
              </button>
              {ev.is_test && (
                <p className="text-xs text-amber-200 text-center">Modalità test: pagamento in sandbox, visibile solo allo staff campagna principale.</p>
              )}
              {blocked && reasons.length > 0 && (
                <ul className="text-xs text-red-200/90 list-disc pl-5 space-y-0.5">
                  {reasons.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              )}
              {!blocked && (
                <p className="text-center text-sm text-indigo-200/90">
                  Da <span className="font-bold">{minCost} €</span>
                  {Array.isArray(ev.opzioni) && ev.opzioni.length > 0 ? ' (con opzioni)' : null}
                </p>
              )}
            </div>
          );
        })}

      {modalEvent && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-md rounded-xl border border-gray-600 bg-gray-900 p-5 space-y-4 relative max-h-[90vh] overflow-y-auto">
            <button
              type="button"
              className="absolute top-3 right-3 p-1 rounded text-gray-400 hover:text-white"
              onClick={closeModal}
              aria-label="Chiudi"
            >
              <X size={22} />
            </button>
            <h3 className="text-lg font-bold pr-8">
              {modalTipo === 'integra' ? 'Integra iscrizione' : modalEvent.titolo}
            </h3>
            <EventSinossi content={modalEvent.sinossi} />
            <div className="rounded-lg border border-emerald-700 bg-emerald-950/40 px-3 py-2 text-center">
              <p className="text-xs uppercase tracking-wide text-emerald-300 font-black">Importo da pagare</p>
              <p className="text-3xl font-black text-emerald-100 leading-tight">{importoTotale.toFixed(2)} €</p>
            </div>
            {renderOpzioniModal()}
            {modalTipo === 'iscrizione' ? (
              <>
                <p className="text-sm text-gray-400">Scegli il personaggio da iscrivere (campagna principale, vivo).</p>
                <label className="block text-xs font-bold text-gray-400 uppercase">Personaggio</label>
                <select
                  className="w-full rounded-lg border border-gray-600 bg-gray-800 px-3 py-2 text-white"
                  value={selectedPgId}
                  onChange={(e) => setSelectedPgId(e.target.value)}
                >
                  <option value="">— Seleziona —</option>
                  {eligibleCharacters.map((c) => (
                    <option key={c.id} value={String(c.id)}>
                      {c.nome}
                    </option>
                  ))}
                </select>
                {eligibleCharacters.length === 0 && (
                  <p className="text-sm text-amber-200">Nessun personaggio disponibile per l&apos;iscrizione.</p>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-400">
                Personaggio: <span className="text-white font-semibold">{modalEvent.already_registered?.personaggio_nome}</span>
              </p>
            )}
            {importoTotale <= 0 && selectedPgId && (
              <p className="text-sm text-amber-200">Seleziona almeno un&apos;opzione a pagamento.</p>
            )}
            {paypalUiErr && <p className="text-sm text-red-300">{paypalUiErr}</p>}
            {selectedPgId && importoTotale > 0 ? <div ref={paypalHostRef} className="min-h-[120px]" /> : null}
          </div>
        </div>
      )}
    </div>
  );
}
