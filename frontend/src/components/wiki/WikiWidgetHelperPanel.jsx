import React from 'react';
import { Edit, Image as ImageIcon, MousePointerClick, Upload } from 'lucide-react';
import { getWidgetToken, sortByUsage } from './wikiWidgetTokens';

export default function WikiWidgetHelperPanel({
  showWidgetHelper,
  setShowWidgetHelper,
  widgetHelperTab,
  setWidgetHelperTab,
  usedWidgetIds,
  availableTierWidgets,
  availableTiers,
  availableEre,
  availableTierCollectionWidgets,
  availableImages,
  availableButtonWidgets,
  availableMattoniWidgets,
  tierSearch,
  setTierSearch,
  showUploadImage,
  insertWidget,
  onCreateTierWidget,
  onEditTierWidget,
  onCreateTierCollectionWidget,
  onEditTierCollectionWidget,
  onCreateImage,
  onEditImage,
  onCreateButtonWidget,
  onEditButtonWidget,
  onCreateMattoniWidget,
  onEditMattoniWidget,
}) {
  return (
    <div className="bg-blue-50 p-3 rounded border border-blue-200">
      <button
        type="button"
        onClick={() => setShowWidgetHelper(!showWidgetHelper)}
        className="w-full bg-blue-600 text-white px-3 py-2 rounded text-xs hover:bg-blue-700 transition flex justify-between items-center"
      >
        <span>🧩 Inserisci Widget</span>
        <span>{showWidgetHelper ? '▲' : '▼'}</span>
      </button>

      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-[10px] text-yellow-800">
        <strong>💡 Modifica Widget:</strong> Per modificare un widget già inserito, vai alla sezione corrispondente (Tier/Immagini/Pulsanti) e modifica l'elemento. Le modifiche si rifletteranno automaticamente nella pagina.
      </div>

      {showWidgetHelper && (
        <div className="mt-2 bg-white rounded border border-gray-300 shadow-inner">
          <div className="flex border-b border-gray-200">
            <button type="button" onClick={() => setWidgetHelperTab('tier')} className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${widgetHelperTab === 'tier' ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>📊 Tier</button>
            <button type="button" onClick={() => setWidgetHelperTab('ere')} className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${widgetHelperTab === 'ere' ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>🏛️ Ere</button>
            <button type="button" onClick={() => setWidgetHelperTab('tierCollection')} className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${widgetHelperTab === 'tierCollection' ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>🗂️ Collezioni</button>
            <button type="button" onClick={() => setWidgetHelperTab('image')} className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${widgetHelperTab === 'image' ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>🖼️ Immagini</button>
            <button type="button" onClick={() => setWidgetHelperTab('buttons')} className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${widgetHelperTab === 'buttons' ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>🔘 Pulsanti</button>
            <button type="button" onClick={() => setWidgetHelperTab('mattoni')} className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${widgetHelperTab === 'mattoni' ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>🧱 Mattoni</button>
          </div>

          <div className="max-h-40 md:max-h-60 overflow-y-auto">
            {widgetHelperTab === 'tier' && (
              <>
                {(() => {
                  const usedTierIds = usedWidgetIds.tiers || [];
                  const widgetIdsSet = new Set((availableTierWidgets || []).map((w) => w.id));
                  const usedWidgets = usedTierIds.filter((id) => widgetIdsSet.has(id));
                  if (usedWidgets.length === 0) return null;
                  return (
                    <div className="p-2 border-b border-gray-200 bg-amber-50">
                      <p className="text-xs font-bold text-gray-700 mb-1">Widget Tier in questa pagina</p>
                      {usedWidgets.map((id) => {
                        const w = availableTierWidgets.find((x) => x.id === id);
                        return (
                          <div key={id} className="flex justify-between items-center gap-1 py-1">
                            <span className="text-xs truncate">{w?.tier_nome || `#${id}`}</span>
                            <div className="flex items-center gap-1 shrink-0">
                              <button type="button" onClick={() => onEditTierWidget(w || { id })} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded" title="Modifica widget tier"><Edit size={12} /></button>
                              <span className="text-[10px] px-1 rounded bg-gray-100">ID:{id}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                <div className="p-2 border-b border-gray-200 bg-indigo-50">
                  <button type="button" onClick={onCreateTierWidget} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors">
                    <MousePointerClick size={14} />
                    Crea / Configura Widget Tier
                  </button>
                </div>

                {availableTierWidgets.length > 0 && (
                  <div className="p-1 border-b border-gray-200">
                    <p className="text-xs font-bold text-gray-600 mb-1">Widget Tier esistenti</p>
                    {sortByUsage(availableTierWidgets, usedWidgetIds.tiers).map((w) => {
                      const isUsed = usedWidgetIds.tiers.includes(w.id);
                      return (
                        <div key={w.id} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                          <button type="button" onClick={() => insertWidget(`{{WIDGET_TIER:${getWidgetToken(w)}}}`)} className="flex-1 flex items-center gap-2 truncate">
                            <span className={`font-bold truncate ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓ </span>}{w.tier_nome || `Widget #${w.id}`}</span>
                          </button>
                          <div className="flex items-center gap-1 shrink-0">
                            <button type="button" onClick={() => onEditTierWidget(w)} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded" title="Modifica"><Edit size={12} /></button>
                            <span className="text-[10px] px-1 rounded bg-gray-100">ID:{w.id}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="p-2 border-b border-gray-200 bg-gray-50 sticky top-0 z-10">
                  <p className="text-xs font-bold text-gray-600 mb-1">Inserisci tier semplice (senza opzioni)</p>
                  <input type="text" placeholder="Cerca tier per nome..." value={tierSearch} onChange={(e) => setTierSearch(e.target.value)} className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                {availableTiers.length === 0 && <p className="p-2 text-xs text-gray-500">Caricamento...</p>}
                {[...availableTiers]
                  .filter((t) => !(tierSearch || '').trim() || (t.nome || '').toLowerCase().includes((tierSearch || '').trim().toLowerCase()))
                  .sort((a, b) => (a.nome || '').localeCompare(b.nome || ''))
                  .map((tier) => {
                    const isUsed = usedWidgetIds.tiers.includes(tier.id);
                    return (
                      <button key={tier.id} type="button" onClick={() => insertWidget(`{{WIDGET_TIER:${getWidgetToken(tier)}}}`)} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                        <span className={`font-bold truncate pr-2 flex items-center gap-2 ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓</span>}{tier.nome}</span>
                        <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>ID:{tier.id}</span>
                      </button>
                    );
                  })}
              </>
            )}

            {widgetHelperTab === 'ere' && (
              <>
                {availableEre.length === 0 && <p className="p-2 text-xs text-gray-500">Nessuna era disponibile</p>}
                {sortByUsage(availableEre, usedWidgetIds.ere).map((era) => {
                  const token = getWidgetToken(era);
                  const isUsed = usedWidgetIds.ere.includes(token);
                  return (
                    <button key={token} type="button" onClick={() => insertWidget(`{{WIDGET_ERA:${token}}}`)} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                      <span className={`font-bold truncate pr-2 flex items-center gap-2 ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓</span>}{era.nome}</span>
                      <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>ID:{token}</span>
                    </button>
                  );
                })}
              </>
            )}

            {widgetHelperTab === 'tierCollection' && (
              <>
                <div className="p-2 border-b border-gray-200 bg-indigo-50">
                  <button type="button" onClick={onCreateTierCollectionWidget} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors">
                    <MousePointerClick size={14} />
                    Crea / Configura Collezione Tier
                  </button>
                </div>
                {availableTierCollectionWidgets.length === 0 && <p className="p-2 text-xs text-gray-500">Nessuna collezione tier disponibile</p>}
                {sortByUsage(availableTierCollectionWidgets, usedWidgetIds.tierCollections).map((w) => {
                  const isUsed = usedWidgetIds.tierCollections.includes(w.id);
                  return (
                    <div key={w.id} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                      <button type="button" onClick={() => insertWidget(`{{WIDGET_TIER_COLLECTION:${getWidgetToken(w)}}}`)} className="flex-1 flex items-center gap-2 truncate">
                        <span className={`font-bold group-hover:text-blue-800 truncate ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓ </span>}{w.title || `Collezione #${w.id}`}</span>
                      </button>
                      <div className="flex items-center gap-1 shrink-0">
                        <button type="button" onClick={() => onEditTierCollectionWidget(w)} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors" title="Modifica collezione"><Edit size={12} /></button>
                        <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>ID:{w.id}</span>
                      </div>
                    </div>
                  );
                })}
              </>
            )}

            {widgetHelperTab === 'image' && (
              <>
                <div className="p-2 border-b border-gray-200 bg-green-50">
                  <button type="button" onClick={onCreateImage} className="w-full bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors">
                    <Upload size={14} />
                    Carica Nuova Immagine
                  </button>
                </div>
                {availableImages.length === 0 && !showUploadImage && <p className="p-2 text-xs text-gray-500">Nessuna immagine disponibile</p>}
                {sortByUsage(availableImages, usedWidgetIds.images).map((img) => {
                  const isUsed = usedWidgetIds.images.includes(img.id);
                  return (
                    <div key={img.id} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                      <button type="button" onClick={() => insertWidget(`{{WIDGET_IMAGE:${getWidgetToken(img)}}}`)} className="flex-1 flex items-center gap-2 truncate">
                        <ImageIcon size={14} className={`shrink-0 ${isUsed ? 'text-green-600' : 'text-gray-400'}`} />
                        <span className={`font-bold group-hover:text-blue-800 truncate ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓ </span>}{img.titolo || `Immagine #${img.id}`}</span>
                      </button>
                      <div className="flex items-center gap-1 shrink-0">
                        <button type="button" onClick={() => onEditImage(img)} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors" title="Modifica immagine"><Edit size={12} /></button>
                        <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>ID:{img.id}</span>
                      </div>
                    </div>
                  );
                })}
              </>
            )}

            {widgetHelperTab === 'buttons' && (
              <>
                <div className="p-2 border-b border-gray-200 bg-purple-50">
                  <button type="button" onClick={onCreateButtonWidget} className="w-full bg-purple-600 hover:bg-purple-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors">
                    <MousePointerClick size={14} />
                    Crea Nuovo Widget Pulsanti
                  </button>
                </div>
                {availableButtonWidgets.length === 0 && <p className="p-2 text-xs text-gray-500">Nessun widget pulsanti disponibile</p>}
                {sortByUsage(availableButtonWidgets, usedWidgetIds.buttons).map((widget) => {
                  const isUsed = usedWidgetIds.buttons.includes(widget.id);
                  return (
                    <div key={widget.id} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                      <button type="button" onClick={() => insertWidget(`{{WIDGET_BUTTONS:${getWidgetToken(widget)}}}`)} className="flex-1 flex items-center gap-2 truncate">
                        <MousePointerClick size={14} className={`shrink-0 ${isUsed ? 'text-purple-600' : 'text-purple-500'}`} />
                        <span className={`font-bold group-hover:text-blue-800 truncate ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓ </span>}{widget.title || `Widget #${widget.id}`}</span>
                      </button>
                      <div className="flex items-center gap-1 shrink-0">
                        <button type="button" onClick={() => onEditButtonWidget(widget)} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors" title="Modifica widget"><Edit size={12} /></button>
                        <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>{widget.buttons?.length || 0} btn</span>
                      </div>
                    </div>
                  );
                })}
              </>
            )}

            {widgetHelperTab === 'mattoni' && (
              <>
                {(() => {
                  const usedMattoniIds = usedWidgetIds.mattoni || [];
                  const widgetIdsSet = new Set((availableMattoniWidgets || []).map((w) => w.id));
                  const usedWidgets = usedMattoniIds.filter((x) => widgetIdsSet.has(x));
                  if (usedWidgets.length === 0) return null;
                  return (
                    <div className="p-2 border-b border-gray-200 bg-amber-50">
                      <p className="text-xs font-bold text-gray-700 mb-1">Widget Mattoni in questa pagina</p>
                      {usedWidgets.map((wid) => {
                        const w = availableMattoniWidgets.find((x) => x.id === wid);
                        return (
                          <div key={wid} className="flex justify-between items-center gap-1 py-1">
                            <span className="text-xs truncate">{w?.title || `Widget #${wid}`}</span>
                            <div className="flex items-center gap-1 shrink-0">
                              <button type="button" onClick={() => onEditMattoniWidget(w || { id: wid })} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded" title="Modifica widget mattoni"><Edit size={12} /></button>
                              <span className="text-[10px] px-1 rounded bg-gray-100">ID:{wid}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                <div className="p-2 border-b border-gray-200 bg-indigo-50">
                  <button type="button" onClick={onCreateMattoniWidget} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors">
                    <MousePointerClick size={14} />
                    Crea / Configura Widget Mattoni
                  </button>
                </div>

                {availableMattoniWidgets.length === 0 && <p className="p-2 text-xs text-gray-500">Nessun widget mattoni disponibile</p>}
                {sortByUsage(availableMattoniWidgets, usedWidgetIds.mattoni).map((w) => {
                  const isUsed = usedWidgetIds.mattoni.includes(w.id);
                  return (
                    <div key={w.id} className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''}`}>
                      <button type="button" onClick={() => insertWidget(`{{WIDGET_MATTONI:${getWidgetToken(w)}}}`)} className="flex-1 flex items-center gap-2 truncate">
                        <span className={`font-bold group-hover:text-blue-800 truncate ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>{isUsed && <span className="text-green-600">✓ </span>}{w.title || `Widget #${w.id}`}</span>
                      </button>
                      <div className="flex items-center gap-1 shrink-0">
                        <button type="button" onClick={() => onEditMattoniWidget(w)} className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors" title="Modifica widget"><Edit size={12} /></button>
                        <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>ID:{w.id}</span>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
