import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL, getArcanaSSOStatus } from '../api';

const LoginPage = ({ onLoginSuccess }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  const [message, setMessage] = useState({ text: '', type: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [ssoStatus, setSsoStatus] = useState(null);
  const [useLocalPassword, setUseLocalPassword] = useState(false);

  const showArcanaSso =
    ssoStatus && ssoStatus.enabled && ssoStatus.reachable;

  useEffect(() => {
    let cancelled = false;
    getArcanaSSOStatus()
      .then((s) => {
        if (!cancelled) setSsoStatus(s);
      })
      .catch(() => {
        if (!cancelled) setSsoStatus({ enabled: false, reachable: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ticket = params.get('arcana_ticket');
    const ssoError = params.get('arcana_error');

    if (ssoError) {
      const ssoMessages = {
        callback_failed: 'Errore durante il completamento login su Arcana Domine.',
        invalid_state: 'Sessione SSO scaduta o già usata. Riprova dal pulsante Arcana.',
        missing_code_or_state: 'Risposta incompleta da Arcana Domine.',
        missing_access_token: 'Token di accesso non ricevuto da Arcana Domine.',
      };
      setMessage({
        text: ssoMessages[ssoError] || `Errore login Arcana Domine (${ssoError}). Riprova.`,
        type: 'error',
      });
      return;
    }

    if (!ticket) return;

    const exchangeTicket = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/arcana/exchange-ticket/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket }),
        });
        if (!response.ok) throw new Error('Ticket SSO non valido o scaduto.');
        const data = await response.json();
        localStorage.setItem('kor35_token', data.token);
        localStorage.setItem('kor35_is_admin', String(!!data.is_superuser));
        localStorage.removeItem('kor35_is_staff');
        localStorage.removeItem('kor35_is_master');
        localStorage.setItem('kor35_login_method', 'arcana');
        if (onLoginSuccess && typeof onLoginSuccess === 'function') {
          onLoginSuccess(data.token);
        }
        window.location.href = data.next || '/app';
      } catch (err) {
        setMessage({ text: err.message, type: 'error' });
      } finally {
        setIsLoading(false);
      }
    };
    exchangeTicket();
  }, [onLoginSuccess]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.id]: e.target.value });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setMessage({ text: '', type: '' });
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        throw new Error('Credenziali non valide. Riprova.');
      }

      const data = await response.json();

      if (data.token) {
        localStorage.setItem('kor35_token', data.token);
        localStorage.setItem('kor35_is_admin', String(!!data.is_superuser));
        localStorage.removeItem('kor35_is_staff');
        localStorage.removeItem('kor35_is_master');
        localStorage.setItem('kor35_login_method', 'local');

        if (onLoginSuccess && typeof onLoginSuccess === 'function') {
          onLoginSuccess(data.token);
        } else {
          window.location.reload();
        }
      } else {
        throw new Error('Token non ricevuto.');
      }
    } catch (err) {
      setMessage({ text: err.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  const goArcana = () => {
    localStorage.removeItem('kor35_token');
    localStorage.removeItem('kor35_is_admin');
    localStorage.removeItem('kor35_is_staff');
    localStorage.removeItem('kor35_is_master');
    localStorage.removeItem('kor35_login_method');
    window.location.href = `${API_BASE_URL}/api/auth/arcana/login/?next=${encodeURIComponent('/app')}`;
  };

  const showLocalForm = !showArcanaSso || useLocalPassword;

  return (
    <div
      className="flex items-center justify-center min-h-screen px-4"
      style={{
        background:
          'radial-gradient(ellipse at 20% 0%, #7f1d1d66, transparent 50%), linear-gradient(165deg, #0c0a09 0%, #1c100c 40%, #111827 100%)',
      }}
    >
      <div className="w-full max-w-md p-8 space-y-6 rounded-lg border border-stone-700/80 bg-black/55 backdrop-blur-sm shadow-2xl">
        <div className="text-center space-y-3">
          <img
            src="/Logo Kor-AD_Trasp.png"
            alt=""
            width={72}
            height={72}
            className="mx-auto h-16 w-16 object-contain"
          />
          <h1 className="wiki-hero-brand text-3xl text-white">KOR35</h1>
          <p className="text-sm text-stone-300">Accedi all&apos;area di gioco</p>
        </div>

        {message.text && (
          <div
            className={`p-3 text-sm text-center rounded ${
              message.type === 'success' ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'
            }`}
          >
            {message.text}
          </div>
        )}

        {showArcanaSso && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={goArcana}
              disabled={isLoading}
              className="w-full px-4 py-2.5 font-bold text-white bg-emerald-800 rounded-md shadow-lg hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
            >
              Accedi con Arcana Domine
            </button>
            <label className="flex items-start gap-2 text-sm text-stone-300 cursor-pointer">
              <input
                type="checkbox"
                className="mt-1 rounded border-gray-600"
                checked={useLocalPassword}
                onChange={(e) => {
                  setUseLocalPassword(e.target.checked);
                  setMessage({ text: '', type: '' });
                }}
              />
              <span>No, voglio entrare con la password locale</span>
            </label>
          </div>
        )}

        {showLocalForm && (
          <form className="space-y-4" onSubmit={handleLogin}>
            {showArcanaSso && (
              <p className="text-xs text-stone-400">Accesso con utente e password Kor35.</p>
            )}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-stone-300">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={formData.username}
                onChange={handleChange}
                required
                autoComplete="username"
                className="w-full px-3 py-2 mt-1 text-gray-900 bg-stone-100 border border-stone-500 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-red-700"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-stone-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                autoComplete="current-password"
                className="w-full px-3 py-2 mt-1 text-gray-900 bg-stone-100 border border-stone-500 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-red-700"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full px-4 py-2.5 font-bold text-white bg-[var(--wiki-brand,#7f1d1d)] rounded-md shadow-lg hover:bg-[var(--wiki-brand-hot,#b91c1c)] focus:outline-none focus:ring-2 focus:ring-red-600 disabled:opacity-50"
            >
              {isLoading ? 'Attendere...' : 'Accedi'}
            </button>
          </form>
        )}

        <p className="text-center text-xs text-stone-500">
          <Link to="/" className="text-stone-300 hover:text-white underline-offset-2 hover:underline">
            Torna al regolamento
          </Link>
        </p>

        {ssoStatus === null && (
          <p className="text-center text-xs text-stone-500">Verifica accesso Arcana Domine...</p>
        )}
      </div>
    </div>
  );
};

export default LoginPage;
