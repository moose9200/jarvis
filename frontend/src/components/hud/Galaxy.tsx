/**
 * Floating 3D galaxy background.
 *
 * Generates a logarithmic-spiral point cloud (~12k stars across 3 arms),
 * tinted by radial distance so the core glows warm-white and the outer arms
 * fade to jcyan. Slowly rotates around its own axis, drifts gently in 3D,
 * and parallax-tilts toward the cursor so the scene feels alive without
 * dominating the foreground.
 *
 * Performance: one BufferGeometry + PointsMaterial. No per-frame allocations.
 * Sized at ~12k points — runs at 60fps on integrated GPUs.
 */
import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const STAR_COUNT = 12_000;
const ARMS = 3;
const RADIUS = 6.0;          // outer extent of galaxy
const SPIN = 1.2;             // how tightly arms wrap
const ARM_NOISE = 0.55;       // outward scatter (perpendicular to arm)
const VERTICAL_NOISE = 0.35;  // disk thickness — keep small for a flat galaxy

// Color stops sampled radially: core (warm) → mid (white) → edge (jcyan).
const CORE_COLOR = new THREE.Color("#ffd9a8");
const MID_COLOR  = new THREE.Color("#ffffff");
const EDGE_COLOR = new THREE.Color("#00d4ff");

export function Galaxy() {
  const ref = useRef<THREE.Points>(null);
  const { mouse } = useThree();

  // Build geometry + per-vertex colors once. useMemo so HMR doesn't realloc.
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(STAR_COUNT * 3);
    const colors = new Float32Array(STAR_COUNT * 3);
    const tmp = new THREE.Color();

    for (let i = 0; i < STAR_COUNT; i++) {
      // Radial distance — bias toward center with Math.pow(r, 1.7) so the
      // core is denser than the rim (looks more like a real galaxy).
      const t = Math.random();
      const r = Math.pow(t, 1.7) * RADIUS;

      // Which arm + base angle
      const armIndex = i % ARMS;
      const armAngle = (armIndex / ARMS) * Math.PI * 2;
      const spin = r * SPIN;

      // Scatter perpendicular to the arm to soften the spiral edges
      const scatter = (Math.random() - 0.5) * ARM_NOISE * (1 + r * 0.2);
      const angle = armAngle + spin + scatter;

      const x = Math.cos(angle) * r;
      const z = Math.sin(angle) * r;
      // Disk gets thicker near the core (bulge), thin at edges
      const y = (Math.random() - 0.5) * VERTICAL_NOISE * Math.exp(-r * 0.3);

      positions[i * 3 + 0] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      // Color by radial distance
      const tn = r / RADIUS;
      if (tn < 0.35) {
        tmp.copy(CORE_COLOR).lerp(MID_COLOR, tn / 0.35);
      } else {
        tmp.copy(MID_COLOR).lerp(EDGE_COLOR, (tn - 0.35) / 0.65);
      }
      // Random brightness wobble so stars don't look uniform
      const brightness = 0.55 + Math.random() * 0.45;
      colors[i * 3 + 0] = tmp.r * brightness;
      colors[i * 3 + 1] = tmp.g * brightness;
      colors[i * 3 + 2] = tmp.b * brightness;
    }

    return { positions, colors };
  }, []);

  // Tilt the galaxy slightly so we see it from above-front instead of edge-on.
  useEffect(() => {
    if (ref.current) {
      ref.current.rotation.x = -0.5;
      ref.current.rotation.z = 0.15;
    }
  }, []);

  // Slow self-rotation + cursor parallax + vertical drift
  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;

    // Spin the galaxy around its disk axis
    ref.current.rotation.y = t * 0.04;

    // Drift Y position gently
    ref.current.position.y = Math.sin(t * 0.15) * 0.15;

    // Parallax tilt toward cursor (tiny — we don't want it to chase the mouse)
    const targetTiltX = -0.5 + mouse.y * 0.08;
    const targetTiltZ = 0.15 + mouse.x * 0.08;
    ref.current.rotation.x += (targetTiltX - ref.current.rotation.x) * 0.04;
    ref.current.rotation.z += (targetTiltZ - ref.current.rotation.z) * 0.04;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color"    args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.035}
        sizeAttenuation
        vertexColors
        transparent
        opacity={0.95}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}


/**
 * Soft glow "nebula" blobs that float behind the galaxy. Three large
 * transparent spheres with emissive material — they read as colored fog
 * smears through the star field thanks to additive blending.
 */
export function Nebulae() {
  const refs = useRef<(THREE.Mesh | null)[]>([null, null, null]);

  const blobs = useMemo(
    () => [
      { pos: [-3.5, 0.8, -2.5] as [number, number, number], color: "#5a2dff", scale: 2.8 },
      { pos: [ 4.0, -0.5, -3.0] as [number, number, number], color: "#00d4ff", scale: 2.2 },
      { pos: [ 0.5, 1.5, -4.0] as [number, number, number], color: "#ff3d8c", scale: 1.8 },
    ],
    [],
  );

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    refs.current.forEach((m, i) => {
      if (!m) return;
      // Each blob drifts on its own slow sine — independent phases.
      const phase = i * 1.7;
      m.position.x = blobs[i].pos[0] + Math.sin(t * 0.1 + phase) * 0.4;
      m.position.y = blobs[i].pos[1] + Math.cos(t * 0.12 + phase) * 0.3;
    });
  });

  return (
    <>
      {blobs.map((b, i) => (
        <mesh
          key={i}
          ref={(el) => (refs.current[i] = el)}
          position={b.pos}
          scale={b.scale}
        >
          <sphereGeometry args={[1, 24, 24]} />
          <meshBasicMaterial
            color={b.color}
            transparent
            opacity={0.06}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </>
  );
}
