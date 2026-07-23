import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function Particles({ audioLevel = 0 }) {
  const points = useRef();
  const materialRef = useRef();
  const audioRef = useRef(0);

  const { positions, sizes, seeds, count } = useMemo(() => {
    const count = 1800;

    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    const seeds = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const spread = Math.pow(Math.random(), 0.65);
      const r = 1.5 + spread * 2.1;

      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;

      positions[i * 3] =
        r * Math.sin(phi) * Math.cos(theta);

      positions[i * 3 + 1] =
        r * Math.sin(phi) * Math.sin(theta);

      positions[i * 3 + 2] =
        r * Math.cos(phi);

      sizes[i] = 0.28 + Math.random() * 0.88;
      seeds[i] = Math.random() * Math.PI * 2;
    }

    return { positions, sizes, seeds, count };
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    audioRef.current = THREE.MathUtils.lerp(audioRef.current, audioLevel, 0.15);
    const speechGate = THREE.MathUtils.smoothstep(audioRef.current, 0.05, 0.22);
    const beat = 0.5 + 0.5 * Math.sin(t * 0.72);
    const breath = THREE.MathUtils.smoothstep(beat, 0.2, 1.0) * speechGate;

    if (points.current) {
      points.current.rotation.y = t * 0.04;
      points.current.rotation.x = Math.sin(t * 0.12) * 0.05;
      const s = 1 + breath * 0.03 + audioRef.current * 0.02;
      points.current.scale.set(s, s, s);
    }

    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = t;
      materialRef.current.uniforms.uAudio.value = audioRef.current;
      materialRef.current.uniforms.uBeat.value = breath;
    }
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={count}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aSize"
          array={sizes}
          count={count}
          itemSize={1}
        />
        <bufferAttribute
          attach="attributes-aSeed"
          array={seeds}
          count={count}
          itemSize={1}
        />
      </bufferGeometry>

      <shaderMaterial
        ref={materialRef}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        uniforms={{
          uTime: { value: 0 },
          uAudio: { value: 0 },
          uBeat: { value: 0 }
        }}
        vertexShader={`
          uniform float uTime;
          uniform float uAudio;
          uniform float uBeat;
          attribute float aSize;
          attribute float aSeed;

          varying float vAlpha;

          void main() {
            vec3 p = position;
            float twinkle = 0.42 + 0.22 * sin(uTime * 1.4 + aSeed) + uBeat * 0.2 + uAudio * 0.28;
            vAlpha = twinkle;

            vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
            gl_Position = projectionMatrix * mvPosition;
            gl_PointSize = (aSize * (3.0 + uBeat * 1.2 + uAudio * 1.6) * twinkle) / -mvPosition.z;
          }
        `}
        fragmentShader={`
          varying float vAlpha;

          void main() {
            vec2 uv = gl_PointCoord - vec2(0.5);
            float d = length(uv);
            float core = smoothstep(0.2, 0.0, d);
            float halo = smoothstep(0.5, 0.18, d);
            vec3 color = mix(vec3(1.0, 0.62, 0.2), vec3(1.0, 0.9, 0.65), core);
            float alpha = (halo * 0.15 + core * 0.2) * vAlpha;

            gl_FragColor = vec4(color, alpha);
          }
        `}
      />
    </points>
  );
}