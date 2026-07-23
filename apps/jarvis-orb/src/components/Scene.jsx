import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { EffectComposer, Bloom, Noise } from "@react-three/postprocessing";
import * as THREE from "three";

import Orb from "./Orb";
export default function Scene({ audioLevel = 0 }) {

  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true }}
      camera={{
        position: [0, 0, 4.8],
        fov: 42,
      }}
      onCreated={({ gl }) => {
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 0.92;
      }}
    >
      <color attach="background" args={["#060810"]} />

      <ambientLight intensity={0.04} />

      <hemisphereLight
        args={["#2a3f68", "#080a12", 0.18]}
      />

      <pointLight
        position={[2.2, 1.8, 2.8]}
        intensity={0.8 + audioLevel * 1.1}
        color="#ffb24a"
      />

      <pointLight
        position={[-2.4, -0.8, -1.4]}
        intensity={0.24 + audioLevel * 0.5}
        color="#ff8b2a"
      />

      <Orb audioLevel={audioLevel} />

      <EffectComposer>
        <Bloom
          intensity={0.12 + audioLevel * 0.12}
          luminanceThreshold={0.55}
          luminanceSmoothing={0.12}
          radius={0.18 + audioLevel * 0.04}
        />
        <Noise opacity={0.002} premultiply />
      </EffectComposer>

      <OrbitControls
        enableZoom={false}
        enablePan={false}
        minAzimuthAngle={-0.7}
        maxAzimuthAngle={0.7}
        minPolarAngle={1.15}
        maxPolarAngle={1.95}
      />
    </Canvas>
  );
}