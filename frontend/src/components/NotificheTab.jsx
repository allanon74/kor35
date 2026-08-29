import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Bell, Calendar, Copy, Link2, Mail, RefreshCw, Send, Smartphone, Unlink } from 'lucide-react';
import {
  getNotificaPreferenze,
  patchNotificaPreferenze,
  postTelegramLink,
  postTelegramUnlink,
  postCalendarioFeedTokenRigenera,
} from '../api';
import { useCharacter } from './CharacterContext';
import { isWebPushSupported } from '../lib/webpush';

const CHANNELS = [
  { id: 'webpush', label: 'Web push KOR35', hint: 'Notifiche del browser / PWA', Icon: Smartphone },
  { id: 'telegram', label: 'Telegram', hint: 'Messaggi sul bot KOR35', Icon: Send },
  { id: 'email', label: 'Email', hint: 'Casella Gmail di campagna', Icon: Mail },
];

function Toggle({ checked, disabled, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors ${
        disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
      } ${checked ? 'bg-emerald-600' : 'bg-gray-600'}`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
          checked ? 'left-5' : 'left-0.5'
        }`}
      />
    </button>
  );
}

export default function NotificheTab({ onLogout }) {
  const { subscribeToPush } = useCharacter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [tgLink, setTgLink] = useState(null);
  const [pushMsg, setPushMsg] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const row = await getNotificaPreferenze(onLogout);
      setData(row);
    } catch (e) {
      setError(e?.message || 'Impossibile caricare le preferenze.');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const icsUrl = useMemo(() => {
    const path = data?.calendario?.path;
    if (!path || typeof window === 'undefined') return '';
    return `${window.location.origin}${path}`;
  }, [data]);

  const setChannel = async (canale, categoria, enabled) => {
    if (!data?.canali) return;
    setSaving(true);
    setError('');
    try {
      const row = await patchNotificaPreferenze({ canali: { [canale]: { [categoria]: enabled } } }, onLogout);
      setData(row);
    } catch (e) {
      setError(e?.message || 'Salvataggio fallito.');
    } finally {
      setSaving(false);
    }
  };

  const copyIcs = async () => {
    if (!icsUrl) return;
    try {
      await navigator.clipboard.writeText(icsUrl);
      setInfo(
        'Link calendario copiato. Incollalo in Google Calendar (Altri calendari → Da URL) o in iOS Calendario (Aggiungi calendario iscritto).',
      );
    } catch {
      window.prompt('Copia il link calendario:', icsUrl);
    }
  };

  const rigeneraIcs = async () => {
    if (!window.confirm('Il vecchio link smetterà di funzionare. Continuare?')) return;
    try {
      const row = await postCalendarioFeedTokenRigenera(onLogout);
      setData((prev) => (prev ? { ...prev, calendario: row } : prev));
      setInfo('Nuovo link calendario generato. Aggiorna la sottoscrizione sul telefono.');
    } catch (e) {
      setError(e?.message || 'Impossibile rigenerare il link.');
    }
  };

  const collegaTelegram = async () => {
    setError('');
    try {
      const row = await postTelegramLink(onLogout);
      setTgLink(row);
    } catch (e) {
      setError(e?.detail || e?.message || 'Telegram non è configurato sul server.');
    }
  };

  const scollegaTelegram = async () => {
    try {
      const row = await postTelegramUnlink(onLogout);
      setData(row);
      setTgLink(null);
      setInfo('Telegram scollegato.');
    } catch (e) {
      setError(e?.message || 'Scollegamento fallito.');
    }
  };

  const attivaWebPush = async () => {
    const result = await subscribeToPush();
    if (result?.ok) {
      setPushMsg('Notifiche browser attive su questo dispositivo.');
    } else {
      setPushMsg(result?.message || 'Impossibile attivare le notifiche browser.');
    }
  };

  if (loading && !data) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400" role="status">
        Caricamento notifiche…
      </div>
    );
  }

  const categorie = data?.categorie || [];
  const canali = data?.canali || {};
  const telegram = data?.telegram || {};
  const email = data?.email || {};
  const includeCompiti = !!data?.calendario?.include_compiti;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-5 max-w-3xl mx-auto">
      <header className="flex items-start gap-3">
        <Bell className="text-violet-300 shrink-0 mt-0.5" size={22} />
        <div>
          <h1 className="text-lg font-bold text-white">Notifiche</h1>
          <p className="text-sm text-gray-400">
            Scegli come ricevere gli avvisi. Il web push KOR35 è attivo di default; Telegram ed email restano spenti
            finché non li abiliti. Le istruzioni per calendario e Telegram sono in questa scheda; il pulsante «?»
            in alto apre anche la guida wiki (visibile solo da loggati).
          </p>
        </div>
      </header>

      {error ? (
        <p className="text-sm text-red-300 bg-red-950/50 border border-red-800 rounded-lg px-3 py-2">{error}</p>
      ) : null}
      {info ? (
        <p className="text-sm text-sky-200 bg-sky-950/50 border border-sky-800 rounded-lg px-3 py-2">{info}</p>
      ) : null}

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[520px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-gray-500 border-b border-gray-800">
                <th className="text-left font-semibold px-3 py-2">Categoria</th>
                {CHANNELS.map((ch) => (
                  <th key={ch.id} className="text-center font-semibold px-2 py-2">
                    <span className="inline-flex items-center gap-1 justify-center">
                      <ch.Icon size={12} />
                      {ch.label}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {categorie.map((cat) => (
                <tr key={cat.id} className="border-b border-gray-800 last:border-0">
                  <td className="px-3 py-2.5 text-gray-200">{cat.label}</td>
                  {CHANNELS.map((ch) => {
                    const on = !!canali?.[ch.id]?.[cat.id];
                    const telegramBlocked = ch.id === 'telegram' && !telegram.linked;
                    const emailBlocked = ch.id === 'email' && !email.address;
                    return (
                      <td key={ch.id} className="px-2 py-2 text-center">
                        <div className="flex justify-center">
                          <Toggle
                            checked={on}
                            disabled={saving || telegramBlocked || emailBlocked}
                            label={`${ch.label}: ${cat.label}`}
                            onChange={(v) => setChannel(ch.id, cat.id, v)}
                          />
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 space-y-3">
        <h2 className="font-bold text-white flex items-center gap-2">
          <Smartphone size={16} className="text-violet-300" /> Web push KOR35
        </h2>
        <p className="text-sm text-gray-400">
          Default acceso. Serve il permesso del browser (HTTPS). Funziona anche nella PWA installata.
        </p>
        {isWebPushSupported() ? (
          <button
            type="button"
            onClick={attivaWebPush}
            className="rounded-lg bg-violet-700 hover:bg-violet-600 px-3 py-1.5 text-sm font-bold text-white"
          >
            Attiva su questo dispositivo
          </button>
        ) : (
          <p className="text-xs text-amber-300">Questo browser non supporta le push (serve HTTPS e un browser moderno).</p>
        )}
        {pushMsg ? <p className="text-xs text-gray-300">{pushMsg}</p> : null}
      </section>

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 space-y-3">
        <h2 className="font-bold text-white flex items-center gap-2">
          <Send size={16} className="text-sky-300" /> Telegram
        </h2>
        <p className="text-sm text-gray-400">
          Default spento. Collega il bot, poi accendi le categorie nella colonna Telegram.
        </p>
        <ol className="text-sm text-gray-300 space-y-2 list-decimal pl-5">
          <li>
            Tocca <strong className="text-white">Collega Telegram</strong> qui sotto. Si apre il bot KOR35:
            premi <strong className="text-white">Avvia</strong>.
          </li>
          <li>
            Se Telegram non si apre, cerca il bot e invia il comando{' '}
            <code className="text-sky-200">/start CODICE</code> con il codice mostrato in app (scade in 30 minuti).
          </li>
          <li>
            Quando lo stato è «Collegato», accendi le categorie nella colonna Telegram (restano spente finché non le attivi).
          </li>
          <li>
            Per scollegare usa il pulsante in questa scheda oppure scrivi{' '}
            <code className="text-sky-200">/stop</code> al bot.
          </li>
        </ol>
        {telegram.linked ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-emerald-300">
              Collegato{telegram.username ? ` (@${telegram.username})` : ''}.
            </span>
            <button
              type="button"
              onClick={scollegaTelegram}
              className="inline-flex items-center gap-1 text-xs font-semibold text-red-300 hover:text-red-200"
            >
              <Unlink size={12} /> Scollega
            </button>
          </div>
        ) : telegram.bot_configured ? (
          <div className="space-y-2">
            <button
              type="button"
              onClick={collegaTelegram}
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky-800 hover:bg-sky-700 px-3 py-1.5 text-sm font-bold text-white"
            >
              <Link2 size={14} /> Collega Telegram
            </button>
            {tgLink?.start_url ? (
              <div className="text-sm text-gray-300 space-y-1">
                <p>{tgLink.instructions}</p>
                <a
                  href={tgLink.start_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-300 underline break-all"
                >
                  {tgLink.start_url}
                </a>
                <p className="text-xs text-gray-500">
                  In alternativa cerca @{tgLink.bot_username} e invia <code>/start {tgLink.code}</code>.
                </p>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-amber-200">
            Telegram non è ancora configurato sul server (mancano token e username del bot). Chiedi allo staff di
            impostare <code>TELEGRAM_BOT_TOKEN</code> e <code>TELEGRAM_BOT_USERNAME</code>.
          </p>
        )}
      </section>

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 space-y-3">
        <h2 className="font-bold text-white flex items-center gap-2">
          <Mail size={16} className="text-amber-300" /> Email
        </h2>
        <p className="text-sm text-gray-400">
          Default spento. Le mail partono dalla casella Gmail di campagna (SMTP). Serve un indirizzo sul tuo account
          KOR35.
        </p>
        {email.address ? (
          <p className="text-sm text-gray-300">
            Destinazione: <span className="font-mono text-amber-100">{email.address}</span>
          </p>
        ) : (
          <p className="text-sm text-amber-200">
            Nessuna email sull&apos;account. Aggiungila dal profilo utente (o chiedi allo staff) prima di abilitare il
            canale.
          </p>
        )}
        {!email.configured ? (
          <p className="text-xs text-gray-500">
            SMTP non configurato su questo nodo: le email non partiranno finché lo staff non imposta host e casella
            campagna.
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border border-sky-900 bg-sky-950/30 p-4 space-y-3">
        <h2 className="font-bold text-sky-100 flex items-center gap-2">
          <Calendar size={16} /> Calendario (iCal)
        </h2>
        <p className="text-sm text-sky-200/80">
          {includeCompiti
            ? 'Il tuo feed include gli eventi KOR35 e i compiti assegnati (ruolo aiuto staff / staff / master).'
            : 'Il tuo feed include solo gli eventi KOR35. I compiti operativi restano riservati ad aiuto staff, staff e master.'}{' '}
          Il link è personale: non condividerlo. Le modifiche fatte sul telefono non tornano in KOR35.
        </p>
        <ol className="text-sm text-sky-100/90 space-y-2 list-decimal pl-5">
          <li>
            Tocca <strong>Copia link iscrizione</strong>.
          </li>
          <li>
            <strong>Google Calendar (computer)</strong>: a sinistra, Altri calendari → il «+» → Da URL → incolla il
            link → Aggiungi calendario.
          </li>
          <li>
            <strong>Android</strong>: apri Google Calendar con lo stesso account, oppure Impostazioni → Aggiungi
            calendario → Da URL (se disponibile). Il calendario iscritto dal computer si sincronizza sul telefono.
          </li>
          <li>
            <strong>iPhone / iPad</strong>: Impostazioni → App → Calendario → Account calendario → Aggiungi account →
            Altro → Aggiungi calendario iscritto → incolla il link. Su iOS più vecchi: Impostazioni → Calendario →
            Account → Aggiungi account → Altro.
          </li>
          <li>
            Se usi <strong>Rigenera link</strong>, il vecchio URL smette di funzionare: aggiorna la sottoscrizione sul
            telefono.
          </li>
        </ol>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={copyIcs}
            disabled={!icsUrl}
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-800 hover:bg-sky-700 px-3 py-1.5 text-sm font-bold text-white disabled:opacity-50"
          >
            <Copy size={14} /> Copia link iscrizione
          </button>
          <button
            type="button"
            onClick={rigeneraIcs}
            className="inline-flex items-center gap-1.5 rounded-lg border border-sky-800 px-3 py-1.5 text-sm font-semibold text-sky-200 hover:bg-sky-900/60"
          >
            <RefreshCw size={14} /> Rigenera link
          </button>
        </div>
        {icsUrl ? <p className="text-[11px] text-sky-400/80 break-all font-mono">{icsUrl}</p> : null}
      </section>
    </div>
  );
}
