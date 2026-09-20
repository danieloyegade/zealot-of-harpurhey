import {
  DoubleSide,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  type Group,
} from 'three';
import { VISUAL_STYLE } from '../rendering/visualStyle';
import { loadSurfaceTexture } from './surfaceDecals';
import type { SpecterGraffitiMarker, SpecterVariant } from './worldLayout';

/*
 * Spray-painted specter decals: flat alpha-textured quads laid a few
 * millimetres proud of a wall. Paint has no thickness and no collision.
 */

/** Distance off the wall, enough to clear shadow-map acne without reading as a sticker. */
const WALL_OFFSET = 0.012;

const materialCache = new Map<SpecterVariant, MeshStandardMaterial>();

function specterMaterial(variant: SpecterVariant): MeshStandardMaterial {
  const cached = materialCache.get(variant);
  if (cached) {
    return cached;
  }
  const material = new MeshStandardMaterial({
    name: `mat-graffiti-${variant}`,
    map: loadSurfaceTexture(`graffiti/${variant}`, { color: true }),
    // Aerosol paint is matte and sits in the wall's own lighting.
    roughness: 0.88,
    metalness: 0,
    transparent: true,
    alphaTest: 0.02,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
    side: DoubleSide,
    flatShading: VISUAL_STYLE.geometry.facetedLighting,
  });
  materialCache.set(variant, material);
  return material;
}

export function addSpecterGraffiti(root: Group, marker: SpecterGraffitiMarker): void {
  const mesh = new Mesh(
    new PlaneGeometry(marker.width, marker.height),
    specterMaterial(marker.variant),
  );
  mesh.name = marker.name;
  mesh.rotation.y = marker.rotationY;
  mesh.position.set(
    marker.x + Math.sin(marker.rotationY) * WALL_OFFSET,
    marker.y + marker.height / 2,
    marker.z + Math.cos(marker.rotationY) * WALL_OFFSET,
  );
  mesh.receiveShadow = true;
  mesh.renderOrder = 1;
  root.add(mesh);
}
