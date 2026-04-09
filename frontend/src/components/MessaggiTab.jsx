import React, { Fragment, useEffect, memo, useMemo, useState } from 'react';
import { Tab } from '@headlessui/react';
import { useCharacter } from './CharacterContext';
import PlayerMessageTab from './PlayerMessageTab';
import AdminMessageTab from './AdminMessageTab';
import JobRequestsWidget from './JobRequestsWidget'; // <--- 1. Importa il Widget
import { getMessageUnreadCounts } from '../api';
import { Mail } from 'lucide-react';

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const MessaggiTab = ({ onLogout, composeTarget, onComposeTargetConsumed }) => {
  const { selectedCharacterData: char, viewAll, unreadCount, fetchUserMessages, selectedCharacterId, selectCharacter } = useCharacter();
  const [unreadBuckets, setUnreadBuckets] = useState({
    totals: { player: 0, staff: 0, all: 0 },
    by_scope: { player: [], staff: [] },
    by_character: [],
  });
  const [scrollToFirstUnreadNonce, setScrollToFirstUnreadNonce] = useState(0);
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Refresh messaggi quando si apre la tab
  useEffect(() => {
    if (selectedCharacterId) fetchUserMessages(selectedCharacterId);
  }, [selectedCharacterId, fetchUserMessages]);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const data = await getMessageUnreadCounts(onLogout);
        if (!alive) return;
        if (Array.isArray(data)) {
          // Compatibilita con vecchio formato endpoint.
          setUnreadBuckets({
            totals: {
              player: data.reduce((acc, r) => acc + Number(r?.unread_count || 0), 0),
              staff: 0,
              all: data.reduce((acc, r) => acc + Number(r?.unread_count || 0), 0),
            },
            by_scope: { player: data, staff: [] },
            by_character: data,
          });
        } else {
          const payload = data || {};
          setUnreadBuckets({
            totals: payload.totals || { player: 0, staff: 0, all: 0 },
            by_scope: payload.by_scope || { player: [], staff: [] },
            by_character: payload.by_character || [],
          });
        }
      } catch (e) {
        if (!alive) return;
        setUnreadBuckets({
          totals: { player: 0, staff: 0, all: 0 },
          by_scope: { player: [], staff: [] },
          by_character: [],
        });
      }
    };
    load();
    const id = window.setInterval(load, 45000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [onLogout, selectedCharacterId, unreadCount]);

  const unreadList = useMemo(() => {
    const list = Array.isArray(unreadBuckets?.by_character) ? unreadBuckets.by_character : [];
    return list.filter((r) => Number(r.unread_count || 0) > 0);
  }, [unreadBuckets]);

  const unreadPlayerList = useMemo(() => {
    const list = Array.isArray(unreadBuckets?.by_scope?.player) ? unreadBuckets.by_scope.player : [];
    return list.filter((r) => Number(r.unread_count || 0) > 0);
  }, [unreadBuckets]);

  const unreadStaffList = useMemo(() => {
    const list = Array.isArray(unreadBuckets?.by_scope?.staff) ? unreadBuckets.by_scope.staff : [];
    return list.filter((r) => Number(r.unread_count || 0) > 0);
  }, [unreadBuckets]);

  if (!char) return <div className="p-4 text-gray-400">Caricamento...</div>;

  // Mostra tab Admin solo se staff e non in view-all
  const showAdminTab = char.is_staff && !viewAll;
  const staffUnreadTotal = Number(unreadBuckets?.totals?.staff || 0);

  return (
    <div className="w-full p-2 sm:p-4 pb-20">
      
      {/* --- 2. INSERISCI QUI IL WIDGET LAVORI --- */}
      {/* Apparirà sopra le tab, visibile subito se ci sono richieste */}
      <JobRequestsWidget characterId={char.id} />

      {unreadList.length > 0 && (
        <div className="mb-4 rounded-xl border border-amber-400/20 bg-gray-900/70 p-3">
          <div className="flex items-center gap-2 text-sm font-bold text-amber-200 mb-2">
            <Mail size={16} /> Messaggi da leggere
          </div>
          {unreadPlayerList.length > 0 && (
            <div className="mb-3">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-100/80">
                Giocatore
              </div>
              <div className="flex flex-wrap gap-2">
                {unreadPlayerList.map((r) => (
                  <button
                    key={`unread-player-${r.personaggio_id}`}
                    type="button"
                    onClick={async () => {
                      const id = r.personaggio_id;
                      selectCharacter(String(id));
                      await fetchUserMessages(String(id));
                      setScrollToFirstUnreadNonce((n) => n + 1);
                    }}
                    className={`px-3 py-2 rounded-lg border text-sm font-semibold inline-flex items-center gap-2 ${
                      String(r.personaggio_id) === String(selectedCharacterId)
                        ? 'bg-amber-900/30 border-amber-300/40 text-amber-100'
                        : 'bg-gray-800 border-gray-700 text-gray-200 hover:bg-gray-700'
                    }`}
                    title="Apri inbox personaggio"
                  >
                    <span className="truncate max-w-40">{r.personaggio_nome || `PG ${r.personaggio_id}`}</span>
                    <span className="min-w-6 h-6 px-2 rounded-full bg-red-600 text-white text-xs leading-6 text-center">
                      {Number(r.unread_count) > 99 ? '99+' : Number(r.unread_count)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {unreadStaffList.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-200/80">
                Staff
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (!showAdminTab) return;
                    setActiveTabIndex(1);
                  }}
                  className={`px-3 py-2 rounded-lg border text-sm font-semibold inline-flex items-center gap-2 ${
                    showAdminTab ? 'bg-red-900/30 border-red-300/40 text-red-100 hover:bg-red-900/40' : 'bg-gray-800 border-gray-700 text-gray-500'
                  }`}
                  title={showAdminTab ? 'Apri Admin Area' : 'Admin Area non disponibile'}
                  disabled={!showAdminTab}
                >
                  <span className="truncate max-w-40">Admin Area</span>
                  <span className="min-w-6 h-6 px-2 rounded-full bg-red-700 text-white text-xs leading-6 text-center">
                    {staffUnreadTotal > 99 ? '99+' : staffUnreadTotal}
                  </span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <Tab.Group selectedIndex={activeTabIndex} onChange={setActiveTabIndex}>
        <Tab.List className="flex space-x-1 rounded-xl bg-gray-800 p-1 mb-4">
          <Tab as={Fragment}>
            {({ selected }) => (
              <button className={classNames(
                  'w-full rounded-lg py-2.5 text-sm font-medium leading-5 relative transition-all',
                  'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-gray-800 ring-white ring-opacity-60',
                  selected ? 'bg-indigo-600 text-white shadow' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              )}>
                Ricevuti
                {unreadCount > 0 && (
                    <span className="absolute top-1 right-2 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-red-600 rounded-full shadow-sm animate-pulse">
                        {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                )}
              </button>
            )}
          </Tab>
          
          {showAdminTab && (
            <Tab as={Fragment}>
              {({ selected }) => (
                <button className={classNames(
                    'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                    'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-gray-800 ring-white ring-opacity-60',
                    selected ? 'bg-red-700 text-white shadow' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                )}>
                  Admin Area
                  {staffUnreadTotal > 0 && (
                    <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-red-600 rounded-full shadow-sm">
                      {staffUnreadTotal > 99 ? '99+' : staffUnreadTotal}
                    </span>
                  )}
                </button>
              )}
            </Tab>
          )}
        </Tab.List>

        <Tab.Panels>
          <Tab.Panel className="focus:outline-none animate-fadeIn">
            {/* Passiamo le props necessarie al componente figlio esistente */}
            <PlayerMessageTab
              onLogout={onLogout}
              composeTarget={composeTarget}
              onComposeTargetConsumed={onComposeTargetConsumed}
              scrollToFirstUnreadNonce={scrollToFirstUnreadNonce}
            />
          </Tab.Panel>
          
          {showAdminTab && (
            <Tab.Panel className="focus:outline-none animate-fadeIn">
              <AdminMessageTab onLogout={onLogout} />
            </Tab.Panel>
          )}
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
};

export default memo(MessaggiTab);