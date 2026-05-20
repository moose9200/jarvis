import { Canvas } from "@react-three/fiber";
import { Galaxy, Nebulae } from "./Galaxy";

/**
 * Full-viewport ambient background. A slow-rotating spiral galaxy with
 * three soft nebula blobs behind it. Tuned to be subtle — fades to dark
 * at the edges so the foreground HUD panels stay readable.
 */
export function HUDScene() {
  return (
    <Canvas
      camera={{ position: [0, 1.2, 8.5], fov: 55 }}
      className="absolute inset-0"
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      dpr={[1, 1.8]}
    >
      {/* Faint ambient + a single key light for any non-additive meshes */}
      <ambientLight intensity={0.15} />
      <pointLight position={[0, 4, 6]} color="#9fb8ff" intensity={0.6} />

      <Nebulae />
      <Galaxy />
    </Canvas>
  );
}
