import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import JarvisCore, { type CoreStatus } from "./JarvisCore";
import { mediaBlobToWav } from "./wav";
import { startWakeWordStream } from "./wakeWord";

// Auto-recording (triggered by the wake word, no button held) stops itself
// once the user has been quiet for this long.
const SILENCE_STOP_MS = 1100;
const SILENCE_MIN_MS = 600;
const SILENCE_MAX_MS = 12000;
const SILENCE_THRESHOLD = 0.06;

type Health = {
  status: string;
  gemini_configured: boolean;
  jarvis_conds_loaded: boolean;
  mcp_tools?: string[];
  tts_device?: string;
  wake_word_loaded?: boolean;
};

type ToolEvent = {
  name: string;
  args?: Record<string, unknown>;
  result_preview?: string;
};

type Status =
  | "idle"
  | "recording"
  | "transcribing"
  | "thinking"
  | "tool"
  | "speaking"
  | "error";

function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

function statusLabel(status: Status, tool: string): string {
  switch (status) {
    case "idle":
      return "Systems nominal — hold to speak";
    case "recording":
      return "Listening…";
    case "transcribing":
      return "Parsing audio…";
    case "thinking":
      return "Processing request…";
    case "tool":
      return tool ? `Accessing ${tool.replace(/_/g, " ")}…` : "Consulting systems…";
    case "speaking":
      return "Speaking…";
    case "error":
      return "Fault detected";
    default:
      return status;
  }
}

