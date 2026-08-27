import React, { useCallback, useEffect, useState, memo } from 'react';
import { RefreshCw, RotateCcw, Trash2, Skull } from 'lucide-react';
import {
  staffGetPersonaggiEliminati,
  staffRestorePersonaggioEliminato,
  staffHardDeletePersonaggioEliminato,
} from '../../api';
import {
  StaffToolPageTitle,
  StaffToolShell,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';
import MasterGenericList from './MasterGenericList';

const formatDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('it-IT');
  } catch {
    return iso;
  }
};

const PersonaggiEliminatiManager = ({ onLogout }) => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await staffGetPersonaggiEliminati(onLogout);
      setRows(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e?.message || 'Errore caricamento');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSelected = async () => {
    if (!confirm) return;
    const { kind, row } = confirm;
    setConfirm(null);
    setBusyId(row.id);
    try {
      if (kind === 'restore') {
        await staffRestorePersonaggioEliminato(row.id, onLogout);
      } else {
        await staffHardDeletePersonaggioEliminato(row.id, onLogout);
      }
      await load();
    } catch (e) {
      alert(e?.message || 'Operazione fallita');
    } finally {
      setBusyId(null);
    }
  };

  if (loading && rows.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400">
        <RefreshCw className="mr-2 h-8 w-8 animate-spin" /> Caricamento…
      </div>
    );
  }

  return (
    <StaffToolShell maxWidth="6xl">
      <StaffToolPageTitle
        icon={<Skull className="h-7 w-7 text-red-400" />}
        title="Personaggi eliminati"
        description="Archivio soft-delete: i dati restano nel database finché non li elimini definitivamente."
        actions={
        <button type="button" onClick={load} className={staffSecondaryBtnClass}>
          <RefreshCw size={16} /> Aggiorna
        </button>
        }
      />

      {error && (
        <div className="mb-4 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {rows.length === 0 && !loading ? (
        <p className="text-sm text-gray-500">Nessun personaggio archiviato per la campagna attiva.</p>
      ) : (
        <MasterGenericList
          title="Archivio"
          items={rows}
          fill={false}
          persistKey="staff-personaggi-eliminati"
          loading={loading}
          emptyMessage="Nessun personaggio archiviato."
          getSearchText={(row) => [row.nome, row.proprietario_nome, row.proprietario_username, row.campagna_nome].filter(Boolean).join(' ')}
          extraRowActions={(row) => (
            <>
              <button
                type="button"
                disabled={busyId === row.id}
                onClick={() => setConfirm({ kind: 'restore', row })}
                className="inline-flex items-center gap-1 rounded-lg border border-emerald-700 bg-emerald-950/50 px-2.5 py-1.5 text-xs font-bold text-emerald-300 hover:bg-emerald-900 disabled:opacity-50"
                title="Ripristina personaggio"
              >
                <RotateCcw size={14} /> Ripristina
              </button>
              <button
                type="button"
                disabled={busyId === row.id}
                onClick={() => setConfirm({ kind: 'hard', row })}
                className="inline-flex items-center gap-1 rounded-lg border border-red-800 bg-red-950/60 px-2.5 py-1.5 text-xs font-bold text-red-300 hover:bg-red-900 disabled:opacity-50"
                title="Elimina definitivamente dal database"
              >
                <Trash2 size={14} /> Definitivo
              </button>
            </>
          )}
          columns={[
            { key: 'nome', header: 'Nome', getSortValue: (row) => row.nome || '', render: (row) => <span className="font-semibold text-white">{row.nome}</span> },
            {
              key: 'proprietario',
              header: 'Proprietario',
              getSortValue: (row) => row.proprietario_nome || row.proprietario_username || '',
              render: (row) => row.proprietario_nome || row.proprietario_username || '—',
            },
            { key: 'campagna', header: 'Campagna', getSortValue: (row) => row.campagna_nome || '', render: (row) => row.campagna_nome || '—' },
            { key: 'tipologia', header: 'Tipologia', getSortValue: (row) => row.tipologia_nome || '', render: (row) => row.tipologia_nome || '—' },
            {
              key: 'eliminato',
              header: 'Eliminato il',
              getSortValue: (row) => row.eliminato_at || '',
              render: (row) => <span className="font-mono text-xs text-red-300/90">{formatDate(row.eliminato_at)}</span>,
            },
          ]}
        />
      )}

      {confirm && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-2xl border border-gray-600 bg-gray-800 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white">
              {confirm.kind === 'restore' ? 'Ripristinare personaggio' : 'Eliminazione definitiva'}
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-gray-300">
              {confirm.kind === 'restore' ? (
                <>
                  Ripristinare <strong className="text-white">«{confirm.row.nome}»</strong>?
                  Tornerà visibile nell&apos;app come prima dell&apos;archiviazione.
                </>
              ) : (
                <>
                  Eliminare definitivamente <strong className="text-white">«{confirm.row.nome}»</strong> dal database?
                  Questa azione è irreversibile: scheda, inventario, social e dati collegati verranno rimossi.
                </>
              )}
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirm(null)}
                className="rounded-lg border border-gray-600 bg-gray-700 px-4 py-2 text-sm font-bold text-gray-200 hover:bg-gray-600"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={() => void handleSelected()}
                className={`rounded-lg px-4 py-2 text-sm font-bold text-white ${
                  confirm.kind === 'restore' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-red-600 hover:bg-red-500'
                }`}
              >
                Conferma
              </button>
            </div>
          </div>
        </div>
      )}
    </StaffToolShell>
  );
};

export default memo(PersonaggiEliminatiManager);
