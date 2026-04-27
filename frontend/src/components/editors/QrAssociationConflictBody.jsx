import React from 'react';

const TIPO_LABELS = {
  nodo: 'Nodo (QR)',
  manifesto: 'Manifesto',
  inventario: 'Inventario',
  oggetto: 'Oggetto',
  infusione: 'Infusione',
  tessitura: 'Tessitura',
  cerimoniale: 'Cerimoniale',
  innesco_timer: 'Innesco timer',
  personaggio: 'Personaggio',
  attivata: 'Attivata (legacy)',
  a_vista: 'Elemento vista (generico)',
  sconosciuto: 'Elemento sconosciuto',
};

function normalizeAssoc(errorData) {
  if (!errorData) return null;
  if (errorData.associazione_attuale) return errorData.associazione_attuale;
  const cv = errorData.current_vista;
  if (cv && (cv.nome != null || cv.id != null)) {
    return {
      tipo: cv.tipo,
      nome: cv.nome,
      elemento_id: cv.id != null ? String(cv.id) : undefined,
    };
  }
  return null;
}

/**
 * Corpo del modal di conflitto QR (409): mostra a cosa è legato il codice e chiede conferma per sostituire.
 */
const QrAssociationConflictBody = ({ errorData, targetHint }) => {
  const a = normalizeAssoc(errorData);
  const tipoLabel = TIPO_LABELS[a?.tipo] || a?.tipo || '—';

  return (
    <div className="space-y-3 text-sm text-gray-300 mt-1">
      {a ? (
        <>
          <p className="text-gray-400">Il codice QR scansionato è già collegato a:</p>
          <div className="bg-gray-950 border border-gray-700 rounded-lg p-3 text-white space-y-1.5">
            <div>
              <span className="text-gray-500">Tipo: </span>
              <span className="font-semibold text-indigo-200">{tipoLabel}</span>
            </div>
            <div>
              <span className="text-gray-500">Nome: </span>
              <span className="font-medium">{a.nome || '—'}</span>
            </div>
            {a.elemento_id && (
              <div className="text-[10px] text-gray-500">ID elemento: {a.elemento_id}</div>
            )}
            {errorData?.qr_id && (
              <div className="text-[10px] text-gray-500">ID QR: {errorData.qr_id}</div>
            )}
          </div>
          <p>
            Vuoi <span className="text-amber-300 font-bold">sostituire</span> l&apos;associazione
            {targetHint ? (
              <>
                {' '}
                e collegare il QR a <span className="text-white font-semibold">{targetHint}</span>?
              </>
            ) : (
              <> e collegare il QR a questo elemento?</>
            )}
          </p>
        </>
      ) : (
        <p className="text-gray-400 whitespace-pre-line">{errorData?.message || 'Conflitto di associazione QR.'}</p>
      )}
    </div>
  );
};

export default QrAssociationConflictBody;
