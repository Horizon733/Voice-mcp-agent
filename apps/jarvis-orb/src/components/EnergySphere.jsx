import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function EnergySphere({ audioLevel = 0 }) {
  const root = useRef();
  const shellGroup = useRef();
  const ringGroup = useRef();
  const audioLevelRef = useRef(0);

  const ringData = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => ({
      radius: 1.0 + Math.random() * 0.3,
      thickness: 0.0016 + (i % 3) * 0.0005,
      rotX: Math.random() * Math.PI,
      rotY: Math.random() * Math.PI,
      speed: 0.012 + Math.random() * 0.02,
      phase: Math.random() * Math.PI * 2,
      arcLength: (Math.PI * 2) * (0.32 + Math.random() * 0.24)
    }));
  }, []);

  const shellGeometry = useMemo(() => {
    const segmentCount = 2600;
    const arr = new Float32Array(segmentCount * 2 * 3);
    const up = new THREE.Vector3(0, 1, 0);
    const hotAxis = new THREE.Vector3(0.9, 0.2, 0.25).normalize();

    for (let i = 0; i < segmentCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(1 - 2 * Math.random());

      const normal = new THREE.Vector3(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta)
      ).normalize();

      const axisWeight = Math.max(0.0, normal.dot(hotAxis));
      const clusterBoost = Math.random() < axisWeight * 0.7 ? 1.0 : 0.0;
      const radius = 1.08 + (Math.random() - 0.5) * 0.2 + clusterBoost * 0.08;

      const center = normal.clone().multiplyScalar(radius);
      const tangentA = new THREE.Vector3().crossVectors(normal, up);
      if (tangentA.lengthSq() < 0.0001) {
        tangentA.set(1, 0, 0);
      }
      tangentA.normalize();

      const tangentB = new THREE.Vector3().crossVectors(normal, tangentA).normalize();
      const spin = Math.random() * Math.PI * 2;
      const dir = tangentA
        .clone()
        .multiplyScalar(Math.cos(spin))
        .add(tangentB.clone().multiplyScalar(Math.sin(spin)))
        .normalize();

      const len = 0.016 + Math.random() * 0.07 + clusterBoost * 0.035;
      const a = center.clone().addScaledVector(dir, -len * 0.5);
      const b = center.clone().addScaledVector(dir, len * 0.5);

      const offset = i * 6;
      arr[offset] = a.x;
      arr[offset + 1] = a.y;
      arr[offset + 2] = a.z;
      arr[offset + 3] = b.x;
      arr[offset + 4] = b.y;
      arr[offset + 5] = b.z;
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    return g;
  }, []);

  const bandGeometry = useMemo(() => {
    const bandCount = 28;
    const segmentsPerBand = 130;
    const arr = new Float32Array(bandCount * segmentsPerBand * 2 * 3);
    const hotAxis = new THREE.Vector3(0.9, 0.2, 0.25).normalize();
    let ptr = 0;

    for (let b = 0; b < bandCount; b++) {
      const lat = (Math.random() - 0.5) * Math.PI;
      const radius = 1.03 + (Math.random() - 0.5) * 0.22;
      const bandR = Math.cos(lat) * radius;
      const y = Math.sin(lat) * radius;

      for (let i = 0; i < segmentsPerBand; i++) {
        if (Math.random() < 0.4) {
          continue;
        }

        const a0 = (i / segmentsPerBand) * Math.PI * 2;
        const step = 0.03 + Math.random() * 0.07;
        const a1 = a0 + step;

        const p0 = new THREE.Vector3(
          Math.cos(a0) * bandR,
          y,
          Math.sin(a0) * bandR
        );
        const p1 = new THREE.Vector3(
          Math.cos(a1) * bandR,
          y,
          Math.sin(a1) * bandR
        );

        const mid = p0.clone().add(p1).multiplyScalar(0.5).normalize();
        const w = Math.max(0, mid.dot(hotAxis));
        if (Math.random() > 0.45 + w * 0.55) {
          continue;
        }

        arr[ptr++] = p0.x;
        arr[ptr++] = p0.y;
        arr[ptr++] = p0.z;
        arr[ptr++] = p1.x;
        arr[ptr++] = p1.y;
        arr[ptr++] = p1.z;
      }
    }

    const trimmed = arr.slice(0, ptr);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(trimmed, 3));
    return g;
  }, []);

  const circuitGeometry = useMemo(() => {
    const segmentCount = 640;
    const arr = new Float32Array(segmentCount * 2 * 3);
    const up = new THREE.Vector3(0, 1, 0);
    const hotAxis = new THREE.Vector3(0.9, 0.2, 0.25).normalize();

    for (let i = 0; i < segmentCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(1 - 2 * Math.random());
      const r = 0.45 + Math.random() * 0.56;

      const normal = new THREE.Vector3(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta)
      ).normalize();

      const bias = Math.max(0.0, normal.dot(hotAxis));
      if (Math.random() > 0.35 + bias * 0.65) {
        continue;
      }

      const p = normal.clone().multiplyScalar(r);

      const tangentA = new THREE.Vector3().crossVectors(normal, up);
      if (tangentA.lengthSq() < 0.0001) {
        tangentA.set(1, 0, 0);
      }
      tangentA.normalize();
      const tangentB = new THREE.Vector3().crossVectors(normal, tangentA).normalize();
      const dir = tangentA
        .clone()
        .multiplyScalar(Math.cos(theta * 2.0))
        .add(tangentB.clone().multiplyScalar(Math.sin(theta * 2.0)))
        .normalize();

      const drift = dir.multiplyScalar((Math.random() - 0.5) * (0.04 + Math.random() * 0.14));

      const p2 = p.clone().add(drift);
      if (p2.length() > 1.12) {
        p2.setLength(1.12);
      }

      const offset = i * 6;
      arr[offset] = p.x;
      arr[offset + 1] = p.y;
      arr[offset + 2] = p.z;
      arr[offset + 3] = p2.x;
      arr[offset + 4] = p2.y;
      arr[offset + 5] = p2.z;
    }

    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    return g;
  }, []);

  const radialGeometry = useMemo(() => {
    const segmentCount = 34;
    const arr = new Float32Array(segmentCount * 2 * 3);
    const hotAxis = new THREE.Vector3(0.9, 0.2, 0.25).normalize();
    let ptr = 0;

    for (let i = 0; i < segmentCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(1 - 2 * Math.random());

      const normal = new THREE.Vector3(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta)
      ).normalize();

      if (Math.random() > 0.35 + Math.max(0.0, normal.dot(hotAxis)) * 0.65) {
        continue;
      }

      const a = normal.clone().multiplyScalar(0.15 + Math.random() * 0.12);
      const b = normal.clone().multiplyScalar(0.56 + Math.random() * 0.22);

      arr[ptr++] = a.x;
      arr[ptr++] = a.y;
      arr[ptr++] = a.z;
      arr[ptr++] = b.x;
      arr[ptr++] = b.y;
      arr[ptr++] = b.z;
    }

    const trimmed = arr.slice(0, ptr);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(trimmed, 3));
    return geometry;
  }, []);

  useFrame(({ clock }) => {
    const time = clock.elapsedTime;
    audioLevelRef.current = THREE.MathUtils.lerp(audioLevelRef.current, audioLevel, 0.14);
    const audioBoost = audioLevelRef.current;
    const speechGate = THREE.MathUtils.smoothstep(audioBoost, 0.05, 0.22);
    const beat = 0.5 + 0.5 * Math.sin(time * 0.72);
    const breath = THREE.MathUtils.smoothstep(beat, 0.2, 1.0) * speechGate;

    if (root.current) {
      root.current.rotation.y = time * 0.022;
      root.current.rotation.x = Math.sin(time * 0.08) * 0.02;
      const s = 1 + breath * 0.05 + audioBoost * 0.045;
      root.current.scale.set(s, s, s);
    }

    if (shellGroup.current) {
      shellGroup.current.rotation.y = -time * 0.03;
      shellGroup.current.rotation.z = Math.sin(time * 0.12) * 0.02;
      const shellScale = 1 + breath * 0.032 + audioBoost * 0.02;
      shellGroup.current.scale.set(shellScale, shellScale, shellScale);
    }

    if (ringGroup.current) {
      ringGroup.current.children.forEach((ring, idx) => {
        const config = ringData[idx];
        ring.rotation.z = time * config.speed + config.phase;
        ring.rotation.y = config.rotY + Math.sin(time * 0.18 + idx) * 0.06;
        ring.rotation.x = config.rotX + Math.sin(time * 0.1 + idx) * 0.02;

        const ringPulse = 1 + breath * (0.04 + (idx % 3) * 0.01) + audioBoost * 0.02;
        ring.scale.set(ringPulse, ringPulse, ringPulse);
      });
    }
  });

  const speechGlow = THREE.MathUtils.smoothstep(audioLevel, 0.05, 0.22);

  const shellOpacity = 0.52 + speechGlow * 0.12 + audioLevel * 0.16;
  const bandOpacity = 0.64 + speechGlow * 0.14 + audioLevel * 0.14;
  const circuitOpacity = 0.2 + speechGlow * 0.08 + audioLevel * 0.12;
  const radialOpacity = 0.12 + speechGlow * 0.1 + audioLevel * 0.16;
  const coreOpacity = 0.8 + speechGlow * 0.14 + audioLevel * 0.12;
  const innerRingOpacity = 0.64 + speechGlow * 0.12 + audioLevel * 0.14;
  const arcAOpacity = 0.48 + speechGlow * 0.1 + audioLevel * 0.16;
  const arcBOpacity = 0.44 + speechGlow * 0.11 + audioLevel * 0.16;
  const microRingOpacity = 0.28 + speechGlow * 0.08 + audioLevel * 0.14;

  return (
    <group ref={root}>
      <group ref={shellGroup}>
        <lineSegments geometry={shellGeometry}>
          <lineBasicMaterial
            color="#ffb548"
            transparent
            opacity={shellOpacity}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </lineSegments>
        <lineSegments geometry={bandGeometry}>
          <lineBasicMaterial
            color="#ffc86e"
            transparent
            opacity={bandOpacity}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </lineSegments>
      </group>

      <lineSegments geometry={circuitGeometry}>
        <lineBasicMaterial
          color="#ffd98b"
          transparent
          opacity={circuitOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>

      <lineSegments geometry={radialGeometry}>
        <lineBasicMaterial
          color="#ffaf3d"
          transparent
          opacity={radialOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>

      <mesh>
        <sphereGeometry args={[0.042, 24, 24]} />
        <meshBasicMaterial
          color="#ffe6b5"
          transparent
          opacity={coreOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[Math.PI * 0.5, 0, 0]}>
        <torusGeometry args={[0.2, 0.005, 8, 120]} />
        <meshBasicMaterial
          color="#ffd78d"
          transparent
          opacity={innerRingOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[0.35, 1.1, 0.25]}>
        <torusGeometry args={[0.3, 0.004, 8, 120, Math.PI * 1.55]} />
        <meshBasicMaterial
          color="#ffad40"
          transparent
          opacity={arcAOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[-0.2, -0.8, 0.6]}>
        <torusGeometry args={[0.26, 0.003, 8, 120, Math.PI * 1.28]} />
        <meshBasicMaterial
          color="#ffd184"
          transparent
          opacity={arcBOpacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      <group ref={ringGroup}>
        {ringData.map((ring, index) => (
          <mesh key={index} rotation={[ring.rotX, ring.rotY, ring.phase]}>
            <torusGeometry args={[ring.radius, ring.thickness, 8, 120, ring.arcLength]} />
            <meshBasicMaterial
              color={index % 2 === 0 ? "#ffd685" : "#ff9f2d"}
              transparent
              opacity={microRingOpacity}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
}