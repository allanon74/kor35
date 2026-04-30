import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Ticket, X } from 'lucide-react';
import {
  fetchAuthenticated,
  getIscrizioniEventoEligibility,
  postIscrizioneEventoCattura,
  postIscrizioneEventoCreaOrdine,
} from '../api';

function loadPayPalScript(clientId, currency, sandbox) {
  const host = sandbox ? 'https://www.sandbox.paypal.com' : 'https://www.paypal.com';
  const src = `${host}/sdk/js?client-id=${encodeURIComponent(clientId)}&currency=${encodeURIComponent(
    currency || 'EUR'
  )}&intent=capture`;
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

/**
 * Blocco start page: iscrizione eventi con PayPal (finestra date + condizioni Arcana/password/PG).
 */
export default function EventSubscriptionStartPanel({ onLogout }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [modalEvent, setModalEvent] = useState(null);
  const [modalChars, setModalChars] = useState([]);
  const [selectedPgId, setSelectedPgId] = useState('');
  const [paypalUiErr, setPaypalUiErr] = useState('');
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

  const eligibleCharacters = useMemo(() => {
    if (!Array.isArray(modalChars)) return [];
    return modalChars.filter((c) => {
      if (c.data_morte) return false;
      if (c.tipologia_giocante === false) return false;
      return true;
    });
  }, [modalChars]);

  const closeModal = () => {
    setModalEvent(null);
    setSelectedPgId('');
    setPaypalUiErr('');
    if (paypalHostRef.current) {
      paypalHostRef.current.innerHTML = '';
    }
  };

  useEffect(() => {
    if (!modalEvent || !selectedPgId) return undefined;
    const clientId = String(modalEvent.paypal_client_id || '').trim();
    if (!clientId) {
      setPaypalUiErr('PayPal non configurato (client id mancante).');
      return undefined;
    }
    const sandbox = !!modalEvent.paypal_uses_sandbox;
    let cancelled = false;
    const run = async () => {
      setPaypalUiErr('');
      if (paypalHostRef.current) paypalHostRef.current.innerHTML = '';
      try {
        await loadPayPalScript(clientId, 'EUR', sandbox);
        if (cancelled || !window.paypal) throw new Error('SDK PayPal non disponibile');
        const buttons = window.paypal.Buttons({
          style: { layout: 'vertical', shape: 'rect', label: 'pay' },
          createOrder: async () => {
            const res = await postIscrizioneEventoCreaOrdine(
              { evento_id: modalEvent.id, personaggio_id: parseInt(selectedPgId, 10) },
              onLogout
            );
            const oid = res?.paypal_order_id;
            if (!oid) throw new Error(res?.error || 'Ordine PayPal non creato');
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
          onCancel: () => {
            closeModal();
            navigate('/app/iscrizione-esito?esito=cancellato');
          },
          onError: () => {
            closeModal();
            navigate('/app/iscrizione-esito?esito=rifiutato');
          },
        });
        if (paypalHostRef.current) await buttons.render(paypalHostRef.current);
      } catch (e) {
        if (!cancelled) setPaypalUiErr(e?.message || 'Errore PayPal');
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [modalEvent, selectedPgId, navigate, onLogout]);

  const events = Array.isArray(data?.events) ? data.events : [];
  if (!loading && events.length === 0 && !err) {
    return null;
  }

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
              <div
                key={ev.id}
                className="rounded-lg border border-emerald-800/70 bg-emerald-950/30 px-4 py-3 text-emerald-100 text-center text-base font-semibold"
              >
                {nomePg} già iscritto all&apos;evento «{ev.titolo}»
              </div>
            );
          }
          const blocked = ev.cta_kind === 'blocked' || !ev.paypal_ready;
          const reasons = [];
          if (!ev.paypal_ready) reasons.push('PayPal non configurato in amministrazione (credenziali mancanti).');
          (ev.blocking_reasons || []).forEach((r) => reasons.push(r));
          const label = ev.is_test ? `[TEST] Iscriviti: ${ev.titolo}` : `Iscriviti all'evento ${ev.titolo}`;
          return (
            <div key={ev.id} className="space-y-2">
              <button
                type="button"
                disabled={blocked}
                onClick={() => {
                  if (blocked) return;
                  setModalEvent(ev);
                  setSelectedPgId('');
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
                  Costo: <span className="font-bold">{ev.costo_euro} €</span>
                </p>
              )}
            </div>
          );
        })}

      {modalEvent && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-md rounded-xl border border-gray-600 bg-gray-900 p-5 space-y-4 relative">
            <button
              type="button"
              className="absolute top-3 right-3 p-1 rounded text-gray-400 hover:text-white"
              onClick={closeModal}
              aria-label="Chiudi"
            >
              <X size={22} />
            </button>
            <h3 className="text-lg font-bold pr-8">{modalEvent.titolo}</h3>
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
            {paypalUiErr && <p className="text-sm text-red-300">{paypalUiErr}</p>}
            {selectedPgId ? <div ref={paypalHostRef} className="min-h-[120px]" /> : null}
          </div>
        </div>
      )}
    </div>
  );
}
