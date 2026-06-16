import React, { useCallback, useEffect, useState } from 'react';
import { ImageIcon, Loader, RefreshCw } from 'lucide-react';
import { staffAggiornaMinigiocoBiblioteca, staffGetMinigiocoBiblioteca } from '../../api';

const MinigiocoBibliotecaPanel = ({ onLogout }) => {
  const [data, setData] = useState({ count: 0, target: 100, items: [] });
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setMsg('');
    try {
      const res = await staffGetMinigiocoBiblioteca(onLogout);
      setData(res || { count: 0, target: 100, items: [] });
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
    if (!window.confirm('Scaricare ~100 immagini open license da Openverse? Può richiedere 1–2 minuti.')) {
      return;
    }
    setUpdating(true);
    setMsg('Download in corso… attendere.');
    try {
      const res = await staffAggiornaMinigiocoBiblioteca(data.target || 100, onLogout);
      setMsg(
        res?.ok
          ? `Libreria aggiornata: ${res.count}/${res.target} immagini (${Math.round((res.elapsed_ms || 0) / 1000)}s).`
          : res?.error || 'Aggiornamento fallito.'
      );
      await load();
    } catch (e) {
      const detail =
        e?.data?.error ||
        (Array.isArray(e?.data?.openverse_errors) && e.data.openverse_errors[0]) ||
        (Array.isArray(e?.data?.errors_sample) && e.data.errors_sample[0]);
      setMsg(detail || e.message || 'Errore aggiornamento libreria');
    } finally {
      setUpdating(false);
    }
  };

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
        Immagini CC0 / CC-BY da Openverse. Se un QR non ha immagine dedicata e l&apos;opzione è attiva,
        ne viene scelta una a caso da qui.
      </p>

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
