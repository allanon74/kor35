import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { PREVIEW_STATION } from '../kioskPreview.js';
import { navigateScreen } from '../viewport.js';

const EMPTY = {
  ingegneria: {
    nome: 'Console Ingegneria',
    enabled: false,
    sigla: '…',
    requisito: '…',
    screen: 'compattatore',
  },
  scientifica: {
    nome: 'Console Scientifica',
    enabled: false,
    sigla: '…',
    requisito: '…',
    screen: 'scientifica',
  },
};

export default function StationPicker({ preview = false }) {
  const [data, setData] = useState(preview ? PREVIEW_STATION : null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(!preview);

  const load = useCallback(async () => {
    if (preview) {
      setData(PREVIEW_STATION);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await api.stationConsoles();
      setData(res);
    } catch (e) {
      setError(e.network
        ? 'Server non raggiungibile. Controlla il WiFi e riprova.'
        : (e.message || 'Impossibile leggere le console.'));
      setData((prev) => prev || EMPTY);
    } finally {
      setLoading(false);
    }
  }, [preview]);

  useEffect(() => {
    load();
  }, [load]);

  const open = (screen, enabled) => {
    if (!enabled && !error) return;
    if (preview) {
      const params = new URLSearchParams(window.location.search);
      params.set('screen', screen);
      params.set('from', 'station');
      params.set('preview', 'login');
      window.location.search = params.toString();
      return;
    }
    navigateScreen(screen);
  };

  const ing = data?.ingegneria;
  const sci = data?.scientifica;

  return (
    <div className="station-picker">
      <header className="station-picker-head">
        <span className="station-picker-kicker">KOR-35 // STAZIONE</span>
        <h1>Scegli la console</h1>
      </header>
      {loading ? <p className="station-picker-note">Collegamento al server…</p> : null}
      {error ? <p className="station-picker-error">{error}</p> : null}
      <div className="station-picker-grid">
        <ConsoleButton
          title="Ingegneria"
          detail={ing ? `Accesso ${ing.requisito || ing.sigla}` : 'Accesso …'}
          disabled={loading || (!error && ing && !ing.enabled)}
          offLabel={!error && ing && !ing.enabled ? 'Disabilitata nello staff' : ''}
          onClick={() => open('compattatore', !ing || ing.enabled || Boolean(error))}
        />
        <ConsoleButton
          title="Scientifica"
          detail={sci ? `Accesso ${sci.requisito || sci.sigla}` : 'Accesso …'}
          disabled={loading || (!error && sci && !sci.enabled)}
          offLabel={!error && sci && !sci.enabled ? 'Disabilitata nello staff' : ''}
          onClick={() => open('scientifica', !sci || sci.enabled || Boolean(error))}
        />
      </div>
      <footer className="station-picker-foot">
        <span>WiFi bosco: kor35-larp. Se assente, il Pi usa la rete di riserva.</span>
        {error ? (
          <button type="button" className="station-retry" onClick={load}>Riprova</button>
        ) : null}
      </footer>
    </div>
  );
}

function ConsoleButton({ title, detail, disabled, offLabel, onClick }) {
  return (
    <button type="button" className="station-choice" disabled={disabled} onClick={onClick}>
      <span className="station-choice-kicker">CONSOLE</span>
      <span className="station-choice-title">{title}</span>
      <span className="station-choice-detail">{offLabel || detail}</span>
    </button>
  );
}
