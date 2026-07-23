/**
 * Streams the mic (downsampled to 16kHz mono PCM16) to the gateway's
 * /ws/wake endpoint, which runs openWakeWord ("hey jarvis") server-side.
 * Fully local — no third-party account/key required.
 */
function floatTo16BitPCM(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

export async function startWakeWordStream(
  wakeWsUrl: string,
  onWake: () => void,
  onError: (message: string) => void
): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const AudioCtor =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioCtor();
  const source = ctx.createMediaStreamSource(stream);
  // ScriptProcessorNode is deprecated but remains the simplest cross-browser
  // way to get raw PCM frames without shipping an AudioWorklet bundle.
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const mute = ctx.createGain();
  mute.gain.value = 0; // processing runs without echoing the mic to speakers

  const ratio = ctx.sampleRate / 16000;

  const ws = new WebSocket(wakeWsUrl);
  ws.binaryType = "arraybuffer";

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(String(ev.data)) as Record<string, unknown>;
      if (msg.type === "wake") onWake();
      else if (msg.type === "error") onError(String(msg.message || "Wake-word error"));
    } catch {
      // ignore malformed frames
    }
  };
  ws.onerror = () => onError("Wake-word socket error — is the gateway running on :8000?");

  processor.onaudioprocess = (e) => {
    if (ws.readyState !== WebSocket.OPEN) return;
    const input = e.inputBuffer.getChannelData(0);
    const outLen = Math.max(1, Math.floor(input.length / ratio));
    const down = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      down[i] = input[Math.min(input.length - 1, Math.floor(i * ratio))];
    }
    ws.send(floatTo16BitPCM(down).buffer);
  };

  source.connect(processor);
  processor.connect(mute);
  mute.connect(ctx.destination);

  return () => {
    try {
      processor.disconnect();
    } catch {
      /* already disconnected */
    }
    try {
      source.disconnect();
    } catch {
      /* already disconnected */
    }
    try {
      mute.disconnect();
    } catch {
      /* already disconnected */
    }
    void ctx.close();
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close();
    stream.getTracks().forEach((t) => t.stop());
  };
}
