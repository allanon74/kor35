import React, { useMemo, useCallback, memo, useState, useEffect } from 'react';
import { useCharacter } from './CharacterContext';
import { Coins, Star, Bell, Backpack, Zap, Pencil, Save, X } from 'lucide-react';
import PunteggioDisplay from './PunteggioDisplay';
import GenericGroupedList from './GenericGroupedList';
import IconaPunteggio from './IconaPunteggio';
import ActiveItemWidget from './ActiveItemWidget'; // <--- IMPORT WIDGET
import StatisticaModificatoriModal from './StatisticaModificatoriModal'; // <--- IMPORT MODAL
import { stripRazzaPrefix } from './RazzaCollapsible';
import RichTextDisplay from './RichTextDisplay';
import RichTextEditor from './RichTextEditor';
import { updatePersonaggio, resolveMediaUrl } from '../api';

// --- NUOVI COMPONENTI ---
import LogViewer from './LogViewer';
import TransazioniViewer from './TransazioniViewer';

// --- Componenti Helper ---

const StatRow = memo(({ label, value, icon }) => (
  <div className="flex justify-between items-center p-2 bg-gray-800 rounded-md hover:bg-gray-750 transition-colors">
    <div className="flex items-center">
      {icon}
      <span className="ml-2 font-semibold text-gray-300 capitalize">{label}</span>
    </div>
    <span className="text-xl font-bold text-white">{value}</span>
  </div>
));

StatRow.displayName = 'StatRow';

// (ItemList commentato come nel tuo originale)
// const ItemList = ({ title, items, keyField = 'id', nameField = 'nome' }) => (
//   <div className="mb-6">
// ...
//   </div>
// );

const LoadingComponent = () => (
  <div className="p-8 text-center text-lg text-gray-400">
    Caricamento dati personaggio...
  </div>
);


// --- Componente Scheda ---

