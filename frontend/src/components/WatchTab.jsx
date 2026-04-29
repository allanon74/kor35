import React, { useState, useEffect, useMemo } from 'react';
import { Watch } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { watchPairConfirm, watchDisconnect, watchWearManifest } from '../api';

/** Allineato al default backend `WATCH_WEAR_APK_PATH` (nginx: react_build/watch-apps/...). */
const WEAR_DEFAULT_APK_PATH = '/watch-apps/wearos-kor35/app-release.apk';

/** URL assoluto per download APK: evita href solo-path se il manifest espone path relativo. */
function wearApkAbsoluteUrl(apkUrl) {
    if (!apkUrl || typeof apkUrl !== 'string') return '';
    const u = apkUrl.trim();
    if (/^https?:\/\//i.test(u)) return u;
    if (typeof window === 'undefined') return u;
    return u.startsWith('/') ? `${window.location.origin}${u}` : `${window.location.origin}/${u}`;
}

/**
 * Scheda dedicata fuori dal contesto IN_GAME (Game / Scheda): pairing Wear OS, APK e disconnessione device.
 */
const WatchTab = () => {
    const { selectedCharacterData: char, personaggiList, refreshCharacterData, onLogout } = useCharacter();
    const [pairCodeInput, setPairCodeInput] = useState('');
    const [pairTransportMode, setPairTransportMode] = useState('WIFI');
    const [watchBusy, setWatchBusy] = useState(false);
    const [wearManifest, setWearManifest] = useState(null);

    const listWatchRow = useMemo(() => {
        if (!char?.id) return null;
        return (personaggiList || []).find((p) => String(p.id) === String(char.id));
    }, [personaggiList, char?.id]);

    const watchEnabledEffective = useMemo(() => {
        if (!char) return false;
        const v = char.watch_enabled;
        if (v !== undefined && v !== null) return !!v;
        return !!listWatchRow?.watch_enabled;
    }, [char, listWatchRow]);

    useEffect(() => {
        let mounted = true;
        const loadWearManifest = async () => {
            if (!char?.id || !watchEnabledEffective) {
                if (mounted) setWearManifest(null);
                return;
            }
            try {
                const data = await watchWearManifest(char.id, onLogout);
                if (!mounted) return;
                setWearManifest(data?.enabled ? data : null);
            } catch {
                if (mounted) setWearManifest(null);
            }
        };
        loadWearManifest();
        return () => {
            mounted = false;
        };
    }, [char?.id, watchEnabledEffective, onLogout]);

    if (!char) {
        return (
            <div className="flex h-full min-h-[40vh] flex-col items-center justify-center gap-3 px-4 text-center text-gray-400">
                <Watch className="h-12 w-12 opacity-30" aria-hidden />
                <p className="text-sm font-medium">Caricamento personaggio…</p>
            </div>
        );
    }

    if (!watchEnabledEffective) {
        return (
            <div className="animate-fadeIn space-y-3 px-3 py-6 text-gray-200">
                <div className="flex items-center gap-2 text-sky-400">
                    <Watch className="h-6 w-6 shrink-0" aria-hidden />
                    <h1 className="text-sm font-black uppercase tracking-widest">Smartwatch</h1>
                </div>
                <p className="text-sm text-gray-400 leading-relaxed">
                    Per questo personaggio lo smartwatch non è abilitato. Chiedi allo staff di attivare il flag sulla
                    scheda di gestione.
                </p>
            </div>
        );
    }

    const watchBinding = char.watch_binding || null;

    const handleWatchPair = async () => {
        if (!pairCodeInput.trim()) {
            alert('Inserisci il codice del device in attesa.');
            return;
        }
        setWatchBusy(true);
        try {
            await watchPairConfirm(char.id, pairCodeInput, pairTransportMode, onLogout);
            setPairCodeInput('');
            await refreshCharacterData();
        } catch (e) {
            alert(e?.message || 'Errore pairing smartwatch.');
        } finally {
            setWatchBusy(false);
        }
    };

    const handleWatchDisconnect = async () => {
        setWatchBusy(true);
        try {
            await watchDisconnect(char.id, onLogout);
            await refreshCharacterData();
        } catch (e) {
            alert(e?.message || 'Errore disconnessione smartwatch.');
        } finally {
            setWatchBusy(false);
        }
    };

    return (
        <div className="animate-fadeIn space-y-5 px-3 py-4 pb-24 text-gray-100">
            <header className="space-y-1">
                <div className="flex items-center gap-2 text-sky-400">
                    <Watch className="h-6 w-6 shrink-0" aria-hidden />
                    <h1 className="text-sm font-black uppercase tracking-widest">Smartwatch (Wear OS)</h1>
                </div>
                <p className="text-[11px] text-gray-500 leading-snug">
                    Pairing e connessione al personaggio selezionato: fuori dalla scheda di gioco in campo.
                </p>
            </header>

            <div className="rounded-xl border border-sky-800/50 bg-gray-900/70 p-4 space-y-3">
                <p className="text-[11px] text-gray-400">
                    Il pairing con codice funziona in ogni ambiente. Il manifest API (versione + URL ufficiale) richiede
                    backend con <span className="font-mono">WATCH_WEAR_ENABLED</span> e risposta 200; il file APK va
                    comunque copiato sul volume nginx (es. rsync da CI).
                </p>
                {wearManifest?.apk_url ? (
                    <div className="rounded-lg border border-gray-700 bg-gray-800/60 p-3 text-xs text-gray-300">
                        App Wear OS (v{wearManifest.version || 'n/d'}). Installa dal telefono Android collegato all&apos;orologio.
                        <div className="mt-2">
                            <a
                                href={wearApkAbsoluteUrl(wearManifest.apk_url)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex rounded bg-indigo-900/70 px-3 py-2 text-xs font-bold hover:bg-indigo-800"
                            >
                                Scarica app Wear OS
                            </a>
                        </div>
                    </div>
                ) : (
                    <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 space-y-2 text-[11px] text-gray-300">
                        <p className="text-amber-200/90">
                            Manifest Wear non disponibile da questo host (errore di rete, 404 o{' '}
                            <span className="font-mono">WATCH_WEAR_ENABLED=false</span> nel backend). Il pairing qui
                            sotto funziona comunque.
                        </p>
                        <p className="text-gray-400">
                            Puoi provare il download diretto sullo stesso host: ha successo solo se l&apos;APK è stato
                            pubblicato sotto nginx (<span className="font-mono">extra/ota-artifacts/…</span> → rsync in
                            deploy).
                        </p>
                        <a
                            href={wearApkAbsoluteUrl(WEAR_DEFAULT_APK_PATH)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex rounded bg-indigo-900/70 px-3 py-2 text-xs font-bold text-white hover:bg-indigo-800"
                        >
                            Scarica APK Wear OS (link diretto)
                        </a>
                    </div>
                )}

                {watchBinding ? (
                    <div className="space-y-2 border-t border-gray-700/80 pt-3">
                        <p className="text-xs text-gray-300">
                            Connesso:{' '}
                            <span className="font-mono text-white">{watchBinding.device_id}</span>
                            <span className="text-gray-500"> · </span>
                            Trasporto: {watchBinding.transport_mode}
                        </p>
                        <button
                            type="button"
                            disabled={watchBusy}
                            onClick={handleWatchDisconnect}
                            className="rounded bg-red-900/60 px-3 py-2 text-xs font-bold hover:bg-red-800 disabled:opacity-50"
                        >
                            Disconnetti dispositivo
                        </button>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2 border-t border-gray-700/80 pt-3 md:flex-row md:flex-wrap">
                        <input
                            value={pairCodeInput}
                            onChange={(e) => setPairCodeInput(e.target.value.toUpperCase().slice(0, 12))}
                            placeholder="Codice device (es. A7K9Q2)"
                            className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 font-mono text-xs text-white md:max-w-xs"
                        />
                        <select
                            value={pairTransportMode}
                            onChange={(e) => setPairTransportMode(e.target.value)}
                            className="rounded border border-gray-600 bg-gray-800 px-2 py-2 text-xs md:w-auto"
                        >
                            <option value="WIFI">Wi-Fi diretto</option>
                            <option value="BT_BRIDGE">Bluetooth bridge</option>
                        </select>
                        <button
                            type="button"
                            disabled={watchBusy || !pairCodeInput.trim()}
                            onClick={handleWatchPair}
                            className="rounded bg-emerald-900/60 px-3 py-2 text-xs font-bold hover:bg-emerald-800 disabled:opacity-50"
                        >
                            Connetti device al personaggio
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default WatchTab;
