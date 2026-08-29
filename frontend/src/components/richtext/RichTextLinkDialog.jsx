import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link2, Search, X } from 'lucide-react';
import { getWikiMenu } from '../../api';

/** Appiattisce l'albero del menu wiki in un elenco di pagine linkabili. */
const flattenMenuPages = (menuItems = []) => {
    const pages = [];
    const traverse = (items) => {
        (items || []).forEach((item) => {
            if (item?.slug) {
                pages.push({ titolo: item.titolo, slug: item.slug, path: `/regolamento/${item.slug}` });
            }
            if (item?.children?.length) traverse(item.children);
        });
    };
    traverse(menuItems);
    return pages;
};

/**
 * Dialog di inserimento link: ricerca fra le pagine wiki oppure URL manuale.
 * A schermo pieno su smartphone, centrato su desktop.
 */
const RichTextLinkDialog = ({ open, initialText = '', onCancel, onConfirm }) => {
    const [text, setText] = useState('');
    const [url, setUrl] = useState('');
    const [filter, setFilter] = useState('');
    const [pages, setPages] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!open) return;
        setText(initialText || '');
        setUrl('');
        setFilter('');
    }, [open, initialText]);

    useEffect(() => {
        if (!open) return undefined;

        let cancelled = false;
        setLoading(true);
        getWikiMenu()
            .then((menu) => {
                if (!cancelled) setPages(flattenMenuPages(menu));
            })
            .catch((error) => {
                console.error('Errore caricamento pagine wiki:', error);
                if (!cancelled) setPages([]);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [open]);

    useEffect(() => {
        if (!open) return undefined;
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') onCancel();
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [open, onCancel]);

    const filteredPages = useMemo(() => {
        const needle = filter.trim().toLowerCase();
        if (!needle) return pages;
        return pages.filter(
            (page) => page.titolo?.toLowerCase().includes(needle) || page.slug?.toLowerCase().includes(needle)
        );
    }, [pages, filter]);

    const selectPage = useCallback((page) => {
        setUrl(page.path);
        setText((current) => current.trim() || page.titolo || '');
    }, []);

    const submit = useCallback(() => {
        const finalText = text.trim();
        const finalUrl = url.trim();
        if (!finalUrl) return;
        onConfirm({ text: finalText || finalUrl, url: finalUrl });
    }, [text, url, onConfirm]);

    if (!open) return null;

    return (
        <div
            className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center bg-black/70 p-0 sm:p-4"
            onMouseDown={(event) => {
                if (event.target === event.currentTarget) onCancel();
            }}
        >
            <div className="flex flex-col w-full sm:max-w-2xl h-[92vh] sm:h-auto sm:max-h-[85vh] bg-gray-800 border border-gray-600 sm:rounded-xl shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-700 shrink-0">
                    <h3 className="text-base font-semibold text-gray-100 flex items-center gap-2">
                        <Link2 size={18} className="text-indigo-400" />
                        Inserisci link
                    </h3>
                    <button
                        type="button"
                        onClick={onCancel}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10"
                        aria-label="Chiudi"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-4 custom-scrollbar">
                    <div>
                        <label className="block text-xs font-bold uppercase tracking-wide text-gray-400 mb-1">
                            Testo del link
                        </label>
                        <input
                            type="text"
                            value={text}
                            onChange={(event) => setText(event.target.value)}
                            placeholder="es. Guida alle Classi"
                            className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-bold uppercase tracking-wide text-gray-400 mb-1">
                            Pagina wiki
                        </label>
                        <div className="relative mb-2">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                            <input
                                type="text"
                                value={filter}
                                onChange={(event) => setFilter(event.target.value)}
                                placeholder="Cerca pagina…"
                                className="w-full pl-9 pr-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 outline-none"
                            />
                        </div>

                        <div className="border border-gray-600 rounded-md bg-gray-900 max-h-56 overflow-y-auto custom-scrollbar">
                            {loading ? (
                                <div className="p-4 text-center text-sm text-gray-400">Caricamento pagine…</div>
                            ) : filteredPages.length === 0 ? (
                                <div className="p-4 text-center text-sm text-gray-400">Nessuna pagina trovata</div>
                            ) : (
                                <div className="divide-y divide-gray-700/70">
                                    {filteredPages.map((page) => (
                                        <button
                                            key={page.slug}
                                            type="button"
                                            onClick={() => selectPage(page)}
                                            className={`w-full text-left px-3 py-2.5 transition-colors ${
                                                url === page.path
                                                    ? 'bg-indigo-600/25 border-l-4 border-indigo-500'
                                                    : 'hover:bg-gray-800'
                                            }`}
                                        >
                                            <div className="text-sm font-medium text-gray-100">{page.titolo}</div>
                                            <div className="text-[11px] text-gray-500 mt-0.5">{page.path}</div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-bold uppercase tracking-wide text-gray-400 mb-1">
                            Oppure URL manuale
                        </label>
                        <input
                            type="text"
                            value={url}
                            onChange={(event) => setUrl(event.target.value)}
                            placeholder="/regolamento/pagina, #sezione oppure https://…"
                            className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 outline-none"
                        />
                    </div>
                </div>

                <div className="flex gap-2 justify-end px-4 py-3 border-t border-gray-700 shrink-0">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-4 py-2 rounded-md bg-gray-700 text-gray-200 hover:bg-gray-600 transition-colors"
                    >
                        Annulla
                    </button>
                    <button
                        type="button"
                        onClick={submit}
                        disabled={!url.trim()}
                        className="px-4 py-2 rounded-md bg-indigo-600 text-white font-semibold hover:bg-indigo-500 transition-colors disabled:opacity-50 inline-flex items-center gap-2"
                    >
                        <Link2 size={16} />
                        Inserisci
                    </button>
                </div>
            </div>
        </div>
    );
};

export default RichTextLinkDialog;
