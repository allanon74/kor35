import React from 'react';
import { Puzzle } from 'lucide-react';
import MinigiocoQrEditor from './MinigiocoQrEditor';

/**
 * Sezione minigioco QR nelle schermate staff (nodi, timer, …).
 * Richiede un QR già associato all'elemento A_vista.
 */
const StaffMinigiocoQrSection = ({ qrcodeId, onLogout, lookup = {} }) => (
  <div className="border-t border-indigo-800/40 pt-4 mt-4">
    {!qrcodeId ? (
      <div className="text-xs text-gray-500 bg-gray-900/50 border border-gray-700 rounded p-3">
        <div className="flex items-center gap-2 text-indigo-300/80 font-semibold mb-1">
          <Puzzle size={14} />
          Minigioco QR
        </div>
        Associa prima un QR fisico con il pulsante <strong className="text-gray-300">Associa QR</strong>,
        poi potrai attivare puzzle / memory / tessere rotabili su quella scansione.
      </div>
    ) : (
      <MinigiocoQrEditor qrId={qrcodeId} onLogout={onLogout} lookup={lookup} />
    )}
  </div>
);

export default StaffMinigiocoQrSection;
