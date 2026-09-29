import React, { useCallback, useEffect, useRef, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';

const POLL_MS = 2000;

/**
 * Login inverso:
 * - la console crea un ticket temporaneo;
 * - mostra il QR del link claim;
 * - il telefono del giocatore loggato conferma;
 * - la console polla lo stato e riceve il token finale.
 */
export default function LoginQR({
  createTicket,
  pollTicket,
  onAuthorized,
  error,
  navigazioneStatSigla = '0PI',
  title = 'KOR-35 // CONSOLE PILOTA',
  lead = 'Scannerizza questo QR con lo smartphone del giocatore.',
  requisito = null,
  onBack = null,
  previewClaimUrl = '',
}) {
  const [ticket, setTicket] = useState(null);
  const [statusText, setStatusText] = useState('Inizializzazione...');
  const [localError, setLocalError] = useState('');
  const [remainingSec, setRemainingSec] = useState(0);
  const pollRef = useRef(null);
  const secRef = useRef(null);

  const stopTimers = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (secRef.current) clearInterval(secRef.current);
    pollRef.current = null;
    secRef.current = null;
  }, []);

  const startFlow = useCallback(async () => {
    stopTimers();
    setLocalError('');
    setStatusText('Genero QR temporaneo...');
    try {
      const t = await createTicket();
      setTicket(t);
      const deadline = new Date(t.expires_at).getTime();
      setRemainingSec(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
      setStatusText('Scannerizza con telefono del giocatore loggato.');

      secRef.current = setInterval(() => {
        const s = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        setRemainingSec(s);
      }, 1000);

      pollRef.current = setInterval(async () => {
        try {
          const st = await pollTicket(t.ticket_id, t.codice);
          if (st.status === 'pending') {
            setStatusText('In attesa di conferma dal telefono...');
            return;
          }
          if (st.status === 'expired') {
            setStatusText('Ticket scaduto. Rigenero...');
            stopTimers();
            startFlow();
            return;
          }
          if (st.status === 'authorized' && st.token) {
            setStatusText(`Accesso autorizzato: ${st.pilota?.nome || 'pilota'}`);
            stopTimers();
            onAuthorized(st.token);
          }
        } catch (e) {
          setLocalError(e?.message || 'Errore polling ticket.');
        }
      }, POLL_MS);
    } catch (e) {
      setLocalError(e?.message || 'Impossibile generare ticket login.');
      setStatusText('Errore creazione ticket.');
    }
  }, [createTicket, onAuthorized, pollTicket, stopTimers]);

  useEffect(() => {
    if (previewClaimUrl) {
      setTicket({ claim_url: previewClaimUrl, expires_at: new Date(Date.now() + 120000).toISOString() });
      setRemainingSec(120);
      setStatusText('Anteprima layout: QR dimostrativo.');
      return undefined;
    }
    startFlow();
    return () => stopTimers();
  }, [previewClaimUrl, startFlow, stopTimers]);

  const requisitoTesto = requisito || `Requisito pilota: statistica ${navigazioneStatSigla} >= 1.`;

  return (
    <div className="center-screen login-qr-screen">
      <h1>{title}</h1>
      <p>{lead}</p>
      <div className="card login-qr-card">
        <div className="qr-box">
          {ticket?.claim_url ? (
            <QRCodeSVG value={ticket.claim_url} size={220} bgColor="#ffffff" fgColor="#000000" />
          ) : (
            <p className="note">Preparazione QR...</p>
          )}
        </div>
        <p className="note">{statusText}</p>
        <p className="note">Scadenza ticket: {remainingSec}s</p>
        <div className="login-qr-actions">
          {onBack ? (
            <button type="button" className="btn" onClick={onBack}>
              Scelta
            </button>
          ) : null}
          <button type="button" className="btn primary" onClick={previewClaimUrl ? undefined : startFlow}>
            Rigenera QR
          </button>
        </div>
        {localError && <div className="error">{localError}</div>}
        {error && <div className="error">{error}</div>}
        <p className="note login-qr-req">{requisitoTesto}</p>
      </div>
    </div>
  );
}
