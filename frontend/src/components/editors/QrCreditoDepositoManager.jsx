import React, { memo } from 'react';
import ManifestoManager from './ManifestoManager';

/**
 * Voce menu dedicata: apre direttamente il tab «Crediti QR»
 * (stesso backend/UI di Manifesti / Serie / Trappole / Crediti).
 */
const QrCreditoDepositoManager = (props) => (
  <ManifestoManager {...props} initialTab="crediti" />
);

export default memo(QrCreditoDepositoManager);
