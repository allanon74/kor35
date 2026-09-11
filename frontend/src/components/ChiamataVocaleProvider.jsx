import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { createPortal } from 'react-dom';
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

function startRingtone(ctx) {
  if (!ctx) return () => {};
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
    // Non chiudere il context: su alcuni Android close() dopo lo squillo
    // spegne l'<audio> remoto (chiamato non sente, chiamante sì).
  };
}

/** Tiene l'elemento <audio> in play durante il tap Rispondi/Chiama. */
async function primeRemoteAudioElement(el, ctx) {
  if (!el) return;
  el.muted = false;
  el.volume = 1;
  el.setAttribute('playsinline', 'true');
  el.setAttribute('webkit-playsinline', 'true');
  if (!ctx) {
    const p = el.play();
    if (p && typeof p.catch === 'function') p.catch(() => {});
    return;
  }
  try {
    if (ctx.state === 'suspended') await ctx.resume();
    const dest = ctx.createMediaStreamDestination();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.value = 0.0001;
    osc.connect(gain);
    gain.connect(dest);
    osc.start();
    el.srcObject = dest.stream;
    await el.play();
    window.setTimeout(() => {
      try {
        osc.stop();
      } catch {
        /* già sostituito dallo stream remoto */
      }
    }, 500);
  } catch {
    /* autoplay ancora bloccato */
  }
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

/** Android Chrome spesso lascia il track in muted=true per qualche centinaio di ms. */
function waitTrackUnmuted(track, timeoutMs = 1200) {
  return new Promise((resolve) => {
    if (!track || track.readyState !== 'live' || !track.muted) {
      resolve();
      return;
    }
    const timer = window.setTimeout(resolve, timeoutMs);
    track.addEventListener(
      'unmute',
      () => {
        window.clearTimeout(timer);
        resolve();
      },
      { once: true }
    );
  });
}

export function ChiamataVocaleProvider({ children }) {
  const { selectedCharacterId, onLogout, canAccessModulo } = useCharacter();
  const chiamateAbilitate = canAccessModulo ? canAccessModulo('chiamate') : false;
  const [call, setCall] = useState(null);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState('');
  const [remoteReady, setRemoteReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const wsRef = useRef(null);
  const pcRef = useRef(null);
  const localStreamRef = useRef(null);
  const remoteAudioRef = useRef(null);
  const audioCtxRef = useRef(null);
  const pendingIceRef = useRef([]);
  const pendingSignalsRef = useRef([]);
  const iceServersRef = useRef(null);
  const stopRingRef = useRef(null);
  const callRef = useRef(null);
  const offerSentRef = useRef(null);
  const tearingDownRef = useRef(false);
  const revivingMicRef = useRef(false);
  const wakeLockRef = useRef(null);
  const disconnectTimerRef = useRef(null);
  const iceRestartAtRef = useRef(0);
  callRef.current = call;

  const ensureAudioContext = useCallback(() => {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    if (!audioCtxRef.current) audioCtxRef.current = new Ctx();
    return audioCtxRef.current;
  }, []);

  const unlockAudioSession = useCallback(async () => {
    const ctx = ensureAudioContext();
    if (!ctx) return;
    try {
      await ctx.resume();
    } catch {
      /* iOS può rifiutare se non c'è gesto */
    }
  }, [ensureAudioContext]);

  const playRemote = useCallback(() => {
    const el = remoteAudioRef.current;
    if (!el) return;
    el.muted = false;
    el.volume = 1;
    el.setAttribute('playsinline', 'true');
    el.setAttribute('webkit-playsinline', 'true');
    if (!el.srcObject) return;
    const p = el.play();
    if (p && typeof p.catch === 'function') p.catch(() => {});
  }, []);

  /** Prova l'altoparlante senza rubare cuffie Bluetooth già collegate. */
  const preferSpeakerSink = useCallback(async () => {
    const el = remoteAudioRef.current;
    if (!el || typeof el.setSinkId !== 'function') return;
    if (!navigator.mediaDevices?.enumerateDevices) return;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const outputs = devices.filter((d) => d.kind === 'audiooutput');
      const bluetooth = outputs.some((d) =>
        /bluetooth|headset|airpod|headphone|cuffie|a2dp/i.test(d.label || '')
      );
      if (bluetooth) return;
      const speaker = outputs.find((d) =>
        /speaker|altoparlante|speakerphone/i.test(d.label || '')
      );
      if (speaker && el.sinkId !== speaker.deviceId) {
        await el.setSinkId(speaker.deviceId);
      }
    } catch {
      /* iOS Safari: setSinkId non c'è; Android a volte nega enumerate */
    }
  }, []);

  const boostSpeaker = useCallback(async () => {
    await unlockAudioSession();
    await preferSpeakerSink();
    playRemote();
    const stream = localStreamRef.current;
    stream?.getAudioTracks().forEach((t) => {
      t.enabled = true;
    });
    if (muted) setMuted(false);
  }, [muted, playRemote, preferSpeakerSink, unlockAudioSession]);

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

  const releaseWakeLock = useCallback(() => {
    if (wakeLockRef.current) {
      try {
        wakeLockRef.current.release();
      } catch {
        /* noop */
      }
      wakeLockRef.current = null;
    }
    try {
      if (navigator.mediaSession) {
        navigator.mediaSession.playbackState = 'none';
        navigator.mediaSession.metadata = null;
      }
    } catch {
      /* noop */
    }
  }, []);

  const restartIce = useCallback(
    async (callId) => {
      const pc = pcRef.current;
      if (tearingDownRef.current || !pc || !callId) return;
      if (pc.signalingState !== 'stable') return;
      const now = Date.now();
      if (now - iceRestartAtRef.current < 4000) return;
      iceRestartAtRef.current = now;
      try {
        const offer = await pc.createOffer({ iceRestart: true });
        await pc.setLocalDescription(offer);
        sendSignal({ type: 'sdp', call_id: callId, sdp: serializeSdp(pc.localDescription) });
      } catch {
        /* glare o PC già chiuso */
      }
    },
    [sendSignal]
  );

  const stopLocalMedia = useCallback(() => {
    tearingDownRef.current = true;
    revivingMicRef.current = false;
    iceRestartAtRef.current = 0;
    if (disconnectTimerRef.current) {
      window.clearTimeout(disconnectTimerRef.current);
      disconnectTimerRef.current = null;
    }
    releaseWakeLock();
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
    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch {
        /* noop */
      }
      audioCtxRef.current = null;
    }
  }, [releaseWakeLock]);

  const ensureMic = useCallback(async ({ refresh = false } = {}) => {
    const existing = localStreamRef.current;
    const live = existing?.getAudioTracks().some((t) => t.readyState === 'live' && !t.muted);
    if (existing && live && !refresh) {
      existing.getAudioTracks().forEach((t) => {
        t.enabled = true;
      });
      return existing;
    }
    if (existing) {
      existing.getTracks().forEach((t) => t.stop());
      localStreamRef.current = null;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Microfono non supportato su questo browser.');
    }
    const tryGet = (constraints) => navigator.mediaDevices.getUserMedia(constraints);
    let stream;
    try {
      stream = await tryGet({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
        video: false,
      });
    } catch {
      stream = await tryGet({ audio: true, video: false });
    }
    localStreamRef.current = stream;
    stream.getAudioTracks().forEach((t) => {
      t.enabled = true;
    });
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

  const attachLocalAudio = useCallback(async (pc, stream) => {
    const track = stream?.getAudioTracks()?.[0];
    if (!pc || !track) return;
    track.enabled = true;
    const sender = pc.getSenders().find((s) => !s.track || s.track.kind === 'audio');
    if (sender) {
      if (sender.track !== track) await sender.replaceTrack(track);
    } else {
      pc.addTrack(track, stream);
    }
    pc.getTransceivers().forEach((t) => {
      if (t.sender?.track?.kind === 'audio' || t.receiver?.track?.kind === 'audio') {
        try {
          t.direction = 'sendrecv';
        } catch {
          /* transceiver già chiuso */
        }
      }
    });
    await waitTrackUnmuted(track);
  }, []);

  const reviveLocalMic = useCallback(async () => {
    const pc = pcRef.current;
    if (tearingDownRef.current || revivingMicRef.current || !pc) return;
    if (pc.connectionState === 'closed' || pc.signalingState === 'closed') return;
    revivingMicRef.current = true;
    try {
      const stream = await ensureMic({ refresh: true });
      if (tearingDownRef.current || pcRef.current !== pc) return;
      await attachLocalAudio(pc, stream);
    } catch {
      /* permesso revocato o track già fermato in hangup */
    } finally {
      revivingMicRef.current = false;
    }
  }, [attachLocalAudio, ensureMic]);

  const watchLocalTracks = useCallback(
    (stream) => {
      stream?.getAudioTracks().forEach((track) => {
        const onEnded = () => {
          if (!tearingDownRef.current) reviveLocalMic();
        };
        track.addEventListener('ended', onEnded);
      });
    },
    [reviveLocalMic]
  );

  const setupPeer = useCallback(
    async (callId) => {
      if (pcRef.current) return pcRef.current;
      tearingDownRef.current = false;
      const iceServers = await ensureIce();
      const pc = new RTCPeerConnection({ iceServers, iceCandidatePoolSize: 4 });
      // Rinnova sempre il mic qui: su Android il getUserMedia di "Chiama"
      // (aperto durante lo squillo) arriva spesso muted/silenzioso all'offer.
      const stream = await ensureMic({ refresh: true });
      await attachLocalAudio(pc, stream);
      if (!pc.getSenders().some((s) => s.track?.kind === 'audio')) {
        pc.addTransceiver('audio', { direction: 'sendrecv' });
      }
      watchLocalTracks(stream);
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
        if (tearingDownRef.current || pcRef.current !== pc) return;
        if (pc.connectionState === 'connected') {
          setError('');
          if (disconnectTimerRef.current) {
            window.clearTimeout(disconnectTimerRef.current);
            disconnectTimerRef.current = null;
          }
          return;
        }
        if (pc.connectionState !== 'disconnected' && pc.connectionState !== 'failed') return;
        if (disconnectTimerRef.current) return;
        const delay = pc.connectionState === 'failed' ? 400 : 2500;
        disconnectTimerRef.current = window.setTimeout(() => {
          disconnectTimerRef.current = null;
          if (tearingDownRef.current || pcRef.current !== pc) return;
          if (pc.connectionState === 'connected' || pc.iceConnectionState === 'connected') {
            setError('');
            return;
          }
          setError('Collegamento audio instabile. Riconnessione…');
          restartIce(callId);
        }, delay);
      };
      pc.oniceconnectionstatechange = () => {
        if (tearingDownRef.current || pcRef.current !== pc) return;
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          setError('');
        }
      };
      pcRef.current = pc;
      return pc;
    },
    [attachLocalAudio, attachRemoteStream, ensureIce, ensureMic, restartIce, sendSignal, watchLocalTracks]
  );

  const createOffer = useCallback(
    async (callId) => {
      if (offerSentRef.current === callId) return;
      offerSentRef.current = callId;
      try {
        const pc = await setupPeer(callId);
        // addTrack già presente: non usare offerToReceiveAudio (secondo m-line recvonly).
        const offer = await pc.createOffer();
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
    setError('');
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
          const ctx = ensureAudioContext();
          if (ctx) {
            ctx.resume().catch(() => {});
            stopRingRef.current = startRingtone(ctx);
          }
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
    [clearCall, createOffer, ensureAudioContext, handleRemoteIce, handleRemoteSdp, selectedCharacterId]
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
            const ctx = ensureAudioContext();
            if (ctx) {
              ctx.resume().catch(() => {});
              stopRingRef.current = startRingtone(ctx);
            }
          }
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [ensureAudioContext, onLogout, chiamateAbilitate]);

  const startCall = useCallback(
    async ({ personaggioId = null, versoStaff = false } = {}) => {
      setError('');
      if (!selectedCharacterId) {
        setError('Seleziona un personaggio prima di chiamare.');
        return false;
      }
      if (!chiamateAbilitate) {
        setError('Chiamate vocali: modulo non attivo in questa campagna.');
        return false;
      }
      if (!versoStaff && !personaggioId) {
        setError('Seleziona un personaggio da chiamare.');
        return false;
      }
      setBusy(true);
      try {
        await ensureMic();
        await unlockAudioSession();
        await primeRemoteAudioElement(remoteAudioRef.current, audioCtxRef.current);
        const data = await avviaChiamataVocale(
          {
            chiamante_id: Number(selectedCharacterId),
            chiamato_id: versoStaff ? null : personaggioId,
            verso_staff: !!versoStaff,
          },
          onLogout
        );
        setCall({ ...data, ruolo: 'caller' });
        return true;
      } catch (err) {
        stopLocalMedia();
        const msg =
          err?.detail ||
          err?.data?.detail ||
          err?.message ||
          (typeof err === 'string' ? err : 'Impossibile avviare la chiamata.');
        setError(String(msg));
        return false;
      } finally {
        setBusy(false);
      }
    },
    [chiamateAbilitate, ensureMic, onLogout, selectedCharacterId, stopLocalMedia, unlockAudioSession]
  );

  const acceptCall = useCallback(async () => {
    const current = callRef.current;
    if (!current?.id) return;
    setError('');
    setBusy(true);
    try {
      if (stopRingRef.current) {
        stopRingRef.current();
        stopRingRef.current = null;
      }
      await ensureMic();
      await unlockAudioSession();
      await primeRemoteAudioElement(remoteAudioRef.current, audioCtxRef.current);
      const data = await accettaChiamataVocale(current.id, onLogout);
      setCall({ ...data, ruolo: 'callee' });
      await setupPeer(data.id);
    } catch (err) {
      stopLocalMedia();
      setError(err?.detail || err?.data?.detail || err?.message || 'Impossibile accettare.');
    } finally {
      setBusy(false);
    }
  }, [ensureMic, onLogout, setupPeer, stopLocalMedia, unlockAudioSession]);

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

  useEffect(() => {
    if (call?.stato !== 'in_corso') return undefined;

    const requestLock = async () => {
      if (!('wakeLock' in navigator) || document.visibilityState !== 'visible') return;
      try {
        wakeLockRef.current = await navigator.wakeLock.request('screen');
      } catch {
        /* policy batteria o browser senza Screen Wake Lock */
      }
    };
    requestLock();
    try {
      if (navigator.mediaSession) {
        const peer =
          call.ruolo === 'caller' ? call.chiamato?.nome : call.chiamante?.nome;
        navigator.mediaSession.metadata = new MediaMetadata({
          title: 'Chiamata vocale',
          artist: peer || 'KOR35',
        });
        navigator.mediaSession.playbackState = 'playing';
      }
    } catch {
      /* Media Session non disponibile */
    }

    const onVisible = () => {
      if (document.visibilityState !== 'visible') return;
      requestLock();
      unlockAudioSession();
      playRemote();
      reviveLocalMic();
      const pc = pcRef.current;
      if (
        pc &&
        (pc.connectionState === 'disconnected' ||
          pc.connectionState === 'failed' ||
          pc.iceConnectionState === 'disconnected' ||
          pc.iceConnectionState === 'failed')
      ) {
        restartIce(call.id);
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [call, playRemote, restartIce, reviveLocalMic, unlockAudioSession]);

  const value = useMemo(
    () => ({
      call,
      error,
      muted,
      remoteReady,
      busy,
      startCall,
      acceptCall,
      rejectCall,
      hangup,
      toggleMute,
      boostSpeaker,
    }),
    [acceptCall, boostSpeaker, busy, call, error, hangup, muted, rejectCall, remoteReady, startCall, toggleMute]
  );

  return (
    <ChiamataVocaleContext.Provider value={value}>
      {children}
      {typeof document !== 'undefined'
        ? createPortal(
            <>
              <audio
                ref={remoteAudioRef}
                autoPlay
                playsInline
                // Non usare display:none / sr-only: iOS può silenziare l'elemento.
                style={{
                  position: 'fixed',
                  left: 0,
                  bottom: 0,
                  width: 1,
                  height: 1,
                  opacity: 0.01,
                  pointerEvents: 'none',
                }}
              />
              <ChiamataVocaleOverlay
                call={call}
                error={error}
                busy={busy}
                muted={muted}
                remoteReady={remoteReady}
                acceptCall={acceptCall}
                rejectCall={rejectCall}
                hangup={hangup}
                toggleMute={toggleMute}
                boostSpeaker={boostSpeaker}
              />
            </>,
            document.body
          )
        : null}
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
      boostSpeaker: async () => {},
      busy: false,
    };
  }
  return ctx;
};
