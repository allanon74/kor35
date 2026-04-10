import React from 'react';
import { X } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import PunteggioDisplay from './PunteggioDisplay.jsx';

const AbilitaDetailModal = ({ skill, onClose }) => {
  if (!skill) return null;

  const { punteggiList } = useCharacter();
  
  const caratteristicaPunteggio = skill.caratteristica ? punteggiList.find(
    p => p.id === skill.caratteristica.id
  ) : null;

  const costoPC = skill.costo_pc_calc !== undefined ? skill.costo_pc_calc : skill.costo_pc;
  const costoCrediti = skill.costo_crediti_calc !== undefined ? skill.costo_crediti_calc : skill.costo_crediti;
  const isScontato = skill.costo_crediti_calc !== undefined && 
                     skill.costo_crediti_calc < skill.costo_crediti;
  
  const showCosti = (costoPC !== undefined && costoPC > 0) || (costoCrediti !== undefined && costoCrediti > 0);
  
  // --- Logica per "Modifiche ai punteggi" ---
  const tipiConsentiti = ['CA', 'ST', 'AU']; // Caratteristica, Statistica, Aura
  
  const punteggiModificati = (skill.punteggi_assegnati || [])
    .map(link => {
        const punteggio = punteggiList.find(p => p.id === link.punteggio.id);
        if (punteggio && tipiConsentiti.includes(punteggio.tipo)) {
          return { ...link, punteggio }; 
        }
        return null;
    })
    // CORREZIONE 1: Filtra i valori nulli E quelli con modificatore 0
    .filter(item => item !== null && item.valore !== 0); 

  const statisticheModificate = (skill.statistiche_modificate || [])
    .map(link => {
        const punteggio = punteggiList.find(p => p.id === link.statistica.id);
        if (punteggio) {
          return { ...link, punteggio };
        }
        return null;
    })
    // CORREZIONE 1: Filtra i valori nulli E quelli con modificatore 0
    .filter(item => item !== null && item.valore !== 0);
    
  const showModifiche = punteggiModificati.length > 0 || statisticheModificate.length > 0;
  // --- Fine Logica ---

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-lg p-6 mx-4 bg-gray-800 rounded-lg shadow-xl"
        onClick={(e) => e.stopPropagation()} 
      >
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white"
        >
          <X size={24} />
        </button>
        
        {caratteristicaPunteggio && (
          <div className="absolute top-4 right-16">
            <PunteggioDisplay
              punteggio={caratteristicaPunteggio}
              displayText="none"
              iconType="inv_circle"
            />
          </div>
        )}

        <h2 className="text-2xl font-bold text-indigo-400 mb-4 pr-16">
          {skill.nome}
        </h2>
        
        {skill.descrizione ? (
          <div
            className="text-gray-300 mb-4 prose prose-invert" 
            dangerouslySetInnerHTML={{ __html: skill.descrizione }}
          />
        ) : (
          <p className="text-gray-300 mb-4">
            <em>Nessuna descrizione.</em>
          </p>
        )}

        {showCosti && (
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-200">Costi</h3>
            {costoPC > 0 && (
              <p className="text-gray-400">
                {costoPC} Punti Caratteristica
              </p>
            )}
            {costoCrediti > 0 && (
              <p className="text-gray-400">
                {isScontato ? (
                  <>
                    <del className="text-red-400">{skill.costo_crediti}</del>
                    <span className="text-green-400 ml-1">{costoCrediti}</span>
                  </>
                ) : (
                  <span>{costoCrediti}</span>
                )} Crediti
              </p>
            )}
          </div>
        )}

        {/* --- NUOVO BLOCCO: MODIFICHE AI PUNTEGGI --- */}
        {showModifiche && (
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-200">Modifiche ai punteggi</h3>
            <div className="flex flex-wrap gap-2 mt-2">
              
              {statisticheModificate.map(link => (
                <PunteggioDisplay
                  key={`stat-${link.punteggio.id}`}
                  punteggio={link.punteggio}
                  // CORREZIONE 2: Aggiunto uno spazio iniziale
                  value={link.tipo_modificatore === 'ADD' ? 
                         (link.valore > 0 ? ` +${link.valore}` : ` ${link.valore}`) : 
                         ` x${link.valore}`}
                  displayText="name"
                  iconType="inv_circle"
                />
              ))}
              
              {punteggiModificati.map(link => (
                <PunteggioDisplay
                  key={`punt-${link.punteggio.id}`}
                  punteggio={link.punteggio}
                  // CORREZIONE 2: Aggiunto uno spazio iniziale
                  value={link.valore > 0 ? ` +${link.valore}` : ` ${link.valore}`}
                  displayText="name"
                  iconType="inv_circle"
                />
              ))}
              
            </div>
          </div>
        )}
        {/* --- FINE NUOVO BLOCCO --- */}


        {skill.requisiti && skill.requisiti.length > 0 && (
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-200">Requisiti</h3>
            <ul className="list-disc list-inside text-gray-400">
              {skill.requisiti.map(req => (
                <li key={req.requisito.nome}>
                  {req.requisito.nome}: {req.valore}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {skill.prerequisiti && skill.prerequisiti.length > 0 && (
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-200">Prerequisiti</h3>
            <ul className="list-disc list-inside text-gray-400">
              {skill.prerequisiti.map(pre => (
                <li key={pre.prerequisito.id}>
                  {pre.prerequisito.nome}
                </li>
              ))}
            </ul>
          </div>
        )}

      </div>
    </div>
  );
};

export default AbilitaDetailModal;