const CharacterSheet = memo(({ data, onLogout }) => {
  const { punteggiList, statisticaContainers, subscribeToPush, refreshCharacterData } = useCharacter();
  
  // State per la modal dei modificatori
  const [modalStatistica, setModalStatistica] = useState(null);
  const [isEditingBackground, setIsEditingBackground] = useState(false);
  const [backgroundDraft, setBackgroundDraft] = useState(data?.testo || '');
  const [isSavingBackground, setIsSavingBackground] = useState(false);
  // La modale Razza vive nell'header (MainPage). Qui resta solo il pulsante.

  const {
    id: personaggioId,
    nome,
    avatar_url: avatarUrl,
    crediti,
    punti_caratteristica,
    punteggi_base,
    statistiche_base_dict,
    modificatori_calcolati, 
    abilita_possedute, 
    oggetti,
    // log_eventi <-- RIMOSSO: Ora gestito da LogViewer
  } = data;

  const canEditRazza = !!data?.can_edit_razza;
  const canEditBackground = canEditRazza;

  useEffect(() => {
    setBackgroundDraft(data?.testo || '');
    setIsEditingBackground(false);
  }, [personaggioId, data?.testo]);

  const auraInnataRecord = useMemo(
    () => (punteggiList || []).find((p) => p.tipo === 'AU' && String(p.sigla || '').toUpperCase() === 'AIN'),
    [punteggiList]
  );

  /** Nome e descrizione archetipo/forma per il riepilogo in fondo scheda */
  const razzaRiepilogo = useMemo(() => {
    const isTrattoInnita = (ab) =>
      ab?.is_tratto_aura &&
      ab?.aura_riferimento &&
      String(ab.aura_riferimento.sigla || '').toUpperCase() === 'AIN';
    const arch = (abilita_possedute || []).find(
      (ab) => isTrattoInnita(ab) && (ab.livello_riferimento === 0 || ab.livello_riferimento === 1)
    );
    const forma = (abilita_possedute || []).find((ab) => isTrattoInnita(ab) && ab.livello_riferimento === 2);
    const tratti = auraInnataRecord?.tratti_disponibili || [];
    const umanoCatalogo = tratti.find(
      (t) => t.livello_riferimento === 0 && stripRazzaPrefix(t.nome).toLowerCase() === 'umano'
    );
    return {
      archetipoNome: arch ? stripRazzaPrefix(arch.nome) : 'Umano',
      archetipoDescrizione: arch?.descrizione || umanoCatalogo?.descrizione || null,
      formaNome: forma ? stripRazzaPrefix(forma.nome) : null,
      formaDescrizione: forma?.descrizione || null,
    };
  }, [abilita_possedute, auraInnataRecord]);

  // --- LOGICA FILTRO OGGETTI ATTIVI ---
  const activeItems = useMemo(() => {
    if (!oggetti) return [];
    
    return oggetti.filter(obj => {
      // 1. Mostra sempre Innesti (INN) e Mod (MOD), anche se scarichi
      if (['INN', 'MOD'].includes(obj.tipo_oggetto)) return true;
      
      // 2. Mostra oggetti fisici (es. armi/bacchette) SOLO se hanno cariche attive > 0
      if (obj.cariche_attuali > 0) return true;
      
      return false;
    });
  }, [oggetti]);

  // Calcolo Statistiche
  const { stat_primarie, stat_secondarie, caratteristiche, aure_possedute } = useMemo(() => {
    if (!punteggiList || punteggiList.length === 0 || !punteggi_base) { 
      return { stat_primarie: [], stat_secondarie: [], caratteristiche: [], aure_possedute: [] };
    }

    const sortByOrdine = (a, b) => (a.ordine || 0) - (b.ordine || 0);
    const sortByPunteggioOrdine = (a, b) => (a.punteggio.ordine || 0) - (b.punteggio.ordine || 0);

    const primarie = punteggiList
        .filter(p => p.tipo === 'ST' && p.is_primaria)
        .sort(sortByOrdine);

    const secondarie = punteggiList
        .filter(p => p.tipo === 'ST' && !p.is_primaria)
        .sort(sortByOrdine);

    const punteggiMappati = Object.entries(punteggi_base) 
      .map(([nome, valore]) => {
        const punteggio = punteggiList.find(p => p.nome === nome);
        if (punteggio) return { punteggio, valore };
        return null; 
      })
      .filter(Boolean); 

    const chars = punteggiMappati
        .filter(item => item.punteggio.tipo === 'CA')
        .sort(sortByPunteggioOrdine);
    
    const aure = punteggiMappati
        .filter(item => item.punteggio.tipo === 'AU')
        .sort(sortByPunteggioOrdine);

    return { stat_primarie: primarie, stat_secondarie: secondarie, caratteristiche: chars, aure_possedute: aure };

  }, [punteggiList, punteggi_base]);

  // --- CONTENITORI STATISTICHE (config DB) ---
  const {
    containersTopLevel,
    containersByParentId,
    coveredStatIds,
    statsById,
  } = useMemo(() => {
    const containers = Array.isArray(statisticaContainers) ? statisticaContainers : [];
    const byParent = new Map();
    for (const c of containers) {
      const pid = c.parent_id || null;
      const arr = byParent.get(pid) || [];
      arr.push(c);
      byParent.set(pid, arr);
    }
    for (const [k, arr] of byParent.entries()) {
      arr.sort((a, b) => (a.ordine || 0) - (b.ordine || 0));
      byParent.set(k, arr);
    }

    const top = (byParent.get(null) || []).filter((c) => !!c.render_in_primarie);

    // Segna come "coperte" solo le statistiche dei container effettivamente
    // renderizzati nella sezione primaria (top-level render_in_primarie + figli).
    const covered = new Set();
    const visitVisibleTree = (container) => {
      for (const it of container.items || []) {
        if (it?.statistica_id != null) covered.add(it.statistica_id);
      }
      const children = byParent.get(container.id) || [];
      for (const child of children) visitVisibleTree(child);
    };
    for (const c of top) visitVisibleTree(c);

    const statsMap = new Map((punteggiList || []).map((p) => [p.id, p]));

    return {
      containersTopLevel: top,
      containersByParentId: byParent,
      coveredStatIds: covered,
      statsById: statsMap,
    };
  }, [statisticaContainers, punteggiList]);

  const computeStatValue = useCallback(
    (punteggio) => {
      if (!punteggio) return 0;
      const parametro = punteggio.parametro || null;
      const nome = punteggio.nome;
      // Allineato a Personaggio.get_valore_statistica: base da punteggi_base (scheda, abilità,
      // punteggi dipendenti), poi modificatori globali. Senza questo, la scheda ignora RPG ecc. e
      // nascondi_se_uno nasconde valori ancora a 1 prima dei bonus dipendenti.
      const haPb =
        punteggi_base &&
        nome != null &&
        Object.prototype.hasOwnProperty.call(punteggi_base, nome);
      const valoreBaseDaPersonaggio =
        parametro && statistiche_base_dict ? statistiche_base_dict[parametro] : undefined;
      const valore_base = haPb
        ? Number(punteggi_base[nome] ?? 0)
        : valoreBaseDaPersonaggio ??
          punteggio.valore_base_predefinito ??
          punteggio.valore_predefinito ??
          0;
      const mods =
        (parametro && modificatori_calcolati && modificatori_calcolati[parametro]) || { add: 0, mol: 1.0 };
      return Math.round((valore_base + (mods.add || 0)) * (mods.mol || 1.0));
    },
    [punteggi_base, statistiche_base_dict, modificatori_calcolati]
  );

  const StatisticaContainerTile = ({ container }) => {
    const fakePunteggio = {
      nome: container.nome,
      colore: container.colore,
      icona_url: container.icona_url,
    };

    const children = containersByParentId.get(container.id) || [];
    const shouldHideByRules = (value, cfg) => {
      if (cfg?.nascondi_se_negativa && value < 0) return true;
      if (cfg?.nascondi_se_zero && value === 0) return true;
      if (cfg?.nascondi_se_uno && value === 1) return true;
      return false;
    };

    const items = (container.items || [])
      .slice()
      .sort((a, b) => (a.ordine || 0) - (b.ordine || 0))
      .map((it) => {
        const stat = statsById.get(it.statistica_id);
        if (!stat) return null;
        const value = computeStatValue(stat);
        if (shouldHideByRules(value, it)) return null;
        return { stat, itemConfig: it, value };
      })
      .filter(Boolean);

    const renderedChildren = children
      .map((child) => <StatisticaContainerTile key={child.id} container={child} />)
      .filter(Boolean);

    const hasVisibleNonDipendente = items.some(({ itemConfig }) => !itemConfig?.is_dipendente);
    const canRenderContainer = hasVisibleNonDipendente || renderedChildren.length > 0;

    if (!canRenderContainer) {
      return null;
    }

    return (
      <div className="rounded-lg overflow-hidden border border-gray-700 bg-gray-900/30">
        <PunteggioDisplay
          punteggio={fakePunteggio}
          value={null}
          displayText="name"
          iconType="inv_circle"
          size={container.dimensione || "s"}
          shadow={false}
          roundedClass="rounded-none"
          readOnly={true}
        />

        <div className="p-2 space-y-2">
          {renderedChildren.length > 0 && (
            <div className="grid grid-cols-1 gap-2">
              {renderedChildren}
            </div>
          )}

          {items.length > 0 && (
            <div className="flex flex-col gap-2">
              {items.map(({ stat: p, itemConfig, value }) => (
                <PunteggioDisplay
                  key={p.id}
                  punteggio={
                    container.usa_colore_contenitore_per_figli
                      ? { ...p, colore: container.colore }
                      : p
                  }
                  value={value}
                  displayText="name"
                  iconType="inv_circle"
                  size={itemConfig?.dimensione || "s"}
                  shadow={false}
                  readOnly={true}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // --- RENDER ITEM ABILITÀ ---
  const renderAbilitaItem = (abilita) => {
    const iconUrl = abilita.caratteristica?.icona_url;
    const iconColor = abilita.caratteristica?.colore;

    return (
        <li className="py-2 px-2 hover:bg-gray-700/50 transition-colors rounded-sm cursor-default border-b border-gray-700/50 last:border-0">
            <div className="flex items-center gap-2">
                <div className="mt-1 self-start shrink-0">
                    <IconaPunteggio 
                        url={iconUrl}
                        color={iconColor}
                        mode="cerchio_inv" 
                        size="xs"
                    />
                </div>
                <span className="font-bold text-gray-200 text-base">
                    {abilita.nome}
                </span>
            </div>

            {abilita.descrizione && (
                <div
                    className="text-sm text-gray-400 pl-8 mt-1 prose prose-invert prose-sm max-w-none leading-snug"
                    dangerouslySetInnerHTML={{ __html: abilita.descrizione }}
                />
            )}
        </li>
    );
  };

  // --- RENDER HEADER GRUPPO (PunteggioDisplay) ---
  const renderGroupHeader = (group) => {
    const fakePunteggio = {
        nome: group.name,
        colore: group.color,
        icona_url: group.icon
    };

    return (
        <PunteggioDisplay 
            punteggio={fakePunteggio}
            value={group.items.length} 
            displayText="name"
            iconType="inv_circle" 
            size="s"              
            className="rounded-b-none" 
        />
    );
  };

  const handleSaveBackground = async () => {
    if (!canEditBackground || isSavingBackground) return;
    setIsSavingBackground(true);
    try {
      await updatePersonaggio(personaggioId, { testo: backgroundDraft || '' }, onLogout);
      await refreshCharacterData();
      setIsEditingBackground(false);
    } catch (error) {
      alert(`Errore salvataggio background: ${error.message}`);
    } finally {
      setIsSavingBackground(false);
    }
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-6 pb-4 border-b border-gray-700/80">
        <div className="h-20 w-20 rounded-full border-2 border-indigo-500/35 bg-gray-800 overflow-hidden shrink-0 flex items-center justify-center">
          {avatarUrl ? (
            <img src={resolveMediaUrl(avatarUrl)} alt="" className="h-full w-full object-cover" />
          ) : (
            <span className="text-3xl font-black text-indigo-200">{(nome || '?').charAt(0).toUpperCase()}</span>
          )}
        </div>
        <div className="min-w-0">
          <h2 className="text-2xl font-bold text-white truncate">{nome}</h2>
          <p className="text-xs text-gray-500 mt-1">Scheda personaggio</p>
        </div>
      </div>

      {/* Banner Notifiche */}
      {'Notification' in window && Notification.permission !== 'granted' && (
         <div className="mb-6 p-4 bg-indigo-900/50 rounded-lg border border-indigo-500 flex flex-col sm:flex-row justify-between items-center gap-3">
            <div className="flex items-center gap-3">
                <div className="bg-indigo-600 p-2 rounded-full">
                    <Bell size={20} className="text-white" />
                </div>
                <div>
                    <p className="font-bold text-white text-sm">Notifiche Push</p>
                    <p className="text-xs text-indigo-200">Ricevi messaggi anche ad app chiusa.</p>
                </div>
            </div>
            <button onClick={() => subscribeToPush()} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded shadow transition-colors w-full sm:w-auto">
                Attiva
            </button>
         </div>
      )}

      {auraInnataRecord && canEditRazza && (
        <div className="mb-6 flex justify-center">
          <button
            type="button"
            onClick={() => window.dispatchEvent(new CustomEvent('kor35:open-razza-modal'))}
            className="text-xs font-semibold uppercase tracking-wider text-amber-500/90 hover:text-amber-400 underline-offset-2 hover:underline"
          >
            Modifica forma e archetipo
          </button>
        </div>
      )}
      
      {/* --- NUOVA SEZIONE: DISPOSITIVI ATTIVI --- */}
      {activeItems && activeItems.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3 border-b border-gray-700 pb-2">
             <Zap className="w-5 h-5 text-yellow-400" />
             <h3 className="text-2xl font-semibold text-gray-200">Dispositivi Attivi</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activeItems.map(item => (
              <ActiveItemWidget 
                key={item.id} 
                item={item} 
                onUpdate={refreshCharacterData} 
              />
            ))}
          </div>
        </div>
      )}

      {/* Valute */}
      <div className="grid grid-cols-2 gap-4 mb-6 max-w-lg mx-auto"> 
        <StatRow label="CR" value={crediti || 0} icon={<Coins className="text-yellow-400 animate-pulse" />} />
        <StatRow label="PC" value={punti_caratteristica || 0} icon={<Star className="text-blue-400" />} />
      </div>

      {/* Statistiche Primarie */}
      {stat_primarie.length > 0 && (
        <div className="mb-6">
          <h3 className="text-2xl font-semibold mb-3 text-gray-200 border-b border-gray-700 pb-2">Statistiche</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"> 
            {/* 1) Contenitori (configurazione DB) */}
            {containersTopLevel.map((c) => (
              <StatisticaContainerTile key={c.id} container={c} />
            ))}

            {/* 2) Statistiche primarie non coperte da contenitori */}
            {stat_primarie
              .filter((p) => !coveredStatIds.has(p.id))
              .map((punteggio) => {
              if (!punteggio.parametro) return null; 
              
              const valore_finale = computeStatValue(punteggio);
              
              return (
                <div 
                  key={punteggio.id}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    setModalStatistica(punteggio);
                  }}
                  className="cursor-context-menu"
                  title="Click destro per dettagli"
                >
                  <PunteggioDisplay
                    punteggio={punteggio}
                    value={valore_finale} 
                    displayText="name"
                    iconType="inv_circle"
                    size="m"
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Caratteristiche */}
      {caratteristiche.length > 0 && (
        <div className="mb-6">
          <h3 className="text-2xl font-semibold mb-3 text-gray-200 border-b border-gray-700 pb-2">Caratteristiche</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {caratteristiche.map(({ punteggio, valore }) => (
                <PunteggioDisplay
                  key={punteggio.id} 
                  punteggio={punteggio} 
                  value={valore}         
                  displayText="name"   
                  iconType="inv_circle"
                  size="m"
                />
            ))}
          </div>
        </div>
      )}

      {/* Aure Possedute */}
      {aure_possedute.length > 0 && (
        <div className="mb-6">
            <h3 className="text-2xl font-semibold mb-3 text-gray-200 border-b border-gray-700 pb-2">Aure Possedute</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {aure_possedute.map(({ punteggio, valore }) => (
                    <PunteggioDisplay
                        key={punteggio.id}
                        punteggio={punteggio}
                        value={valore}
                        displayText="name"
                        iconType="inv_circle"
                        size="m"
                    />
                ))}
            </div>
        </div>
      )}

      {/* Abilità */}
      {/* <div className="mb-6">
        <h3 className="text-2xl font-semibold mb-3 text-gray-200 border-b border-gray-700 pb-2">Abilità</h3>
        {abilita_possedute && abilita_possedute.length > 0 ? (
            <GenericGroupedList 
                items={abilita_possedute}
                groupByKey="caratteristica"
                orderKey="ordine"
                titleKey="nome"             
                colorKey="colore"           
                iconKey="icona_url"         
                renderItem={renderAbilitaItem}
                renderHeader={renderGroupHeader}
                compact={false} 
            />
        ) : (
            <p className="text-gray-500 bg-gray-800 p-4 rounded-lg shadow-inner">Nessuna abilità trovata.</p>
        )}
      </div> */}

      {/* Oggetti - Se vuoi riattivare ItemList, scommenta qui sotto. Per ora è commentato come da originale */}
      {/* <ItemList title="Oggetti" items={oggetti} /> */}

      {/* --- SEZIONE LOG EVENTI (PAGINATA) --- */}
      {/* <div className="mb-6">
         <LogViewer />
      </div> */}

      {/* --- SEZIONE TRANSAZIONI (PAGINATA) --- */}
      {/* <div className="mb-6">
         <h3 className="text-2xl font-semibold mb-3 text-gray-200 border-b border-gray-700 pb-2">Transazioni</h3>
         <TransazioniViewer />
      </div> */}

      {/* Statistiche Secondarie (Accordion) */}
      {stat_secondarie && stat_secondarie.length > 0 && (
        <details className="mt-4 bg-gray-800 rounded-lg shadow-inner">
          <summary className="text-xl font-semibold text-gray-200 p-3 cursor-pointer select-none">
            Statistiche Secondarie
          </summary>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 p-4 border-t border-gray-700">
            {stat_secondarie
              .filter((p) => !coveredStatIds.has(p.id))
              .map((punteggio) => {
              const valore_finale = computeStatValue(punteggio);
              
              return (
                <div 
                  key={punteggio.id}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    setModalStatistica(punteggio);
                  }}
                  className="cursor-context-menu"
                  title="Click destro per dettagli"
                >
                  <PunteggioDisplay
                    punteggio={punteggio}
                    value={valore_finale} 
                    displayText="name"
                    iconType="inv_circle"
                    size="m"
                  />
                </div>
              );
            })}
          </div>
        </details>
      )}

      {auraInnataRecord && (
        <div className="mt-10 pt-6 border-t border-gray-700">
          <h3 className="text-xl font-semibold text-gray-200 mb-4 border-b border-gray-700 pb-2">
            Razza
          </h3>
          <div className="flex flex-col lg:flex-row gap-8 lg:items-start">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-500/90 mb-2">
                Archetipo
              </p>
              <p className="text-lg font-bold text-gray-100 mb-2">{razzaRiepilogo.archetipoNome}</p>
              {razzaRiepilogo.archetipoDescrizione ? (
                <div
                  className="text-sm text-gray-300 prose prose-invert prose-sm max-w-none leading-relaxed prose-p:my-1.5 prose-headings:text-gray-200"
                  dangerouslySetInnerHTML={{ __html: razzaRiepilogo.archetipoDescrizione }}
                />
              ) : null}
            </div>
            {razzaRiepilogo.formaNome ? (
              <div className="flex-1 min-w-0 pt-6 border-t border-gray-700 lg:pt-0 lg:border-t-0 lg:border-l lg:border-gray-700 lg:pl-8">
                <p className="text-xs font-semibold uppercase tracking-wider text-cyan-500/90 mb-2">
                  Forma
                </p>
                <p className="text-lg font-bold text-gray-100 mb-2">{razzaRiepilogo.formaNome}</p>
                {razzaRiepilogo.formaDescrizione ? (
                  <div
                    className="text-sm text-gray-300 prose prose-invert prose-sm max-w-none leading-relaxed prose-p:my-1.5 prose-headings:text-gray-200"
                    dangerouslySetInnerHTML={{ __html: razzaRiepilogo.formaDescrizione }}
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      )}

      <details className="mt-6 bg-gray-800 rounded-lg shadow-inner">
        <summary className="text-xl font-semibold text-gray-200 p-3 cursor-pointer select-none">
          Background
        </summary>
        <div className="p-4 border-t border-gray-700 space-y-3">
          {isEditingBackground ? (
            <>
              <RichTextEditor
                label="Background Personaggio"
                value={backgroundDraft}
                onChange={setBackgroundDraft}
              />
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleSaveBackground}
                  disabled={isSavingBackground}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-bold text-sm"
                >
                  <Save size={16} />
                  {isSavingBackground ? 'Salvataggio...' : 'Salva'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setBackgroundDraft(data?.testo || '');
                    setIsEditingBackground(false);
                  }}
                  disabled={isSavingBackground}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-bold text-sm"
                >
                  <X size={16} />
                  Annulla
                </button>
              </div>
            </>
          ) : (
            <>
              {data?.testo ? (
                <RichTextDisplay content={data.testo} />
              ) : (
                <p className="text-sm text-gray-400 italic">Nessun background inserito.</p>
              )}
              {canEditBackground ? (
                <button
                  type="button"
                  onClick={() => setIsEditingBackground(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm"
                >
                  <Pencil size={16} />
                  Modifica background
                </button>
              ) : (
                <p className="text-xs text-amber-300">
                  Modifica background bloccata: il primo evento associato al personaggio e gia iniziato.
                </p>
              )}
            </>
          )}
        </div>
      </details>

      {/* Modal Modificatori */}
      {modalStatistica && (
        <StatisticaModificatoriModal 
          punteggio={modalStatistica}
          personaggioId={personaggioId}
          onClose={() => setModalStatistica(null)}
          onLogout={onLogout}
        />
      )}
    </div>
  );
});

CharacterSheet.displayName = 'CharacterSheet';

const HomeTab = memo(({ onLogout }) => {
  const { 
    selectedCharacterData, 
    isLoadingDetail,
    isLoadingPunteggi, 
    selectedCharacterId, 
    error 
  } = useCharacter();

  if (isLoadingDetail || isLoadingPunteggi) return <LoadingComponent />;
  if (error && !selectedCharacterData) return <div className="p-4 text-center text-red-400">Errore nel caricamento. Riprova.</div>;
  if (!selectedCharacterId) return <div className="p-8 text-center text-gray-400"><h2 className="text-2xl font-bold mb-4">Benvenuto!</h2><p>Seleziona un personaggio.</p></div>;
  if (!selectedCharacterData) return <div className="p-8 text-center text-gray-400"><p>Nessun dato trovato.</p></div>;

  return <CharacterSheet data={selectedCharacterData} onLogout={onLogout} />;
});

HomeTab.displayName = 'HomeTab';

export default HomeTab;