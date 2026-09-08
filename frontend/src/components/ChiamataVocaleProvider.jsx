import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  accettaChiamataVocale,
  avviaChiamataVocale,
  chiudiChiamataVocale,
  getChiamataIceServers,
  getChiamataVocaleAttiva,
  rifiutaChiamataVocale,
} from '../api';
import { useCharacter } from './CharacterContext';
import ChiamataVocaleOverlay from './ChiamataVocaleOverlay';

const ChiamataVocaleContext = createContext(null);

function wsUrl() {
  const token = localStorage.getItem('kor35_token');
  if (!token) return null;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws/chiamate/?token=${encodeURIComponent(token)}`;
}

function startRingtone() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return () => {};
  const ctx = new AudioCtx();
  let stopped = false;
  const beep = () => {
    if (stopped) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 880;
    gain.gain.value = 0.08;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.18);
  };
  beep();
  const id = window.setInterval(beep, 900);
  return () => {
    stopped = true;
    window.clearInterval(id);
    try {
      ctx.close();
    } catch {
      /* noop */
    }
  };
}

function serializeSdp(desc) {
  if (!desc) return null;
  return { type: desc.type, sdp: desc.sdp };
}

function iceInit(candidate) {
  if (!candidate) return null;
  if (typeof candidate === 'string') return { candidate };
  return {
    candidate: candidate.candidate,
    sdpMid: candidate.sdpMid ?? null,
    sdpMLineIndex: candidate.sdpMLineIndex ?? 0,
    usernameFragment: candidate.usernameFragment,
  };
}

export function ChiamataVocaleProvider({ children }) {
  const { selectedCharacterId, onLogout, canAccessModulo } = useCharacter();
  const chiamateAbilitate = canAccessModulo ? canAccessModulo('chiamate') : false;
  const [call, setCall] = useState(null);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState('');
  const [remoteReady, setRemoteReady] = useState(false);
  const wsRef = useRef(null);
  const pcRef = useRef(null);
  const localStreamRef = useRef(null);
  const remoteAudioRef = useRef(null);
  const pendingIceRef = useRef([]);
  const pendingSignalsRef = useRef([]);
  const iceServersRef = useRef(null);
  const stopRingRef = useRef(null);
  const callRef = useRef(null);
  const offerSentRef = useRef(null);
  callRef.current = call;

  const playRemote = useCallback(async () => {
    const el = remoteAudioRef.current;
    if (!el) return;
    el.muted = false;
    el.volume = 1;
    try {
      await el.play();
    } catch {
      /* autoplay: riprova su ontrack / gesto utente */
    }
  }, []);

  const attachRemoteStream = useCallback(
    (stream) => {
      const el = remoteAudioRef.current;
      if (!el || !stream) return;
      if (el.srcObject !== stream) {
        el.srcObject = stream;
      }
      setRemoteReady(true);
      playRemote();
    },
    [playRemote]
  );

  const sendSignal = useCallback((payload) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
      return;
    }
    pendingSignalsRef.current.push(payload);
  }, []);

  const stopLocalMedia = useCallback(() => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((t) => t.stop());
      localStreamRef.current = null;
    }
    if (pcRef.current) {
      try {
        pcRef.current.close();
      } catch {
        /* noop */
      }
      pcRef.current = null;
    }
    pendingIceRef.current = [];
    pendingSignalsRef.current = [];
    offerSentRef.current = null;
    setRemoteReady(false);
    setMuted(false);
    if (remoteAudioRef.current) {
      remoteAudioRef.current.srcObject = null;
    }
    if (stopRingRef.current) {
      stopRingRef.current();
      stopRingRef.current = null;
    }
  }, []);

  const ensureMic = useCallback(async () => {
    if (localStreamRef.current) return localStreamRef.current;
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Microfono non supportato su questo browser.');
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
    localStreamRef.current = stream;
    return stream;
  }, []);

  const ensureIce = useCallback(async () => {
    if (iceServersRef.current) return iceServersRef.current;
    try {
      const data = await getChiamataIceServers(onLogout);
      iceServersRef.current = data?.iceServers || [];
    } catch {
      iceServersRef.current = [{ urls: 'stun:stun.l.google.com:19302' }];
    }
    return iceServersRef.current;
  }, [onLogout]);

  const flushIce = useCallback(async (pc) => {
    const queued = pendingIceRef.current.splice(0);
    for (const cand of queued) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(cand));
      } catch {
        /* candidato stale */
      }
    }
  }, []);

  const setupPeer = useCallback(
    async (callId) => {
      if (pcRef.current) return pcRef.current;
      const iceServers = await ensureIce();
      const stream = await ensureMic();
      const pc = new RTCPeerConnection({ iceServers, iceCandidatePoolSize: 4 });
      stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream));
      if (!pc.getTransceivers().some((t) => t.receiver?.track?.kind === 'audio' || t.sender?.track?.kind === 'audio')) {
        pc.addTransceiver('audio', { direction: 'sendrecv' });
      }
      pc.onicecandidate = (ev) => {
        if (ev.candidate) {
          sendSignal({
            type: 'ice',
            call_id: callId,
            candidate: iceInit(ev.candidate.toJSON ? ev.candidate.toJSON() : ev.candidate),
          });
        }
      };
      pc.ontrack = (ev) => {
        const remote = ev.streams?.[0] || new MediaStream(ev.track ? [ev.track] : []);
        attachRemoteStream(remote);
      };
      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
          setError('Collegamento audio instabile.');
        }
      };
      pc.oniceconnectionstatechange = () => {
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          setError('');
        }
        if (pc.iceConnectionState === 'failed') {
          setError('Collegamento audio fallito (rete/TURN). Chiudi e richiama.');
        }
      };
      pcRef.current = pc;
      return pc;
    },
    [attachRemoteStream, ensureIce, ensureMic, sendSignal]
  );

  const createOffer = useCallback(
    async (callId) => {
      if (offerSentRef.current === callId) return;
      offerSentRef.current = callId;
      try {
        const pc = await setupPeer(callId);
        const offer = await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: false });
        await pc.setLocalDescription(offer);
        sendSignal({ type: 'sdp', call_id: callId, sdp: serializeSdp(pc.localDescription) });
      } catch (err) {
        if (offerSentRef.current === callId) offerSentRef.current = null;
        setError(err?.message || 'Impossibile avviare l\'audio.');
      }
    },
    [sendSignal, setupPeer]
  );

  const handleRemoteSdp = useCallback(
    async (sdp, callId) => {
      if (!sdp?.type || !sdp?.sdp) return;
      try {
        const pc = await setupPeer(callId);
        if (sdp.type === 'offer' && pc.signalingState !== 'stable') {
          return;
        }
        if (sdp.type === 'answer' && pc.signalingState !== 'have-local-offer') {
          return;
        }
        await pc.setRemoteDescription(new RTCSessionDescription(sdp));
        await flushIce(pc);
        if (sdp.type === 'offer') {
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          sendSignal({ type: 'sdp', call_id: callId, sdp: serializeSdp(pc.localDescription) });
        }
      } catch (err) {
        setError(err?.message || 'Segnalazione audio fallita.');
      }
    },
    [flushIce, sendSignal, setupPeer]
  );

  const handleRemoteIce = useCallback(async (candidate) => {
    const init = iceInit(candidate);
    if (!init?.candidate) return;
    const pc = pcRef.current;
    if (!pc || !pc.remoteDescription) {
      pendingIceRef.current.push(init);
      return;
    }
    try {
      await pc.addIceCandidate(new RTCIceCandidate(init));
    } catch {
      /* noop */
    }
  }, []);

  const clearCall = useCallback(() => {
    stopLocalMedia();
    setCall(null);
    setError('');
  }, [stopLocalMedia]);

  const hangup = useCallback(async () => {
    const current = callRef.current;
    stopLocalMedia();
    setCall(null);
    if (current?.id) {
      sendSignal({ type: 'hangup', call_id: current.id });
      try {
        await chiudiChiamataVocale(current.id, onLogout);
      } catch {
        /* già chiusa */
      }
    }
  }, [onLogout, sendSignal, stopLocalMedia]);

  const applySignal = useCallback(
    (msg) => {
      if (!msg) return;
      const action = msg.action || msg.type;
      const callId = msg.call_id || msg.id;
      if (action === 'sdp' && msg.sdp) {
        handleRemoteSdp(msg.sdp, callId);
        return;
      }
      if (action === 'ice' && msg.candidate) {
        handleRemoteIce(msg.candidate);
        return;
      }
      if (action === 'VOCE_INVITO') {
        const mine = String(msg.chiamante_id) === String(selectedCharacterId);
        setCall((prev) => {
          if (prev && prev.id === callId) return prev;
          return {
            id: callId,
            stato: 'ringing',
            verso_staff: !!msg.verso_staff,
            chiamante: { id: msg.chiamante_id, nome: msg.chiamante_nome },
            chiamato: { id: msg.chiamato_id, nome: msg.chiamato_nome },
            ruolo: mine ? 'caller' : 'callee',
          };
        });
        if (!mine && !stopRingRef.current) {
          stopRingRef.current = startRingtone();
        }
        return;
      }
      if (action === 'VOCE_ACCETTATA') {
        if (stopRingRef.current) {
          stopRingRef.current();
          stopRingRef.current = null;
        }
        setCall((prev) => {
          if (!prev || prev.id !== callId) {
            return {
              id: callId,
              stato: 'in_corso',
              verso_staff: !!msg.verso_staff,
              chiamante: { id: msg.chiamante_id, nome: msg.chiamante_nome },
              chiamato: { id: msg.chiamato_id, nome: msg.chiamato_nome },
              ruolo: String(msg.chiamante_id) === String(selectedCharacterId) ? 'caller' : 'callee',
            };
          }
          return { ...prev, stato: 'in_corso' };
        });
        const isCaller = String(msg.chiamante_id) === String(selectedCharacterId);
        if (isCaller) {
          createOffer(callId);
        }
        return;
      }
      if (
        action === 'VOCE_RIFIUTATA' ||
        action === 'VOCE_CHIUSA' ||
        action === 'VOCE_PERSA' ||
        action === 'VOCE_PRESA'
      ) {
        if (callRef.current && String(callRef.current.id) === String(callId)) {
          clearCall();
        }
      }
    },
    [clearCall, createOffer, handleRemoteIce, handleRemoteSdp, selectedCharacterId]
  );

  useEffect(() => {
    const onVoce = (ev) => applySignal(ev.detail);
    window.addEventListener('kor35:voce', onVoce);
    return () => window.removeEventListener('kor35:voce', onVoce);
  }, [applySignal]);

  useEffect(() => {
    if (!chiamateAbilitate) return undefined;
    const url = wsUrl();
    if (!url) return undefined;
    let closed = false;
    let retry = 0;
    let timer;
    const connect = () => {
      if (closed) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        retry = 0;
        const queued = pendingSignalsRef.current.splice(0);
        queued.forEach((payload) => {
          try {
            ws.send(JSON.stringify(payload));
          } catch {
            /* noop */
          }
        });
      };
      ws.onmessage = (ev) => {
        try {
          applySignal(JSON.parse(ev.data));
        } catch {
          /* noop */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        retry = Math.min(retry + 1, 6);
        timer = window.setTimeout(connect, Math.min(1000 * 2 ** retry, 15000));
      };
    };
    connect();
    return () => {
      closed = true;
      window.clearTimeout(timer);
      if (wsRef.current) wsRef.current.close();
    };
  }, [applySignal, chiamateAbilitate]);

  useEffect(() => {
    if (!chiamateAbilitate) return undefined;
    let cancelled = false;
    getChiamataVocaleAttiva(onLogout)
      .then((data) => {
        if (cancelled || !data?.chiamata) return;
        if (data.chiamata.stato === 'in_corso') {
          chiudiChiamataVocale(data.chiamata.id, onLogout).catch(() => {});
          return;
        }
        if (data.chiamata.stato === 'ringing') {
          setCall(data.chiamata);
          if (data.chiamata.ruolo === 'callee') {
            stopRingRef.current = startRingtone();
          }
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [onLogout, chiamateAbilitate]);

  const startCall = useCallback(
    async ({ personaggioId = null, versoStaff = false } = {}) => {
      setError('');
      if (!selectedCharacterId) {
        setError('Seleziona un personaggio prima di chiamare.');
        return;
      }
      if (!chiamateAbilitate) {
        setError('Chiamate vocali: modulo non attivo in questa campagna.');
        return;
      }
      try {
        await ensureMic();
        await playRemote();
        const data = await avviaChiamataVocale(
          {
            chiamante_id: Number(selectedCharacterId),
            chiamato_id: versoStaff ? null : personaggioId,
            verso_staff: !!versoStaff,
          },
          onLogout
        );
        setCall({ ...data, ruolo: 'caller' });
      } catch (err) {
        stopLocalMedia();
        const msg =
          err?.detail ||
          err?.message ||
          (typeof err === 'string' ? err : 'Impossibile avviare la chiamata.');
        setError(String(msg));
        throw err;
      }
    },
    [chiamateAbilitate, ensureMic, onLogout, playRemote, selectedCharacterId, stopLocalMedia]
  );

  const acceptCall = useCallback(async () => {
    const current = callRef.current;
    if (!current?.id) return;
    setError('');
    try {
      await ensureMic();
      await playRemote();
      const data = await accettaChiamataVocale(current.id, onLogout);
      if (stopRingRef.current) {
        stopRingRef.current();
        stopRingRef.current = null;
      }
      setCall({ ...data, ruolo: 'callee' });
      await setupPeer(data.id);
    } catch (err) {
      stopLocalMedia();
      setError(err?.detail || err?.message || 'Impossibile accettare.');
    }
  }, [ensureMic, onLogout, playRemote, setupPeer, stopLocalMedia]);

  const rejectCall = useCallback(async () => {
    const current = callRef.current;
    if (!current?.id) return;
    try {
      await rifiutaChiamataVocale(current.id, onLogout);
    } catch {
      /* noop */
    }
    clearCall();
  }, [clearCall, onLogout]);

  const toggleMute = useCallback(() => {
    const stream = localStreamRef.current;
    if (!stream) return;
    const next = !muted;
    stream.getAudioTracks().forEach((t) => {
      t.enabled = !next;
    });
    setMuted(next);
  }, [muted]);

  const value = useMemo(
    () => ({
      call,
      error,
      muted,
      remoteReady,
      startCall,
      acceptCall,
      rejectCall,
      hangup,
      toggleMute,
    }),
    [acceptCall, call, error, hangup, muted, rejectCall, remoteReady, startCall, toggleMute]
  );

  return (
    <ChiamataVocaleContext.Provider value={value}>
      {children}
      <audio ref={remoteAudioRef} autoPlay playsInline className="absolute w-px h-px opacity-0 overflow-hidden" />
      <ChiamataVocaleOverlay
        call={call}
        error={error}
        muted={muted}
        remoteReady={remoteReady}
        acceptCall={acceptCall}
        rejectCall={rejectCall}
        hangup={hangup}
        toggleMute={toggleMute}
      />
    </ChiamataVocaleContext.Provider>
  );
}

export const useChiamataVocale = () => {
  const ctx = useContext(ChiamataVocaleContext);
  if (!ctx) {
    return {
      call: null,
      error: '',
      muted: false,
      remoteReady: false,
      startCall: async () => {},
      acceptCall: async () => {},
      rejectCall: async () => {},
      hangup: async () => {},
      toggleMute: () => {},
    };
  }
  return ctx;
};