function playWavBase64(
  b64: string,
  audioRef: MutableRefObject<HTMLAudioElement | null>
): HTMLAudioElement {
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

function pumpLevel(
  analyser: AnalyserNode,
  levelRef: MutableRefObject<number>,
  active: () => boolean
): () => void {
  const data = new Uint8Array(analyser.fftSize);
  let raf = 0;
  const tick = () => {
    if (!active()) {
      levelRef.current = 0;
      return;
    }
    analyser.getByteTimeDomainData(data);
    let sumSq = 0;
    for (let i = 0; i < data.length; i++) {
      const v = (data[i]! - 128) / 128;
      sumSq += v * v;
    }
    const rms = Math.sqrt(sumSq / data.length);
    levelRef.current = Math.min(1, rms * 3.4);
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [error, setError] = useState("");
  const [activeTool, setActiveTool] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const levelRef = useRef(0);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const stopMicLevelRef = useRef<(() => void) | null>(null);
  const stopPlaybackLevelRef = useRef<(() => void) | null>(null);
  const mediaSourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const statusRef = useRef<Status>("idle");
  const silenceWatchRef = useRef<(() => void) | null>(null);
  const wakeStopRef = useRef<(() => void) | null>(null);
  const [wakeActive, setWakeActive] = useState(false);

  statusRef.current = status;

  const getAudioCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      const Ctor =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      audioCtxRef.current = new Ctor();
    }
    return audioCtxRef.current;
  }, []);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((data: Health) => setHealth(data))
      .catch(() =>
        setHealth({
          status: "down",
          gemini_configured: false,
          jarvis_conds_loaded: false,
        })
      );
  }, []);

  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    stopPlaybackLevelRef.current?.();
    levelRef.current = 0;
  }, []);

  const sendAudio = useCallback(
    async (blob: Blob) => {
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
        const msg = JSON.parse(String(ev.data)) as Record<string, unknown>;
        const type = String(msg.type || "");

        if (type === "status") {
          const s = String(msg.status || "thinking") as Status;
          setStatus(s);
          if (s === "tool") setActiveTool(String(msg.tool || ""));
        } else if (type === "transcript") {
          setTranscript(String(msg.text || ""));
        } else if (type === "tool") {
          setTools((prev) => [
            ...prev,
            {
              name: String(msg.name || ""),
              args: (msg.args as Record<string, unknown>) || {},
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
            // createMediaElementSource can only be called once per element
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
              levelRef,
              () => !audio.paused && !audio.ended
            );
            audio.addEventListener(
              "ended",
              () => {
                stopPlaybackLevelRef.current?.();
                levelRef.current = 0;
                setStatus("idle");
              },
              { once: true }
            );
          } catch {
            // Visual fallback without Web Audio
          }
        } else if (type === "done") {
          // keep speaking until audio ends if audio arrived; otherwise idle
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
        setError("WebSocket error — is the gateway running on :8000?");
        setStatus("error");
      };
    },
    [getAudioCtx]
  );

  const startRecording = useCallback(async () => {
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
        stopMicLevelRef.current = pumpLevel(
          analyser,
          levelRef,
          () => recorder.state === "recording"
        );
      } catch {
        // optional mic reactivity
      }

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stopMicLevelRef.current?.();
        levelRef.current = 0;
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mime });
        void (async () => {
          try {
            const wav = await mediaBlobToWav(blob);
            await sendAudio(wav);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Audio convert failed");
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
  }, [sendAudio, stopPlayback, getAudioCtx]);

  const stopRecording = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== "inactive") rec.stop();
  }, []);

  // Hands-free capture (wake word triggered, no button held): auto-stop once
  // the user goes quiet, so we still need a natural end-of-turn signal.
  const armSilenceStop = useCallback(() => {
    silenceWatchRef.current?.();
    const startedAt = performance.now();
    let lastLoud = startedAt;
    let raf = 0;
    const tick = () => {
      const now = performance.now();
      if (levelRef.current > SILENCE_THRESHOLD) lastLoud = now;
      const elapsed = now - startedAt;
      if (mediaRecorderRef.current?.state !== "recording") return;
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
  }, [startRecording, armSilenceStop]);

  useEffect(() => {
    return () => wakeStopRef.current?.();
  }, []);

  const toggleWakeWord = useCallback(async () => {
    if (wakeStopRef.current) {
      wakeStopRef.current();
      wakeStopRef.current = null;
      setWakeActive(false);
      return;
    }
    try {
      const stop = await startWakeWordStream(
        wsUrl("/ws/wake"),
        () => {
          if (statusRef.current === "idle") void startHandsFreeRecording();
        },
        (message) => setError(message)
      );
      wakeStopRef.current = stop;
      setWakeActive(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone permission denied");
    }
  }, [startHandsFreeRecording]);

  const busy = status !== "idle" && status !== "recording" && status !== "error";
  const recording = status === "recording";

  return (
    <div className="hud">
      <div className="hud-bg" aria-hidden />

      <header className="hud-top">
        <div className="mark">
          <span className="mark-title">J.A.R.V.I.S.</span>
          <span className="mark-sub">Just A Rather Very Intelligent System</span>
        </div>
        <div className="telemetry">
          {health ? (
            <>
              <span className={health.status === "ok" ? "ok" : "bad"}>
                CORE {health.status.toUpperCase()}
              </span>
              <span>{health.gemini_configured ? "LLM LINKED" : "LLM OFFLINE"}</span>
              <span>{health.jarvis_conds_loaded ? "VOICE READY" : "VOICE MISSING"}</span>
            </>
          ) : (
            <span>BOOTING…</span>
          )}
          {health?.wake_word_loaded ? (
            <button
              type="button"
              className={`wake-toggle ${wakeActive ? "on" : ""}`}
              onClick={() => void toggleWakeWord()}
            >
              {wakeActive ? "WAKE WORD: “HEY JARVIS”" : "ENABLE WAKE WORD"}
            </button>
          ) : health ? (
            <span className="bad" title="openWakeWord failed to load on the gateway">
              WAKE WORD UNAVAILABLE
            </span>
          ) : null}
        </div>
      </header>

      <main className="hud-stage">
        <button
          type="button"
          className={`orb-hit ${recording ? "live" : ""} ${busy ? "busy" : ""}`}
          disabled={busy}
          aria-label={recording ? "Release to send" : "Hold to talk"}
          onMouseDown={() => void startRecording()}
          onMouseUp={stopRecording}
          onMouseLeave={() => {
            if (recording) stopRecording();
          }}
          onTouchStart={(e) => {
            e.preventDefault();
            void startRecording();
          }}
          onTouchEnd={(e) => {
            e.preventDefault();
            stopRecording();
          }}
        >
          <JarvisCore status={status as CoreStatus} levelRef={levelRef} size={440} />
        </button>

        <p className={`orb-status ${status}`}>{statusLabel(status, activeTool)}</p>
        <p className="orb-hint">
          {recording ? "Release to send" : busy ? "Please wait" : "Hold the orb to talk"}
        </p>

        {error ? <p className="error">{error}</p> : null}

        <div className="caption-rail">
          <div className="caption">
            <span className="caption-k">You</span>
            <p>{transcript || "—"}</p>
          </div>
          <div className="caption">
            <span className="caption-k">Jarvis</span>
            <p>{reply || "—"}</p>
          </div>
        </div>

        {tools.length > 0 ? (
          <div className="tool-rail">
            {tools.map((t, i) => (
              <div className="tool-chip" key={`${t.name}-${i}`}>
                <strong>{t.name}</strong>
                <span>{t.result_preview}</span>
              </div>
            ))}
          </div>
        ) : null}

        <button type="button" className="ghost-stop" onClick={stopPlayback}>
          Silence
        </button>
      </main>
    </div>
  );
}
