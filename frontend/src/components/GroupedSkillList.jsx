import React, { useMemo, useState } from 'react';
import PunteggioDisplay from './PunteggioDisplay';

// Sotto-componente per la riga singola (Gestisce lo stato di espansione)
const SkillRow = ({ 
  skill, 
  group, 
  onItemClick, 
  renderSubtitle, 
  showDescription, 
  actionRenderer 
}) => {
  // Stato locale per gestire l'apertura/chiusura della descrizione
  const [isExpanded, setIsExpanded] = useState(false);

  const handleDescriptionClick = (e) => {
    e.stopPropagation(); // Evita di attivare onItemClick (apertura modale) se si clicca sul testo
    setIsExpanded(!isExpanded);
  };

  return (
    <li className="p-3 flex flex-col sm:flex-row sm:items-center justify-between hover:bg-gray-800/60 transition-colors gap-3 border-b border-gray-700/50 last:border-0">
      {/* Parte Sinistra (Cliccabile per aprire dettaglio modale) */}
      <div 
        className="flex flex-col grow cursor-pointer"
        onClick={() => onItemClick && onItemClick(skill)}
      >
        <div className="flex items-center">
          <div className="mr-3 shrink-0">
            {group.charData ? (
              <PunteggioDisplay 
                punteggio={group.charData} 
                displayText="none" 
                size="xs" 
                iconType="inv_circle" 
              />
            ) : (
              <div className="w-4 h-4 bg-gray-600 rounded-full" />
            )}
          </div>
          <span className="font-semibold text-gray-200 text-base block">{skill.nome}</span>
        </div>
        
        {/* Sottotitolo (es. Requisiti/Costo) */}
        {renderSubtitle && renderSubtitle(skill)}
        
        {/* Descrizione Collassabile (Logica Accordion) */}
        {showDescription && skill.descrizione && (
          <div
            onClick={handleDescriptionClick}
            className={`text-xs text-gray-400 pl-7 mt-1 prose prose-invert prose-sm leading-snug cursor-pointer hover:text-gray-200 transition-colors select-none ${
              isExpanded ? '' : 'line-clamp-1'
            }`}
            title={isExpanded ? "Clicca per ridurre" : "Clicca per espandere"}
            // Usa dangerouslySetInnerHTML per supportare eventuali tag HTML nella descrizione
            dangerouslySetInnerHTML={{ __html: skill.descrizione }}
          />
        )}
      </div>
      
      {/* Parte Destra (Azioni/Pulsanti) */}
      {actionRenderer && (
        <div className="flex items-center gap-2 shrink-0 self-end sm:self-center ml-7 sm:ml-0">
          {actionRenderer(skill)}
        </div>
      )}
    </li>
  );
};

const GroupedSkillList = ({ 
  skills, 
  punteggiList, 
  onItemClick, 
  actionRenderer, 
  renderSubtitle, 
  showDescription = true // Default a true per mostrare le descrizioni
}) => {
  
  const { sortedSections } = useMemo(() => {
    if (!skills) return { sortedSections: [] };

    const groups = skills.reduce((acc, skill) => {
      let charName = "Altro";
      let charObj = null;
      let charId = null;

      if (skill.caratteristica) {
        if (typeof skill.caratteristica === 'object') {
            charName = skill.caratteristica.nome;
            charId = skill.caratteristica.id;
            charObj = skill.caratteristica; 
        } else if (typeof skill.caratteristica === 'number') {
             charId = skill.caratteristica;
        } else {
             charName = String(skill.caratteristica);
        }
      }

      if (punteggiList && punteggiList.length > 0) {
        let found = null;
        if (charId) found = punteggiList.find(p => p.id === charId);
        if (!found && charName !== "Altro") found = punteggiList.find(p => p.nome === charName);
        
        if (found) {
            charObj = found;
            charName = found.nome;
        }
      }

      if (!acc[charName]) acc[charName] = { skills: [], charData: charObj };
      acc[charName].skills.push(skill);
      return acc;
    }, {});

    Object.values(groups).forEach(group => {
        group.skills.sort((a, b) => a.nome.localeCompare(b.nome));
    });

    const sections = [];
    const usedKeys = new Set();

    if (punteggiList) {
        punteggiList.forEach(p => {
            if (groups[p.nome]) {
                sections.push({ name: p.nome, ...groups[p.nome] });
                usedKeys.add(p.nome);
            }
        });
    }

    Object.keys(groups).sort().forEach(key => {
        if (!usedKeys.has(key)) {
            sections.push({ name: key, ...groups[key] });
        }
    });

    return { sortedSections: sections };
  }, [skills, punteggiList]);

  if (!skills || skills.length === 0) {
     return <p className="text-gray-500 bg-gray-800 p-4 rounded-lg text-center italic">Nessuna abilità trovata.</p>;
  }

  return (
    <div className="space-y-6">
      {sortedSections.map((group) => {
        const charName = group.name;
        const headerBg = group.charData?.colore || '#374151';
        
        return (
            <div 
                key={charName} 
                className="bg-gray-900/40 rounded-xl overflow-hidden shadow-sm border border-gray-700"
                style={{ borderColor: headerBg }}
            >
              {/* Header con PunteggioDisplay */}
              <div 
                  className="px-4 py-2 border-b border-black/20 flex items-center"
                  style={{ backgroundColor: headerBg }}
              >
                  {group.charData ? (
                      <PunteggioDisplay 
                         punteggio={group.charData}
                         displayText="name" 
                         iconType="inv_circle"
                         size="m"
                         className="bg-transparent! shadow-none! p-0 w-full justify-start text-white"
                      />
                  ) : (
                      <h4 className="text-lg font-bold uppercase tracking-wider text-white">
                         {charName}
                      </h4>
                  )}
              </div>
              
              {/* Lista Skills usando il nuovo componente SkillRow */}
              <ul className="divide-y divide-gray-700/50">
                {group.skills.map((skill) => (
                  <SkillRow 
                    key={skill.id}
                    skill={skill}
                    group={group}
                    onItemClick={onItemClick}
                    renderSubtitle={renderSubtitle}
                    showDescription={showDescription}
                    actionRenderer={actionRenderer}
                  />
                ))}
              </ul>
            </div>
        );
      })}
    </div>
  );
};

export default GroupedSkillList;