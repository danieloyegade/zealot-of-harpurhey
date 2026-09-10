import {
  CanvasTexture,
  MeshBasicMaterial,
  MeshStandardMaterial,
  SRGBColorSpace,
} from 'three';
import { applyTextureProfile, VISUAL_STYLE } from './visualStyle';

function seededNoise(seed: number): () => number {
  let value = seed || 1;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function textSeed(text: string): number {
  return [...text].reduce((value, character) => value + character.charCodeAt(0), 73);
}

export function createWeatheredSignMaterial(
  text: string,
  background: string,
  foreground: string,
  glow = 0.12,
): MeshStandardMaterial {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error(`Could not draw the ${text} sign.`);
  }

  const random = seededNoise(textSeed(text));
  context.fillStyle = background;
  context.fillRect(0, 0, canvas.width, canvas.height);
  const gradient = context.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, 'rgba(255, 210, 130, 0.09)');
  gradient.addColorStop(0.7, 'rgba(0, 0, 0, 0)');
  gradient.addColorStop(1, 'rgba(0, 0, 0, 0.32)');
  context.fillStyle = gradient;
  context.fillRect(0, 0, canvas.width, canvas.height);

  context.fillStyle = foreground;
  context.font = text.length > 14
    ? '900 58px Impact, Arial Narrow, sans-serif'
    : '900 72px Impact, Arial Narrow, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text.toUpperCase(), canvas.width / 2, canvas.height / 2 - 1);

  for (let index = 0; index < 260; index += 1) {
    const x = random() * canvas.width;
    const y = random() * canvas.height;
    const radius = 0.5 + random() * 5;
    context.fillStyle = random() > 0.42
      ? `rgba(15, 12, 10, ${0.08 + random() * 0.28})`
      : `rgba(226, 216, 181, ${0.04 + random() * 0.15})`;
    context.fillRect(x, y, radius * (1 + random() * 2.4), radius);
  }
  context.strokeStyle = 'rgba(15, 12, 10, 0.65)';
  context.lineWidth = 7;
  context.strokeRect(3.5, 3.5, canvas.width - 7, canvas.height - 7);

  const texture = applyTextureProfile(new CanvasTexture(canvas), 'RETRO_GRAPHIC');
  texture.colorSpace = SRGBColorSpace;
  return new MeshStandardMaterial({
    map: texture,
    emissiveMap: texture,
    emissive: 0xffffff,
    emissiveIntensity: glow * VISUAL_STYLE.lighting.emissiveMultiplier,
    roughness: 0.78,
    metalness: 0.05,
  });
}

export function createGraffitiMaterial(
  text: string,
  foreground = '#c54178',
): MeshBasicMaterial {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error(`Could not draw the ${text} graffiti.`);
  }
  const random = seededNoise(textSeed(text) * 7);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.save();
  context.translate(256, 128);
  context.rotate((random() - 0.5) * 0.12);
  context.fillStyle = foreground;
  context.globalAlpha = 0.62;
  context.font = '900 108px Impact, Arial Black, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text.toUpperCase(), 0, 0);
  context.lineWidth = 8;
  context.strokeStyle = 'rgba(15, 10, 19, 0.74)';
  context.strokeText(text.toUpperCase(), 0, 0);
  context.restore();

  for (let index = 0; index < 18; index += 1) {
    context.strokeStyle = `${foreground}${Math.floor(50 + random() * 80)
      .toString(16)
      .padStart(2, '0')}`;
    context.lineWidth = 2 + random() * 6;
    context.beginPath();
    context.moveTo(random() * 512, 170 + random() * 45);
    context.lineTo(random() * 512, 175 + random() * 55);
    context.stroke();
  }

  const texture = applyTextureProfile(new CanvasTexture(canvas), 'RETRO_GRAPHIC');
  texture.colorSpace = SRGBColorSpace;
  return new MeshBasicMaterial({
    map: texture,
    transparent: true,
    opacity: 0.78,
    depthWrite: false,
  });
}

export function createDreamsSignMaterial(): MeshStandardMaterial {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 160;
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not draw the Dreams fascia.');
  }

  const random = seededNoise(1998);
  context.fillStyle = '#b9b8ad';
  context.fillRect(0, 0, canvas.width, canvas.height);

  const lightFalloff = context.createRadialGradient(256, 66, 20, 256, 70, 300);
  lightFalloff.addColorStop(0, 'rgba(255, 255, 238, 0.38)');
  lightFalloff.addColorStop(0.72, 'rgba(208, 222, 216, 0.08)');
  lightFalloff.addColorStop(1, 'rgba(74, 70, 59, 0.2)');
  context.fillStyle = lightFalloff;
  context.fillRect(0, 0, canvas.width, canvas.height);

  for (let index = 0; index < 320; index += 1) {
    const x = random() * canvas.width;
    const y = random() * canvas.height;
    const width = 1 + random() * 13;
    const height = 0.5 + random() * 3.5;
    context.fillStyle = random() > 0.18
      ? `rgba(68, 62, 48, ${0.018 + random() * 0.08})`
      : `rgba(233, 238, 220, ${0.04 + random() * 0.12})`;
    context.fillRect(x, y, width, height);
  }

  context.fillStyle = '#4b83a8';
  context.font = '500 102px Georgia, Times New Roman, serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText('Dreams', 256, 76);

  context.beginPath();
  context.moveTo(132, 132);
  context.bezierCurveTo(210, 112, 300, 151, 390, 124);
  context.bezierCurveTo(312, 160, 218, 126, 132, 138);
  context.closePath();
  context.fillStyle = 'rgba(150, 99, 103, 0.62)';
  context.fill();

  const texture = applyTextureProfile(new CanvasTexture(canvas), 'PHOTO_ENVIRONMENT');
  texture.colorSpace = SRGBColorSpace;
  return new MeshStandardMaterial({
    map: texture,
    emissiveMap: texture,
    emissive: 0xbcd6e1,
    emissiveIntensity: 0.08 * VISUAL_STYLE.lighting.emissiveMultiplier,
    roughness: 0.88,
    metalness: 0,
  });
}
