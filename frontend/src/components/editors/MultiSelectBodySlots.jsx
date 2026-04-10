import React from 'react';

const MultiSelectBodySlots = ({ value = "", allSlots, onChange }) => {
  // Converte la stringa salvata in un array di codici
  const selectedList = value ? value.split(',') : [];

  const toggleSlot = (code) => {
    const newList = selectedList.includes(code)
      ? selectedList.filter(s => s !== code)
      : [...selectedList, code];
    // Restituisce la stringa unita per il backend
    onChange(newList.join(','));
  };

  return (
    <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-700">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-2 text-center tracking-widest">Slot Corporei Consentiti</label>
      <div className="flex flex-wrap gap-2 justify-center">
        {allSlots.map(slot => (
          <button
            key={slot.code}
            type="button"
            onClick={() => toggleSlot(slot.code)}
            className={`px-3 py-1 rounded-md text-[10px] font-bold border uppercase transition-all shadow-sm ${
              selectedList.includes(slot.code) 
                ? 'bg-indigo-600 border-indigo-400 text-white scale-105' 
                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-500'
            }`}
          >
            {slot.name}
          </button>
        ))}
      </div>
    </div>
  );
};

export default MultiSelectBodySlots;