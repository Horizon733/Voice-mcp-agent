import { useCallback, useEffect, useRef, useState } from "react";
import Scene from "./components/Scene";
import DashboardOverlay from "./components/DashboardOverlay";
import { mediaBlobToWav } from "./wav";
import { startWakeWordStream } from "./wakeWord";
import "./App.css";

const SILENCE_STOP_MS = 1100;
const SILENCE_MIN_MS = 600;
const SILENCE_MAX_MS = 12000;
const SILENCE_THRESHOLD = 0.06;

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

function statusLabel(status, tool) {
  switch (status) {
    case "idle":
      return "Systems nominal - hold to speak";
    case "recording":
      return "Listening";
    case "transcribing":
      return "Parsing audio";
    case "thinking":
      return "Processing request";
    case "tool":
      return tool ? `Accessing ${tool.replace(/_/g, " ")}` : "Consulting systems";
    case "speaking":
      return "Speaking";
    case "error":
      return "Fault detected";
    default:
      return status;
  }
}

function playWavBase64(b64, audioRef) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const blob = new Blob([bytes], { type: "audio/wav" });
  const url = URL.createObjectURL(blob);
  if (audioRef.current) {
    audioRef.current.pause();
    URL.revokeObjectURL(audioRef.current.src);
  }
  const audio = new Audio(url);
  audioRef.current = audio;
  void audio.play();
  return audio;
}

