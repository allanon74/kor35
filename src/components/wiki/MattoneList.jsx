import React from 'react';

export default function MattoneList({ mattoni }) {
  return (
    <ul className="space-y-2 mt-2">
      {mattoni.map(m => (
        <li key={m.id} className="bg-gray-100 p-2 rounded border-l-4 border-blue-500">
          <span className="font-bold block">{m.nome}</span>
          <span className="text-sm text-gray-600">{m.descrizione}</span>
        </li>
      ))}
    </ul>
  );
}