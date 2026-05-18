import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { useJarvisStore } from "../../store/jarvisStore";

export function CentralOrb() {
  const ref = useRef<THREE.Mesh>(null);
  const wake = useJarvisStore((s) => s.wakeState);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    const base = wake === "idle" ? 1 : wake === "listening" ? 1.15 : wake === "processing" ? 1.25 : 1.1;
    const s = base + Math.sin(t * 3) * 0.05;
    ref.current.scale.set(s, s, s);
  });

  const intensity = wake === "idle" ? 0.6 : 1.4;

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.55, 64, 64]} />
      <meshStandardMaterial
        color="#00d4ff"
        emissive="#00d4ff"
        emissiveIntensity={intensity}
        roughness={0.2}
        metalness={0.4}
      />
    </mesh>
  );
}