function pumpLevel(analyser, onLevel, active) {
  const data = new Uint8Array(analyser.fftSize);
  let raf = 0;
  let lastCommit = 0;
  const tick = (t) => {
    if (!active()) {
      onLevel(0);
      return;
    }
    analyser.getByteTimeDomainData(data);
    let sumSq = 0;
    for (let i = 0; i < data.length; i++) {
      const v = (data[i] - 128) / 128;
      sumSq += v * v;
    }
    const rms = Math.sqrt(sumSq / data.length);
    const level = Math.min(1, rms * 3.4);
    if (t - lastCommit > 45) {
      onLevel(level);
      lastCommit = t;
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [status, setStatus] = useState("idle");
  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");
  const [tools, setTools] = useState([]);
  const [error, setError] = useState("");
  const [activeTool, setActiveTool] = useState("");
  const [wakeActive, setWakeActive] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioRef = useRef(null);
  const levelRef = useRef(0);
  const audioCtxRef = useRef(null);
  const stopMicLevelRef = useRef(null);
  const stopPlaybackLevelRef = useRef(null);
  const mediaSourceRef = useRef(null);
  const silenceWatchRef = useRef(null);
  const wakeStopRef = useRef(null);
  const wakeWantedRef = useRef(false);
  const statusRef = useRef("idle");

  statusRef.current = status;

  const getAudioCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      const Ctor = window.AudioContext || window.webkitAudioContext;
      audioCtxRef.current = new Ctor();
    }
    return audioCtxRef.current;
  }, []);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((data) => setHealth(data))
      .catch(() =>
        setHealth({
          status: "down",
          gemini_configured: false,
          jarvis_conds_loaded: false,
          wake_word_loaded: false,
        })
      );
  }, []);

  useEffect(() => {
    return () => {
      wakeStopRef.current?.();
      silenceWatchRef.current?.();
      stopMicLevelRef.current?.();
      stopPlaybackLevelRef.current?.();
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  const setLevel = useCallback((level) => {
    levelRef.current = level;
    setAudioLevel(level);
  }, []);

  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    stopPlaybackLevelRef.current?.();
    setLevel(0);
  }, [setLevel]);

  const sendAudio = useCallback(
    async (blob) => {
      setStatus("transcribing");
      setError("");
      setTools([]);
      setActiveTool("");

      const ws = new WebSocket(wsUrl("/ws/turn"));
      ws.binaryType = "arraybuffer";

      ws.onopen = async () => {
        const buffer = await blob.arrayBuffer();
        ws.send(buffer);
      };

      ws.onmessage = (ev) => {
        const msg = JSON.parse(String(ev.data));
        const type = String(msg.type || "");

        if (type === "status") {
          const nextStatus = String(msg.status || "thinking");
          setStatus(nextStatus);
          if (nextStatus === "tool") {
            setActiveTool(String(msg.tool || ""));
          }
        } else if (type === "transcript") {
          setTranscript(String(msg.text || ""));
        } else if (type === "tool") {
          setTools((prev) => [
            ...prev,
            {
              name: String(msg.name || ""),
              args: msg.args || {},
              result_preview: String(msg.result_preview || ""),
            },
          ]);
        } else if (type === "reply_text") {
          setReply(String(msg.text || ""));
        } else if (type === "audio") {
          const audio = playWavBase64(String(msg.base64 || ""), audioRef);
          setStatus("speaking");
          try {
            const audioCtx = getAudioCtx();
            void audioCtx.resume();
            let source = mediaSourceRef.current;
            if (!source || source.mediaElement !== audio) {
              source = audioCtx.createMediaElementSource(audio);
              mediaSourceRef.current = source;
            }
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            source.disconnect();
            source.connect(analyser);
            analyser.connect(audioCtx.destination);
            stopPlaybackLevelRef.current?.();
            stopPlaybackLevelRef.current = pumpLevel(
              analyser,
              setLevel,
              () => !audio.paused && !audio.ended
            );
            audio.addEventListener(
              "ended",
              () => {
                stopPlaybackLevelRef.current?.();
                setLevel(0);
                setStatus("idle");
              },
              { once: true }
            );
          } catch {
            // Continue without visual playback level reactivity.
          }
        } else if (type === "done") {
          setActiveTool("");
          if (!audioRef.current || audioRef.current.ended || audioRef.current.paused) {
            setStatus((s) => (s === "speaking" ? s : "idle"));
          }
        } else if (type === "error") {
          setError(String(msg.message || "Unknown error"));
          setStatus("error");
        }
      };

      ws.onerror = () => {
        setError("WebSocket error - is the gateway running on :8000?");
        setStatus("error");
      };
    },
    [getAudioCtx, setLevel]
  );

  const startRecording = useCallback(async () => {
    // Avoid two simultaneous mic pipelines (wake listener + recorder) on
    // drivers that allow wake-word only once unless the stream is re-opened.
    if (wakeStopRef.current) {
      wakeStopRef.current();
      wakeStopRef.current = null;
      setWakeActive(false);
    }

    stopPlayback();
    setError("");
    setTranscript("");
    setReply("");
    setTools([]);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      chunksRef.current = [];

      try {
        const audioCtx = getAudioCtx();
        void audioCtx.resume();
        const micSource = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        micSource.connect(analyser);
        stopMicLevelRef.current?.();
        stopMicLevelRef.current = pumpLevel(analyser, setLevel, () => recorder.state === "recording");
      } catch {
        // Mic meter is optional.
      }

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        stopMicLevelRef.current?.();
        setLevel(0);
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mime });
        void (async () => {
          try {
            const wav = await mediaBlobToWav(blob);
            await sendAudio(wav);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Audio conversion failed");
            setStatus("error");
          }
        })();
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone permission denied");
      setStatus("error");
    }
  }, [getAudioCtx, sendAudio, setLevel, stopPlayback]);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }, []);

  const armSilenceStop = useCallback(() => {
    silenceWatchRef.current?.();
    const startedAt = performance.now();
    let lastLoud = startedAt;
    let raf = 0;

    const tick = () => {
      const now = performance.now();
      if (levelRef.current > SILENCE_THRESHOLD) {
        lastLoud = now;
      }
      const elapsed = now - startedAt;
      if (mediaRecorderRef.current?.state !== "recording") {
        return;
      }
      if ((elapsed > SILENCE_MIN_MS && now - lastLoud > SILENCE_STOP_MS) || elapsed > SILENCE_MAX_MS) {
        stopRecording();
        return;
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    silenceWatchRef.current = () => cancelAnimationFrame(raf);
  }, [stopRecording]);

  const startHandsFreeRecording = useCallback(async () => {
    await startRecording();
    armSilenceStop();
  }, [armSilenceStop, startRecording]);

  const startWakeListener = useCallback(async () => {
    if (!wakeWantedRef.current || wakeStopRef.current) {
      return;
    }

    try {
      const stop = await startWakeWordStream(
        wsUrl("/ws/wake"),
        () => {
          if (statusRef.current === "idle") {
            // Pause wake listener during capture/turn; it will auto-rearm on idle.
            wakeStopRef.current?.();
            wakeStopRef.current = null;
            setWakeActive(false);
            void startHandsFreeRecording();
          }
        },
        (message) => setError(message)
      );
      wakeStopRef.current = stop;
      setWakeActive(true);
    } catch (err) {
      wakeWantedRef.current = false;
      setWakeActive(false);
      setError(err instanceof Error ? err.message : "Microphone permission denied");
    }
  }, [startHandsFreeRecording]);

  useEffect(() => {
    if (wakeWantedRef.current && !wakeStopRef.current && status === "idle") {
      void startWakeListener();
    }
  }, [status, startWakeListener]);

  const toggleWakeWord = useCallback(async () => {
    if (wakeWantedRef.current) {
      wakeWantedRef.current = false;
      wakeStopRef.current?.();
      wakeStopRef.current = null;
      setWakeActive(false);
      return;
    }

    wakeWantedRef.current = true;
    await startWakeListener();
  }, [startWakeListener]);

  const busy = status !== "idle" && status !== "recording" && status !== "error";
  const recording = status === "recording";

  return (
    <div className="app-shell">
      <Scene audioLevel={audioLevel} />
      <DashboardOverlay
        health={health}
        status={status}
        statusText={statusLabel(status, activeTool)}
        transcript={transcript}
        reply={reply}
        tools={tools}
        error={error}
        wakeActive={wakeActive}
        busy={busy}
        recording={recording}
        onToggleWakeWord={() => void toggleWakeWord()}
        onStartRecording={() => void startRecording()}
        onStopRecording={stopRecording}
        onStopPlayback={stopPlayback}
      />
    </div>
  );
}