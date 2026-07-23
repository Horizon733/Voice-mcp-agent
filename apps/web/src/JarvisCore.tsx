import { useEffect, useRef, type MutableRefObject } from "react";

export type CoreStatus =
  | "idle"
  | "recording"
  | "transcribing"
  | "thinking"
  | "tool"
  | "speaking"
  | "error";

type Palette = {
  hot: string;
  mid: string;
  cool: string;
  glow: string;
};

/** Keep the Iron-Man gold look across states; vary intensity / cool accents only. */
const PALETTES: Record<CoreStatus, Palette> = {
  idle: {
    hot: "rgba(255, 210, 120, 0.95)",
    mid: "rgba(255, 160, 60, 0.55)",
    cool: "rgba(255, 140, 50, 0.22)",
    glow: "rgba(255, 150, 50, 0.28)",
  },
  recording: {
    hot: "rgba(255, 236, 180, 1)",
    mid: "rgba(255, 190, 80, 0.85)",
    cool: "rgba(255, 170, 70, 0.35)",
    glow: "rgba(255, 180, 60, 0.5)",
  },
  transcribing: {
    hot: "rgba(255, 220, 150, 1)",
    mid: "rgba(255, 170, 70, 0.75)",
    cool: "rgba(180, 220, 255, 0.28)",
    glow: "rgba(255, 160, 50, 0.42)",
  },
  thinking: {
    hot: "rgba(255, 200, 110, 1)",
    mid: "rgba(255, 150, 55, 0.8)",
    cool: "rgba(255, 120, 40, 0.35)",
    glow: "rgba(255, 140, 40, 0.48)",
  },
  tool: {
    hot: "rgba(255, 230, 160, 1)",
    mid: "rgba(255, 175, 70, 0.85)",
    cool: "rgba(120, 220, 200, 0.3)",
    glow: "rgba(255, 160, 50, 0.45)",
  },
  speaking: {
    hot: "rgba(255, 245, 200, 1)",
    mid: "rgba(255, 190, 80, 0.95)",
    cool: "rgba(255, 150, 50, 0.4)",
    glow: "rgba(255, 170, 50, 0.62)",
  },
  error: {
    hot: "rgba(255, 160, 120, 1)",
    mid: "rgba(255, 90, 70, 0.75)",
    cool: "rgba(255, 70, 50, 0.3)",
    glow: "rgba(255, 80, 50, 0.45)",
  },
};

const SPIN: Record<CoreStatus, number> = {
  idle: 0.35,
  recording: 0.9,
  transcribing: 1.8,
  thinking: 2.4,
  tool: 3.2,
  speaking: 1.1,
  error: 4.0,
};

const BEAT_HZ: Record<CoreStatus, number> = {
  idle: 0.18,
  recording: 0,
  transcribing: 2.1,
  thinking: 1.35,
  tool: 2.8,
  speaking: 0,
  error: 3.6,
};

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function project(
  x: number,
  y: number,
  z: number,
  rotY: number,
  rotX: number
): { x: number; y: number; z: number } {
  // rotate Y
  const cosY = Math.cos(rotY);
  const sinY = Math.sin(rotY);
  let x1 = x * cosY - z * sinY;
  let z1 = x * sinY + z * cosY;
  // rotate X
  const cosX = Math.cos(rotX);
  const sinX = Math.sin(rotX);
  const y1 = y * cosX - z1 * sinX;
  const z2 = y * sinX + z1 * cosX;
  return { x: x1, y: y1, z: z2 };
}

