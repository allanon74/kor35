import React, { useCallback, useEffect, useState } from 'react';
import { ImageIcon, KeyRound, Loader, RefreshCw, ShieldCheck } from 'lucide-react';
import {
  openverseRegisterFromBrowser,
  staffAggiornaMinigiocoBiblioteca,
  staffGetMinigiocoBiblioteca,
  staffSalvaOpenverseMinigioco,
  staffVerificaOpenverseMinigioco,
} from '../../api';

const DEFAULT_OPENVERSE_FORM = {
  name: 'KOR35 Libreria Minigioco',
  description: 'App staff KOR35 per scaricare immagini Creative Commons per i minigiochi QR (LARP).',
  email: '',
};

const MinigiocoBibliotecaPanel = ({ onLogout }) => {
  const [data, setData] = useState({ count: 0, target: 100, items: [], openverse: {} });
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [msg, setMsg] = useState('');
  const [openverseForm, setOpenverseForm] = useState(DEFAULT_OPENVERSE_FORM);
  const [registeredSecret, setRegisteredSecret] = useState(null);
  const [manualCreds, setManualCreds] = useState({ client_id: '', client_secret: '' });
  const [showManual, setShowManual] = useState(false);
  const [savingManual, setSavingManual] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setMsg('');
    try {
      const res = await staffGetMinigiocoBiblioteca(onLogout);
      setData(res || { count: 0, target: 100, items: [], openverse: {} });
      if (res?.openverse?.contact_email) {
        setOpenverseForm((prev) => (
          prev.email ? prev : { ...prev, email: res.openverse.contact_email }
        ));
      }
    } catch (e) {
      setMsg(e.message || 'Errore caricamento libreria');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const aggiorna = async () => {
    if (!window.confirm('Scaricare ~100 immagini open license (Openverse / Wikimedia)? Può richiedere 1–2 minuti.')) {
      return;
    }
    setUpdating(true);
    setMsg('Download in corso… attendere.');
    try {
      const res = await staffAggiornaMinigiocoBiblioteca(data.target || 100, onLogout);
      setMsg(
        res?.ok
          ? `Libreria aggiornata: ${res.count}/${res.target} immagini${
              Array.isArray(res.sources_used) && res.sources_used.length
                ? ` (${res.sources_used.join(' + ')})`
                : ''
            } (${Math.round((res.elapsed_ms || 0) / 1000)}s).`
          : res?.error || 'Aggiornamento fallito.'
      );
      await load();
    } catch (e) {
      const detail =
        e?.data?.error ||
        (Array.isArray(e?.data?.openverse_errors) && e.data.openverse_errors[0]) ||
        (Array.isArray(e?.data?.wikimedia_errors) && e.data.wikimedia_errors[0]) ||
        (Array.isArray(e?.data?.errors_sample) && e.data.errors_sample[0]);
      setMsg(detail || e.message || 'Errore aggiornamento libreria');
    } finally {
      setUpdating(false);
    }
  };

  const registraOpenverse = async () => {
    if (!openverseForm.email?.trim()) {
      setMsg('Inserisci un indirizzo email per la registrazione Openverse.');
      return;
    }
    const conferma = data.openverse?.configured
      ? window.confirm(
          'Esiste già una configurazione Openverse su questo server. Registrare di nuovo sostituirà le credenziali salvate. Continuare?'
        )
      : window.confirm(
          'Registrare una nuova app Openverse dal tuo browser? Riceverai un\'email di verifica da Openverse.'
        );
    if (!conferma) return;

    setRegistering(true);
    setRegisteredSecret(null);
    setMsg('Registrazione Openverse dal browser…');
    try {
      const ov = await openverseRegisterFromBrowser(openverseForm);
      const res = await staffSalvaOpenverseMinigioco(
        {
          ...openverseForm,
          client_id: ov.client_id,
          client_secret: ov.client_secret,
          api_message: ov.msg || '',
        },
        onLogout
      );
      setRegisteredSecret({
        client_id: ov.client_id,
        client_secret: ov.client_secret,
        message: ov.msg || res?.message,
      });
      setMsg(ov.msg || res?.message || 'App Openverse registrata. Controlla la email per la verifica.');
      await load();
    } catch (e) {
      setMsg(
        e?.cloudflare
          ? `${e.message} Oppure incolla le credenziali ottenute altrove nel form sotto.`
          : e?.data?.error || e.message || 'Registrazione Openverse fallita.'
      );
      setShowManual(true);
    } finally {
      setRegistering(false);
    }
  };

  const salvaCredenzialiManuali = async () => {
    if (!manualCreds.client_id?.trim() || !manualCreds.client_secret?.trim()) {
      setMsg('Inserisci client_id e client_secret.');
      return;
    }
    setSavingManual(true);
    setMsg('Salvataggio credenziali…');
    try {
      const res = await staffSalvaOpenverseMinigioco(
        {
          ...openverseForm,
          client_id: manualCreds.client_id.trim(),
          client_secret: manualCreds.client_secret.trim(),
        },
        onLogout
      );
      setMsg(res?.message || 'Credenziali Openverse salvate sul server.');
      setManualCreds({ client_id: '', client_secret: '' });
      await load();
    } catch (e) {
      setMsg(e?.data?.error || e.message || 'Salvataggio credenziali fallito.');
    } finally {
      setSavingManual(false);
    }
  };

  const verificaOpenverse = async () => {
    setVerifying(true);
    setMsg('Verifica connessione Openverse…');
    try {
      const res = await staffVerificaOpenverseMinigioco(onLogout);
      setMsg(res?.message || 'Connessione Openverse verificata.');
    } catch (e) {
      setMsg(e?.data?.error || e.message || 'Verifica Openverse fallita.');
    } finally {
      setVerifying(false);
    }
  };

  const openverse = data.openverse || {};

  return (
    <div className="mb-6 p-4 bg-gray-800/60 rounded-lg border border-emerald-700/40">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 text-emerald-300 font-bold uppercase text-sm tracking-wide">
          <ImageIcon size={16} />
          Libreria immagini minigioco
        </div>
        <button
          type="button"
          disabled={updating}
          onClick={aggiorna}
          className="flex items-center gap-2 px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 rounded text-xs font-bold disabled:opacity-50"
        >
          {updating ? <Loader className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Aggiorna libreria ({data.target || 100})
        </button>
      </div>

      <p className="text-xs text-gray-400 mb-2">
        Immagini CC0 / CC-BY da Openverse o Wikimedia Commons. Se un QR non ha immagine dedicata e l&apos;opzione è attiva,
        ne viene scelta una a caso da qui.
      </p>

      <div className="mb-4 p-3 rounded border border-sky-800/50 bg-sky-950/30">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 text-sky-300 text-xs font-bold uppercase tracking-wide">
            <KeyRound size={14} />
            Openverse (server VPS)
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={registering || verifying}
              onClick={registraOpenverse}
              className="px-2.5 py-1 bg-sky-700 hover:bg-sky-600 rounded text-[11px] font-bold disabled:opacity-50"
            >
              {registering ? 'Registrazione…' : openverse.configured ? 'Rigenera credenziali' : 'Registra dal browser'}
            </button>
            <button
              type="button"
              disabled={!openverse.configured || registering || verifying}
              onClick={verificaOpenverse}
              className="flex items-center gap-1 px-2.5 py-1 bg-gray-700 hover:bg-gray-600 rounded text-[11px] font-bold disabled:opacity-50"
            >
              {verifying ? <Loader className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
              Verifica
            </button>
          </div>
        </div>

        <p className="text-[11px] text-gray-400 mb-2">
          Il server VPS (DigitalOcean) è spesso bloccato da Cloudflare su Openverse. La registrazione parte dal
          <strong className="text-gray-300"> tuo browser</strong> (non dal server); le credenziali vengono poi salvate
          sul server. Openverse invierà un&apos;email di verifica — finché non la confermi, il token potrebbe non funzionare.
        </p>

        {openverse.configured ? (
          <p className="text-[11px] text-emerald-300 mb-2">
            Configurato ({openverse.source === 'env' ? 'file .env' : 'database'})
            {openverse.client_id_masked ? ` · client ${openverse.client_id_masked}` : ''}
            {openverse.registered_at
              ? ` · registrato ${new Date(openverse.registered_at).toLocaleString()}`
              : ''}
          </p>
        ) : (
          <p className="text-[11px] text-amber-300 mb-2">Openverse non configurato su questo server.</p>
        )}

        {openverse.api_message && (
          <p className="text-[11px] text-gray-500 mb-2">{openverse.api_message}</p>
        )}

        <div className="grid gap-2 sm:grid-cols-3">
          <label className="text-[11px] text-gray-400">
            Nome app
            <input
              type="text"
              value={openverseForm.name}
              onChange={(e) => setOpenverseForm((prev) => ({ ...prev, name: e.target.value }))}
              className="mt-1 w-full px-2 py-1 rounded bg-gray-900 border border-gray-700 text-xs text-white"
            />
          </label>
          <label className="text-[11px] text-gray-400 sm:col-span-2">
            Descrizione
            <input
              type="text"
              value={openverseForm.description}
              onChange={(e) => setOpenverseForm((prev) => ({ ...prev, description: e.target.value }))}
              className="mt-1 w-full px-2 py-1 rounded bg-gray-900 border border-gray-700 text-xs text-white"
            />
          </label>
          <label className="text-[11px] text-gray-400 sm:col-span-3">
            Email contatto (ricevi verifica Openverse)
            <input
              type="email"
              value={openverseForm.email}
              onChange={(e) => setOpenverseForm((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="staff@kor35.it"
              className="mt-1 w-full px-2 py-1 rounded bg-gray-900 border border-gray-700 text-xs text-white"
            />
          </label>
        </div>

        {registeredSecret && (
          <div className="mt-3 p-2 rounded border border-amber-700/50 bg-amber-950/20 text-[11px] text-amber-200">
            <p className="font-bold mb-1">Credenziali generate (mostrate una sola volta)</p>
            <p className="break-all">Client ID: {registeredSecret.client_id}</p>
            <p className="break-all">Client secret: {registeredSecret.client_secret}</p>
            {registeredSecret.message && <p className="mt-1 text-amber-300">{registeredSecret.message}</p>}
          </div>
        )}

        <div className="mt-3 border-t border-gray-700/60 pt-2">
          <button
            type="button"
            onClick={() => setShowManual((v) => !v)}
            className="text-[11px] text-sky-400 hover:text-sky-300 underline"
          >
            {showManual ? 'Nascondi incolla credenziali' : 'Hai già client_id e client_secret? Incollali qui'}
          </button>
          {showManual && (
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label className="text-[11px] text-gray-400 sm:col-span-2">
                Client ID
                <input
                  type="text"
                  value={manualCreds.client_id}
                  onChange={(e) => setManualCreds((prev) => ({ ...prev, client_id: e.target.value }))}
                  className="mt-1 w-full px-2 py-1 rounded bg-gray-900 border border-gray-700 text-xs text-white font-mono"
                />
              </label>
              <label className="text-[11px] text-gray-400 sm:col-span-2">
                Client secret
                <input
                  type="password"
                  value={manualCreds.client_secret}
                  onChange={(e) => setManualCreds((prev) => ({ ...prev, client_secret: e.target.value }))}
                  className="mt-1 w-full px-2 py-1 rounded bg-gray-900 border border-gray-700 text-xs text-white font-mono"
                />
              </label>
              <button
                type="button"
                disabled={savingManual}
                onClick={salvaCredenzialiManuali}
                className="sm:col-span-2 px-2.5 py-1 bg-gray-700 hover:bg-gray-600 rounded text-[11px] font-bold disabled:opacity-50"
              >
                {savingManual ? 'Salvataggio…' : 'Salva credenziali sul server'}
              </button>
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Loader className="w-4 h-4 animate-spin" /> Caricamento anteprima…
        </div>
      ) : (
        <>
          <p className="text-xs text-gray-500 mb-2">
            {data.count} immagini in libreria
            {data.ultimo_aggiornamento ? ` · ultimo aggiornamento ${new Date(data.ultimo_aggiornamento).toLocaleString()}` : ''}
          </p>
          {data.items?.length > 0 && (
            <div className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-10 gap-1 max-h-40 overflow-y-auto">
              {data.items.slice(0, 40).map((item) => (
                <a
                  key={item.id}
                  href={item.source_page_url || item.immagine_url}
                  target="_blank"
                  rel="noreferrer"
                  title={[item.titolo, item.autore, item.licenza].filter(Boolean).join(' · ')}
                  className="block aspect-square rounded overflow-hidden border border-gray-700 hover:border-emerald-500"
                >
                  {item.immagine_url ? (
                    <img src={item.immagine_url} alt="" className="w-full h-full object-cover" loading="lazy" />
                  ) : (
                    <span className="flex items-center justify-center w-full h-full bg-gray-900 text-[10px] text-gray-600">?</span>
                  )}
                </a>
              ))}
            </div>
          )}
        </>
      )}

      {msg && <p className="text-xs text-center text-amber-300 mt-2">{msg}</p>}
    </div>
  );
};

export default MinigiocoBibliotecaPanel;
