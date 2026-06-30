import { getContrastColor } from '../components/IconaPunteggio';

function parseHex(hex) {
  const h = String(hex || '#888888').replace('#', '').trim();
  if (h.length === 3) {
    return {
      r: parseInt(h[0] + h[0], 16),
      g: parseInt(h[1] + h[1], 16),
      b: parseInt(h[2] + h[2], 16),
    };
  }
  if (h.length >= 6) {
    return {
      r: parseInt(h.slice(0, 2), 16),
      g: parseInt(h.slice(2, 4), 16),
      b: parseInt(h.slice(4, 6), 16),
    };
  }
  return { r: 136, g: 136, b: 136 };
}

function toHex({ r, g, b }) {
  const clamp = (n) => Math.max(0, Math.min(255, Math.round(n)));
  return `#${[clamp(r), clamp(g), clamp(b)].map((x) => x.toString(16).padStart(2, '0')).join('')}`;
}

export function shadeHex(hex, amount) {
  const { r, g, b } = parseHex(hex);
  const f = amount >= 0 ? 255 : 0;
  const p = Math.abs(amount);
  return toHex({
    r: r + (f - r) * p,
    g: g + (f - g) * p,
    b: b + (f - b) * p,
  });
}

export function rgbaHex(hex, alpha = 1) {
  const { r, g, b } = parseHex(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function buildCardFrameStyles(energyTheme) {
  const colore = energyTheme?.colore || '#6b7280';
  const headerText = getContrastColor(colore);
  const isLightAura = headerText === 'black';
  const bodyBg = isLightAura ? '#111827' : shadeHex(colore, -0.82);
  const panelBg = isLightAura ? '#1f2937' : shadeHex(colore, -0.7);

  return {
    wrapper: {
      borderColor: colore,
      boxShadow: `0 0 0 1px ${rgbaHex(colore, 0.35)}, 0 8px 24px ${rgbaHex(colore, 0.22)}`,
      background: `linear-gradient(165deg, ${shadeHex(colore, -0.55)} 0%, ${bodyBg} 45%, #0b0f17 100%)`,
    },
    header: {
      background: `linear-gradient(90deg, ${shadeHex(colore, -0.15)} 0%, ${colore} 100%)`,
      color: headerText === 'white' ? '#ffffff' : '#111827',
      borderBottom: `1px solid ${rgbaHex(colore, 0.5)}`,
    },
    typeLine: {
      color: colore,
      borderColor: rgbaHex(colore, 0.35),
      backgroundColor: rgbaHex(colore, 0.08),
    },
    rulesBox: {
      backgroundColor: panelBg,
      borderColor: rgbaHex(colore, 0.25),
    },
    stats: {
      color: colore,
    },
    rarityGem: (raritaClass) => raritaClass,
  };
}
