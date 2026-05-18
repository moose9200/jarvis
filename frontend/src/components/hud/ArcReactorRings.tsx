import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { useJarvisStore } from "../../store/jarvisStore";

export function ArcReactorRings() {
  const g1 = useRef<THREE.Group>(null);
  const g2 = useRef<THREE.Group>(null);
  const g3 = useRef<THREE.Group>(null);
  const wake = useJarvisStore((s) => s.wakeState);

  useFrame((_, dt) => {
    const speed =
      wake === "listening" ? 1.8 : wake === "processing" ? 3.2 : wake === "responding" ? 1.4 : 0.4;
    if (g1.current) g1.current.rotation.z += dt * speed;
    if (g2.current) g2.current.rotation.z -= dt * speed * 0.7;
    if (g3.current) g3.current.rotation.z += dt * speed * 0.5;
  });

  const color =
    wake === "idle" ? "#0066ff" : wake === "processing" ? "#00ffff" : "#00d4ff";

  return (
    <>
      <group ref={g1}>
        <mesh>
          <torusGeometry args={[1.6, 0.02, 16, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.85} />
        </mesh>
      </group>
      <group ref={g2}>
        <mesh>
          <torusGeometry args={[2.0, 0.015, 16, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.6} />
        </mesh>
      </group>
      <group ref={g3}>
        <mesh>
          <torusGeometry args={[2.4, 0.01, 16, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.35} />
        </mesh>
      </group>
    </>
  );
}
