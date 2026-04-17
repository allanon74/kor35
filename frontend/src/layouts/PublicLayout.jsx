import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useCharacter } from '../components/CharacterContext';
import { getWikiMenu } from '../api';
import WikiPageEditorModal from '../components/wiki/WikiPageEditorModal';
import { 
    Menu, X, Search, 
    Folder, FolderOpen, FileText, 
    ChevronRight, ChevronDown, Plus,
    Lock, EyeOff 
} from 'lucide-react';

export default function PublicLayout({ token }) {
  // --- STATI GENERALI ---
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isEditorOpen, setEditorOpen] = useState(false);
  const [newParentId, setNewParentId] = useState(null);
  
  // --- STATI DATI & RICERCA ---
  const [flatMenu, setFlatMenu] = useState([]); 
  const [menuTree, setMenuTree] = useState([]); 
  const [searchTerm, setSearchTerm] = useState(''); 
  const [loadingMenu, setLoadingMenu] = useState(true);
  
  // Gestione apertura nodi (Set di ID)
  const [openNodes, setOpenNodes] = useState(new Set());
  
  // NUOVO: Stato per nascondere bozze/staff (per admin)
  const [hideAdminContent, setHideAdminContent] = useState(() => {
    return localStorage.getItem('wiki_hide_admin_content') === 'true';
  });

  const { character, isCampaignRedactor, isCampaignMaster, isAdmin } = useCharacter();
  const canEdit = isCampaignRedactor || isCampaignMaster || isAdmin;
  const location = useLocation();

  // --- HELPER: COSTRUZIONE ALBERO E ORDINAMENTO ---
  const buildTree = (items) => {
    if (!Array.isArray(items)) return [];
    const map = {};
    const roots = [];
    
    items.forEach((item) => { map[item.id] = { ...item, children: [] }; });

    items.forEach((item) => {
      if (item.parent && map[item.parent]) {
        // CORREZIONE: Attacca sempre al parent, anche se non pubblico
        map[item.parent].children.push(map[item.id]);
      } else if (!item.parent) {
        // Solo i nodi senza parent vanno nei roots
        roots.push(map[item.id]);
      }
      // Se parent non esiste in map, il nodo viene ignorato (non finisce in root)
    });

    // Ordinamento: 1. Ordine (numerico), 2. Titolo (Alfabetico)
    const sortRecursive = (nodes) => {
        nodes.sort((a, b) => {
            const ordA = a.ordine !== undefined ? a.ordine : 999;
            const ordB = b.ordine !== undefined ? b.ordine : 999;
            if (ordA !== ordB) return ordA - ordB;
            return (a.titolo || "").localeCompare(b.titolo || "");
        });
        nodes.forEach(node => {
            if (node.children?.length > 0) sortRecursive(node.children);
        });
    };

    sortRecursive(roots);
    
    // NUOVO: Filtro per nascondere bozze/staff se l'admin lo desidera
    const filterTree = (nodes) => {
      return nodes.filter(node => {
        // Se hideAdminContent è attivo e l'utente è admin, nascondi bozze e staff-only
        if (hideAdminContent && canEdit) {
          if (node.public === false || node.visibile_solo_staff === true) {
            return false;
          }
        }
        
        // Filtra ricorsivamente i figli
        if (node.children?.length > 0) {
          node.children = filterTree(node.children);
        }
        
        return true;
      });
    };
    
    return filterTree(roots);
  };

  // --- 1. CARICAMENTO DATI ---
  useEffect(() => {
    const fetchMenu = async () => {
      setLoadingMenu(true);
      try {
        // L'API (src/api.js) ora decide se mandare il token.
        // Il Backend filtra i dati. Se riceviamo dati, li mostriamo.
        const rawList = await getWikiMenu();
        
        setFlatMenu(rawList); 
      } catch (error) {
        console.error("Errore caricamento menu:", error);
      } finally {
        setLoadingMenu(false);
      }
    };
    fetchMenu();
  }, [token]); // Ricarica se cambia il token (login/logout)
  
  // --- RICALCOLO ALBERO quando cambiano dati o filtri ---
  useEffect(() => {
    if (flatMenu.length > 0) {
      setMenuTree(buildTree(flatMenu));
    }
  }, [flatMenu, hideAdminContent, canEdit]);

  // --- 2. LOGICA AUTO-EXPAND (Apre solo il percorso corrente e primi figli) ---
  useEffect(() => {
    if (flatMenu.length === 0) return;

    const currentSlug = location.pathname.startsWith('/regolamento/') 
        ? location.pathname.split('/')[2] 
        : 'home';

    const currentPage = flatMenu.find(p => p.slug === currentSlug);
    
    if (currentPage) {
        const parents = getAllParents(currentPage.id, flatMenu);
        
        // NUOVO: Apri solo i genitori e la pagina corrente (se ha figli)
        const nodesToOpen = new Set(parents);
        
        // Se la pagina corrente ha figli, aprila
        const hasChildren = flatMenu.some(p => p.parent === currentPage.id);
        if (hasChildren) {
            nodesToOpen.add(currentPage.id);
        }
        
        setOpenNodes(nodesToOpen);
    } else {
        // Se non troviamo la pagina, chiudi tutto
        setOpenNodes(new Set());
    }
  }, [location.pathname, flatMenu]);

  const getAllParents = (nodeId, allItems) => {
      const parents = [];
      let current = allItems.find(i => i.id === nodeId);
      while (current && current.parent) {
          parents.push(current.parent);
          current = allItems.find(i => i.id === current.parent);
      }
      return parents;
  };

  const toggleNode = (id) => {
      setOpenNodes(prev => {
          const next = new Set(prev);
          if (next.has(id)) next.delete(id);
          else next.add(id);
          return next;
      });
  };

  // --- HELPER NAVIGAZIONE ---
  const getCurrentPageId = () => {
      const path = location.pathname;
      let currentSlug = 'home';
      if (path.startsWith('/regolamento/')) currentSlug = path.split('/')[2];
      const page = flatMenu.find(p => p.slug === currentSlug);
      return page ? page.id : null;
  };

  const handleCreateRoot = () => { setNewParentId(null); setEditorOpen(true); };
  const handleCreateNested = () => { setNewParentId(getCurrentPageId()); setEditorOpen(true); };

  // --- COMPONENTE VOCE MENU (STILE MODERNO A BLOCCHI) ---
  const WikiSidebarItem = ({ item, level = 0 }) => {
    const hasChildren = item.children && item.children.length > 0;
    const isActive = location.pathname.includes(item.slug) || (item.slug === 'home' && location.pathname === '/');
    const isOpen = openNodes.has(item.id);
    
    // Flag di stato
    const isDraft = item.public === false;
    const isStaffOnly = item.visibile_solo_staff === true;

    return (
      <li className="mb-1.5 select-none">
        <div 
            className={`
                group flex items-center gap-2
                py-2.5 px-3 rounded-lg transition-all duration-200
                ${isActive 
                    ? 'bg-red-900 text-white shadow-lg' 
                    : 'text-gray-300 hover:bg-gray-700/60 hover:text-white'
                }
                ${isDraft ? 'border-l-4 border-yellow-500 bg-gray-800/50' : ''}
                ${!isDraft && isStaffOnly ? 'border-l-4 border-indigo-500 bg-gray-800/50' : ''}
            `}
            style={{ marginLeft: `${level * 12}px` }}
        >
          {/* NUOVO: Pulsante Espansione PIÙ EVIDENTE (Solo se ha figli) */}
          {hasChildren && (
            <button 
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleNode(item.id); }}
                className={`
                    shrink-0 w-7 h-7 flex items-center justify-center rounded-md transition-all
                    ${isActive 
                        ? 'bg-red-800 hover:bg-red-700 text-white' 
                        : 'bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white'
                    }
                    ${isOpen ? 'rotate-0' : ''}
                `}
                aria-label={isOpen ? 'Chiudi sottosezioni' : 'Apri sottosezioni'}
            >
                {isOpen ? <ChevronDown size={16} strokeWidth={2.5} /> : <ChevronRight size={16} strokeWidth={2.5} />}
            </button>
          )}
          
          {/* Se non ha figli, spazio vuoto per allineamento */}
          {!hasChildren && <div className="w-7 shrink-0"></div>}

          {/* Link Pagina */}
          <Link 
            to={item.slug === 'home' ? '/' : `/regolamento/${item.slug}`}
            className="flex-1 flex items-center gap-2.5 truncate min-w-0"
            onClick={() => setSidebarOpen(false)}
          >
             {/* Icona Cartella/File */}
             {hasChildren 
                ? (isOpen 
                    ? <FolderOpen size={18} className={`shrink-0 ${isActive ? "text-yellow-300" : "text-yellow-500"}`} /> 
                    : <Folder size={18} className={`shrink-0 ${isActive ? "text-yellow-300" : "text-yellow-500"}`} />)
                : <FileText size={17} className={`shrink-0 ${isActive ? "text-red-200" : "text-gray-500"}`} />
             }
             
             <div className="flex flex-col min-w-0 flex-1">
                 <span className={`truncate font-medium text-sm leading-tight ${isDraft ? 'italic text-yellow-400' : ''} ${!isDraft && isStaffOnly ? 'text-indigo-300' : ''}`}>
                    {item.titolo}
                 </span>
                 
                 {/* Badges Visivi */}
                 {(isDraft || isStaffOnly) && (
                   <div className="flex gap-1 mt-1">
                      {isDraft && (
                          <span className="text-[9px] uppercase bg-yellow-600 text-black px-1.5 py-0.5 rounded font-bold flex items-center gap-1 w-fit">
                              <EyeOff size={8}/> Bozza
                          </span>
                      )}
                      {isStaffOnly && (
                          <span className="text-[9px] uppercase bg-indigo-600 text-white px-1.5 py-0.5 rounded font-bold flex items-center gap-1 w-fit">
                              <Lock size={8}/> Staff
                          </span>
                      )}
                   </div>
                 )}
             </div>
          </Link>
        </div>

        {/* Rendering Figli */}
        {hasChildren && isOpen && (
            <ul className="mt-1 relative">
                {/* Linea guida verticale migliorata */}
                <div 
                    className="absolute top-0 bottom-0 w-0.5 bg-linear-to-b from-gray-700 to-transparent rounded-full" 
                    style={{ left: `${(level * 12) + 14}px` }} 
                />
                {item.children.map(child => (
                    <WikiSidebarItem key={child.id} item={child} level={level + 1} />
                ))}
            </ul>
        )}
      </li>
    );
  };

  // --- RENDER LAYOUT ---
  return (
    <>
      {/* Stili Custom per Scrollbar */}
      <style>{`
        nav::-webkit-scrollbar {
          width: 6px;
        }
        nav::-webkit-scrollbar-track {
          background: transparent;
        }
        nav::-webkit-scrollbar-thumb {
          background: #374151;
          border-radius: 3px;
        }
        nav::-webkit-scrollbar-thumb:hover {
          background: #4b5563;
        }
      `}</style>
      
      <div className="flex flex-col h-screen bg-gray-100 text-gray-900 font-sans overflow-hidden">
      
      {/* HEADER */}
      <header className="bg-red-900 text-white shadow-md flex items-center justify-between px-4 py-3 z-20 shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="md:hidden p-1 hover:bg-red-800 rounded focus:outline-none">
            {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
          
          <Link to={token ? "/app/start" : "/"} className="text-xl font-bold tracking-wider flex items-center gap-2" title={token ? "Torna alla splash page" : "Vai alla home wiki"}>
            <img src="/Logo Kor-AD_Trasp.png" alt="Logo" className="h-8" />
            <span className="hidden xs:inline">KOR35 WIKI</span>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {token ? (
            <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block leading-tight">
                    <div className="font-bold text-sm">{character?.nome}</div>
                    <div className="text-xs text-red-200">{canEdit ? 'Staff' : 'Giocatore'}</div>
                </div>
                <Link to="/app" className="bg-white text-red-900 px-3 py-1.5 rounded font-bold hover:bg-gray-100 transition text-sm flex items-center gap-2 shadow-sm">
                  <span>🎮</span> <span className="hidden sm:inline">Entra nel Gioco</span>
                </Link>
                <Link to="/app/social" className="bg-red-700 text-white px-3 py-1.5 rounded font-bold hover:bg-red-600 transition text-sm flex items-center gap-2 shadow-sm">
                  <span>✨</span> <span className="hidden sm:inline">InstaFame</span>
                </Link>
            </div>
          ) : (
             <div className="flex items-center gap-2">
               {!location.pathname.includes('login') && (
                 <Link to="/login" className="bg-red-700 hover:bg-red-600 px-4 py-2 rounded text-white transition text-sm font-medium">
                    Login
                 </Link>
               )}
               <Link to="/app/social" className="bg-red-700 text-white px-3 py-1.5 rounded font-bold hover:bg-red-600 transition text-sm flex items-center gap-2 shadow-sm">
                 <span>✨</span> <span className="hidden sm:inline">InstaFame</span>
               </Link>
             </div>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden relative">
        
        {/* SIDEBAR - Migliorato per Mobile */}
        <aside 
          className={`
            fixed inset-y-0 left-0 w-full sm:w-96 md:w-80 bg-gray-900 text-gray-200 
            transform transition-transform duration-300 z-30 shadow-2xl flex flex-col border-r border-gray-800
            md:relative md:translate-x-0
            ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          `}
        >
          {/* BARRA DI RICERCA E CONTROLLI */}
          <div className="p-3 bg-gray-900 border-b border-gray-800 sticky top-0 z-10 space-y-3">
              <div className="relative group">
                  <Search className="absolute left-3 top-2.5 text-gray-500 group-focus-within:text-red-400 transition-colors" size={16} />
                  <input 
                    type="text"
                    placeholder="Cerca pagine..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-gray-800 text-gray-200 text-sm rounded-lg pl-10 pr-8 py-2 border border-gray-700 focus:border-red-500 focus:ring-1 focus:ring-red-500 outline-none transition-all placeholder-gray-500"
                  />
                  {searchTerm && (
                      <button onClick={() => setSearchTerm('')} className="absolute right-2 top-2 text-gray-500 hover:text-white">
                          <X size={16} />
                      </button>
                  )}
              </div>
              
              {/* NUOVO: Checkbox per Admin - Nascondi Bozze/Staff */}
              {canEdit && (
                  <label className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-gray-800/50 hover:bg-gray-800 cursor-pointer transition-colors border border-gray-700">
                      <input 
                          type="checkbox"
                          checked={hideAdminContent}
                          onChange={(e) => {
                              const newValue = e.target.checked;
                              setHideAdminContent(newValue);
                              localStorage.setItem('wiki_hide_admin_content', newValue.toString());
                          }}
                          className="w-4 h-4 rounded border-gray-600 text-indigo-600 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-0 bg-gray-700 cursor-pointer"
                      />
                      <span className="text-xs text-gray-300 font-medium flex items-center gap-1.5 leading-tight">
                          <EyeOff size={13} className="text-gray-400" />
                          Nascondi bozze e sezioni staff
                      </span>
                  </label>
              )}
          </div>

          {/* CONTENUTO MENU */}
          <nav className="overflow-y-auto flex-1 px-3 pb-20 scroll-smooth" style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#374151 transparent'
          }}>
             {loadingMenu ? (
               <div className="p-6 text-center text-gray-500 text-sm animate-pulse">Caricamento indice...</div>
             ) : (
               <>
                 {searchTerm ? (
                   /* RISULTATI RICERCA */
                   <ul className="space-y-1 mt-2">
                        {(() => {
                            // Filtra in base alla ricerca e hideAdminContent
                            const filtered = flatMenu.filter(i => {
                                const matchesSearch = i.titolo.toLowerCase().includes(searchTerm.toLowerCase());
                                if (!matchesSearch) return false;
                                
                                // Se hideAdminContent è attivo e l'utente è admin, nascondi bozze e staff-only
                                if (hideAdminContent && canEdit) {
                                    if (i.public === false || i.visibile_solo_staff === true) {
                                        return false;
                                    }
                                }
                                
                                return true;
                            });
                            
                            if (filtered.length === 0) {
                                return <li className="p-4 text-gray-500 text-sm text-center">Nessun risultato.</li>;
                            }
                            
                            return filtered.map(item => (
                                <li key={item.id}>
                                    <Link 
                                        to={`/regolamento/${item.slug}`}
                                        className="block p-3 rounded bg-gray-800 hover:bg-gray-700 transition-colors border-l-4 border-transparent hover:border-red-500"
                                        onClick={() => setSidebarOpen(false)}
                                    >
                                        <div className="font-bold text-gray-200">{item.titolo}</div>
                                        {item.parent && <div className="text-xs text-gray-500">in {flatMenu.find(p => p.id === item.parent)?.titolo}</div>}
                                        
                                        <div className="flex gap-1 mt-1">
                                            {item.public === false && <span className="text-[9px] bg-yellow-600 text-black px-1 rounded font-bold uppercase">Bozza</span>}
                                            {item.visibile_solo_staff && <span className="text-[9px] bg-indigo-600 text-white px-1 rounded font-bold uppercase">Staff</span>}
                                        </div>
                                    </Link>
                                </li>
                            ));
                        })()}
                   </ul>
                 ) : (
                    /* ALBERO STANDARD */
                    <ul className="space-y-1 mt-2">
                        {menuTree.map(node => <WikiSidebarItem key={node.id} item={node} />)}
                    </ul>
                 )}
               </>
             )}
          </nav>

          {/* FOOTER SIDEBAR: NUOVA PAGINA */}
          {canEdit && !searchTerm && (
             <div className="p-3 border-t border-gray-800 bg-gray-900">
                <button 
                    onClick={handleCreateRoot}
                    className="w-full bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xs font-bold py-3 px-3 rounded-lg border border-gray-700 border-dashed flex items-center justify-center gap-2 transition"
                >
                    <Plus size={14} /> Nuova Pagina Principale
                </button>
             </div>
          )}
        </aside>

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8 bg-gray-50 relative scroll-smooth w-full">
          <Outlet />
          
          {/* FAB: AGGIUNGI SOTTO-PAGINA */}
          {canEdit && (
            <button 
                onClick={handleCreateNested}
                className="fixed bottom-6 right-6 md:bottom-10 md:right-10 bg-red-700 hover:bg-red-800 text-white w-14 h-14 rounded-full shadow-lg hover:shadow-xl z-40 flex items-center justify-center transition-all transform hover:scale-105 active:scale-95"
                title="Aggiungi Sotto-Pagina qui"
            >
                <Plus size={32} />
            </button>
          )}
        </main>

        {/* Overlay Mobile */}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/60 z-20 md:hidden backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          ></div>
        )}

      </div>

      {/* MODALE EDITOR */}
      {isEditorOpen && (
        <WikiPageEditorModal 
            initialData={{ parent: newParentId }} 
            onClose={() => setEditorOpen(false)} 
            onSuccess={(newSlug) => {
                setEditorOpen(false);
                window.location.href = newSlug ? `/regolamento/${newSlug}` : '/';
            }}
        />
      )}

    </div>
    </>
  );
}