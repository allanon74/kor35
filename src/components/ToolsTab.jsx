import React, { useState } from 'react';
import { useCharacter } from './CharacterContext';
import InfusioneManager from './editors/InfusioneManager';
import TessituraManager from './editors/TessituraManager';
import CerimonialeManager from './editors/CerimonialeManager';
import OggettoManager from './editors/OggettoManager';
import OggettoBaseManager from './editors/OggettoBaseManager';

const ToolsTab = ({ onLogout, initialSection }) => {
  const [activeTool, setActiveTool] = useState(initialSection || 'generic'); 
  const { setStaffWorkMode } = useCharacter();

  useEffect(() => {
        if (initialSection) setActiveTool(initialSection);
    }, [initialSection]);

  const handleBack = () => setActiveTool('menu');

  // Switch per i vari Manager (List + Editor)
  if (activeTool === 'infusione') return <InfusioneManager onBack={handleBack} onLogout={onLogout} />;
  if (activeTool === 'tessitura') return <TessituraManager onBack={handleBack} onLogout={onLogout} />;
  if (activeTool === 'cerimoniale') return <CerimonialeManager onBack={handleBack} onLogout={onLogout} />;
  if (activeTool === 'oggetti') return <OggettoManager onBack={handleBack} onLogout={onLogout} />;
  if (activeTool === 'oggetti_base') return <OggettoBaseManager onBack={handleBack} onLogout={onLogout} />;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-3xl font-bold text-amber-500 uppercase tracking-wider">🛠️ Strumenti Master</h1>
        <button 
          onClick={() => setStaffWorkMode(null)}
          className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded border border-gray-700 transition-colors text-sm font-bold uppercase"
        >
          Menu Principale
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
        <ToolCard 
          title="Gestione Infusioni" 
          desc="Crea e modifica Mod, Materie e Innesti" 
          icon="🧪" 
          color="indigo"
          onClick={() => setActiveTool('infusione')} 
        />
        <ToolCard 
          title="Gestione Tessiture" 
          desc="Gestisci le formule e i parametri dell'Aura" 
          icon="✨" 
          color="cyan"
          onClick={() => setActiveTool('tessitura')} 
        />
        <ToolCard 
          title="Gestione Cerimoniali" 
          desc="Configura riti ed effetti tecnici complessi" 
          icon="🕯️" 
          color="amber"
          onClick={() => setActiveTool('cerimoniale')} 
        />
        <ToolCard 
          title="Oggetti (Istanze)" 
          desc="Gestisci i singoli oggetti esistenti nel mondo" 
          icon="🎒" color="emerald"
          onClick={() => setActiveTool('oggetti')} 
        />
        <ToolCard 
          title="Oggetti Base" 
          desc="Configura il listino e i template degli oggetti" 
          icon="📋" color="blue"
          onClick={() => setActiveTool('oggetti_base')} 
        />
      </div>
    </div>
  );
};

const ToolCard = ({ title, desc, icon, onClick, color }) => (
  <button 
    onClick={onClick}
    className={`bg-gray-800/40 border border-gray-700 p-6 rounded-xl hover:border-${color}-500 hover:bg-gray-800/60 transition-all text-left group shadow-lg`}
  >
    <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">{icon}</div>
    <div className={`text-xl font-bold group-hover:text-${color}-400 transition-colors`}>{title}</div>
    <div className="text-sm text-gray-400 mt-2">{desc}</div>
  </button>
);

export default ToolsTab;