export default function JarvisCore({
  status,
  levelRef,
  size = 420,
}: {
  status: CoreStatus;
  levelRef: MutableRefObject<number>;
  size?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const statusRef = useRef(status);
  const smoothedLevel = useRef(0);
  statusRef.current = status;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Precompute meridian / parallel samples for a dense mesh look
    const meridians = 18;
    const parallels = 12;
    const shellScales = [0.55, 0.78, 1.0, 1.18];
    const arcSeeds = Array.from({ length: 28 }, (_, i) => ({
      a: (i / 28) * Math.PI * 2,
      b: ((i * 7) % 28) / 28 * Math.PI - Math.PI / 2,
      len: 0.35 + (i % 5) * 0.08,
      shell: i % shellScales.length,
    }));

    let raf = 0;
    const start = performance.now();

    const draw = (now: number) => {
      const t = (now - start) / 1000;
      const st = statusRef.current;
      const palette = PALETTES[st];
      const spin = SPIN[st];
      const freq = BEAT_HZ[st];

      const beat = freq > 0 ? 0.5 + 0.5 * Math.sin(t * freq * Math.PI * 2) : 0;
      const rawLevel = levelRef.current || 0;
      smoothedLevel.current = lerp(smoothedLevel.current, rawLevel, 0.32);
      const audioLevel = smoothedLevel.current;

      // Speaking / listening: real audio. Understanding/loading: synthetic vibration.
      const pulse =
        st === "speaking" || st === "recording"
          ? audioLevel
          : Math.max(audioLevel * 0.2, beat * (st === "idle" ? 0.25 : 0.85));

      const vibrate = pulse * (st === "speaking" ? 1.0 : st === "thinking" || st === "transcribing" || st === "tool" ? 0.7 : 0.35);
      const scaleBreath = 1 + vibrate * 0.12 + (st === "speaking" ? audioLevel * 0.08 : 0);

      const cx = size / 2;
      const cy = size / 2;
      const R = size * 0.28 * scaleBreath;

      ctx.clearRect(0, 0, size, size);

      // Soft volumetric glow
      const glowR = R * (2.1 + pulse * 0.9);
      const glow = ctx.createRadialGradient(cx, cy, R * 0.15, cx, cy, glowR);
      glow.addColorStop(0, palette.glow);
      glow.addColorStop(0.45, "rgba(255,140,40,0.08)");
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, glowR, 0, Math.PI * 2);
      ctx.fill();

      const rotY = t * spin;
      const rotX = Math.sin(t * 0.4) * 0.35 + (st === "thinking" ? t * 0.6 : 0);

      const drawEllipseRing = (
        radius: number,
        tilt: number,
        yaw: number,
        color: string,
        width: number,
        alpha = 1
      ) => {
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        let first = true;
        for (let i = 0; i <= 64; i++) {
          const a = (i / 64) * Math.PI * 2;
          const x = Math.cos(a) * radius;
          const y = Math.sin(a) * radius * Math.cos(tilt);
          const z = Math.sin(a) * radius * Math.sin(tilt);
          const p = project(x, y, z, rotY + yaw, rotX);
          const depth = (p.z / radius + 1) * 0.5;
          const sx = cx + p.x;
          const sy = cy + p.y * 0.92;
          if (first) {
            ctx.moveTo(sx, sy);
            first = false;
          } else {
            ctx.lineTo(sx, sy);
          }
          // depth-ish: thicker strokes redrawn selectively via alpha already
          void depth;
        }
        ctx.stroke();
        ctx.restore();
      };

      // Nested shells
      for (let s = 0; s < shellScales.length; s++) {
        const rs = R * shellScales[s];
        const alpha = 0.25 + s * 0.12 + pulse * 0.15;
        for (let m = 0; m < meridians; m++) {
          const yaw = (m / meridians) * Math.PI;
          drawEllipseRing(
            rs,
            Math.PI / 2,
            yaw,
            m % 3 === 0 ? palette.hot : palette.mid,
            m % 3 === 0 ? 1.15 : 0.6,
            alpha * (0.35 + (m % 3 === 0 ? 0.35 : 0.15))
          );
        }
        for (let p = 0; p < parallels; p++) {
          const lat = -0.85 + (p / (parallels - 1)) * 1.7;
          const rr = rs * Math.cos(lat);
          const oy = rs * Math.sin(lat);
          ctx.save();
          ctx.globalAlpha = alpha * 0.35;
          ctx.strokeStyle = palette.cool;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          for (let i = 0; i <= 72; i++) {
            const a = (i / 72) * Math.PI * 2;
            const x = Math.cos(a) * rr;
            const y = oy;
            const z = Math.sin(a) * rr;
            const pt = project(x, y, z, rotY * (1 + s * 0.08), rotX);
            const sx = cx + pt.x;
            const sy = cy + pt.y * 0.92;
            if (i === 0) ctx.moveTo(sx, sy);
            else ctx.lineTo(sx, sy);
          }
          ctx.closePath();
          ctx.stroke();
          ctx.restore();
        }
      }

      // Schematic arc ticks (hologram “data rings”)
      for (const arc of arcSeeds) {
        const rs = R * shellScales[arc.shell] * (1.02 + pulse * 0.05);
        ctx.save();
        ctx.globalAlpha = 0.45 + pulse * 0.35;
        ctx.strokeStyle = palette.hot;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        const steps = 18;
        for (let i = 0; i <= steps; i++) {
          const u = i / steps;
          const a = arc.a + u * arc.len + t * (0.2 + arc.shell * 0.05) * (arc.shell % 2 === 0 ? 1 : -1);
          const lat = arc.b;
          const x = Math.cos(a) * Math.cos(lat) * rs;
          const y = Math.sin(lat) * rs;
          const z = Math.sin(a) * Math.cos(lat) * rs;
          const pt = project(x, y, z, rotY, rotX);
          const sx = cx + pt.x;
          const sy = cy + pt.y * 0.92;
          if (i === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        }
        ctx.stroke();
        ctx.restore();
      }

      // Speckle nodes
      const nodes = 90;
      for (let i = 0; i < nodes; i++) {
        const u = (i * 0.618033) % 1;
        const v = (i * 0.381966) % 1;
        const theta = u * Math.PI * 2 + t * 0.15;
        const phi = Math.acos(2 * v - 1);
        const rs = R * (0.7 + (i % 4) * 0.12);
        const x = Math.sin(phi) * Math.cos(theta) * rs;
        const y = Math.cos(phi) * rs;
        const z = Math.sin(phi) * Math.sin(theta) * rs;
        const pt = project(x, y, z, rotY, rotX);
        if (pt.z < -R * 0.15) continue;
        const depth = (pt.z / R + 1) * 0.5;
        const rad = (0.6 + depth * 1.4) * (1 + pulse * 0.8);
        ctx.beginPath();
        ctx.fillStyle = depth > 0.55 ? palette.hot : palette.mid;
        ctx.globalAlpha = 0.35 + depth * 0.55;
        ctx.arc(cx + pt.x, cy + pt.y * 0.92, rad, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // Bright core — beats harder when speaking
      const coreR = R * (0.22 + pulse * 0.28 + (st === "speaking" ? audioLevel * 0.2 : 0));
      const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR * 1.8);
      core.addColorStop(0, "#fff8e8");
      core.addColorStop(0.25, palette.hot);
      core.addColorStop(0.65, "rgba(255,140,40,0.35)");
      core.addColorStop(1, "rgba(0,0,0,0)");
      ctx.beginPath();
      ctx.fillStyle = core;
      ctx.arc(cx, cy, coreR * 1.8, 0, Math.PI * 2);
      ctx.fill();

      // Micro shake while understanding / loading
      if (st === "thinking" || st === "transcribing" || st === "tool") {
        const shake = Math.sin(t * 40) * vibrate * 1.8;
        canvas.style.transform = `translate(${shake}px, ${-shake * 0.6}px)`;
      } else if (st === "speaking") {
        const shake = Math.sin(t * 28) * audioLevel * 2.4;
        canvas.style.transform = `translate(${shake}px, ${shake * 0.4}px) scale(${1 + audioLevel * 0.03})`;
      } else {
        canvas.style.transform = "translate(0,0)";
      }

      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      canvas.style.transform = "";
    };
  }, [size, levelRef]);

  return (
    <canvas
      ref={canvasRef}
      className="jarvis-orb-canvas"
      style={{ width: size, height: size, display: "block" }}
      aria-hidden
    />
  );
}
