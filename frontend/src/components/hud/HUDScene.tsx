import { Canvas } from "@react-three/fiber";
import { ArcReactorRings } from "./ArcReactorRings";
import { CentralOrb } from "./CentralOrb";
import { ParticleField } from "./ParticleField";

export function HUDScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 6], fov: 50 }}
      className="absolute inset-0"
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[0, 0, 5]} color="#00d4ff" intensity={2} />
      <ParticleField />
      <ArcReactorRings />
      <CentralOrb />
    </Canvas>
  );
}
