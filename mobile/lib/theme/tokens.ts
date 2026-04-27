/**
 * Semantic theme tokens — refined for minimalist Apple-style aesthetic.
 * Pure neutrals, accent used sparingly, hairline dividers, near-imperceptible shadows.
 */

import { palette } from './palette';

export type Mode = 'light' | 'dark';

type Tokens = {
  mode: Mode;

  bg: {
    canvas: string;        // base background (whole screen)
    canvasAlt: string;     // grouped tableview background
    surface: string;       // card/row surface
    surfaceAlt: string;    // pressed/hover state
    surfaceMuted: string;  // sub-surface (input bg)
    elevated: string;      // floating sheet/modal
    overlay: string;
    inverse: string;
    accentSoft: string;    // tinted brand background
    accentTint: string;
    warningSoft: string;
    dangerSoft: string;
    infoSoft: string;
  };
  text: {
    primary: string;
    secondary: string;
    muted: string;
    disabled: string;
    inverse: string;
    onAccent: string;
    accent: string;
    danger: string;
    warning: string;
    success: string;
  };
  border: {
    default: string;       // hairline
    subtle: string;        // even thinner
    strong: string;        // input borders
    focus: string;
    accent: string;
  };
  brand: {
    accent: string;
    accentHover: string;
    accentDeep: string;
    accentLight: string;
    accentCyan: string;
    gradientStart: string;
    gradientEnd: string;
  };
  shadow: {
    cardOpacity: number;
    cardColor: string;
    elevatedOpacity: number;
    elevatedColor: string;
  };
};

const common = {
  brand: {
    accent: palette.green,
    accentHover: palette.greenDark,
    accentDeep: palette.greenDeep,
    accentLight: palette.greenLight,
    accentCyan: palette.cyan,
    gradientStart: palette.green,
    gradientEnd: palette.greenDark,
  },
};

export const lightTokens: Tokens = {
  mode: 'light',
  ...common,
  bg: {
    canvas: '#ffffff',
    canvasAlt: '#f5f5f7',
    surface: '#ffffff',
    surfaceAlt: '#f5f5f7',
    surfaceMuted: '#fafafa',
    elevated: '#ffffff',
    overlay: 'rgba(0,0,0,0.4)',
    inverse: '#000000',
    accentSoft: 'rgba(0,220,130,0.08)',
    accentTint: 'rgba(0,220,130,0.04)',
    warningSoft: 'rgba(245,158,11,0.08)',
    dangerSoft: 'rgba(239,68,68,0.08)',
    infoSoft: 'rgba(34,211,238,0.08)',
  },
  text: {
    primary: '#000000',
    secondary: '#3c3c43',
    muted: '#8e8e93',
    disabled: '#c7c7cc',
    inverse: '#ffffff',
    onAccent: '#ffffff',
    accent: palette.greenDeep,
    danger: '#ef4444',
    warning: '#f59e0b',
    success: palette.greenDeep,
  },
  border: {
    default: 'rgba(0,0,0,0.08)',
    subtle: 'rgba(0,0,0,0.04)',
    strong: 'rgba(0,0,0,0.15)',
    focus: palette.green,
    accent: palette.green,
  },
  shadow: {
    cardOpacity: 0.04,
    cardColor: '#000000',
    elevatedOpacity: 0.10,
    elevatedColor: '#000000',
  },
};

export const darkTokens: Tokens = {
  mode: 'dark',
  ...common,
  bg: {
    canvas: '#000000',
    canvasAlt: '#0a0a0a',
    surface: '#111113',
    surfaceAlt: '#1c1c1e',
    surfaceMuted: '#0a0a0a',
    elevated: '#1c1c1e',
    overlay: 'rgba(0,0,0,0.7)',
    inverse: '#ffffff',
    accentSoft: 'rgba(0,220,130,0.10)',
    accentTint: 'rgba(0,220,130,0.05)',
    warningSoft: 'rgba(245,158,11,0.12)',
    dangerSoft: 'rgba(239,68,68,0.12)',
    infoSoft: 'rgba(34,211,238,0.10)',
  },
  text: {
    primary: '#ffffff',
    secondary: 'rgba(235,235,245,0.78)',
    muted: 'rgba(235,235,245,0.55)',
    disabled: 'rgba(235,235,245,0.30)',
    inverse: '#000000',
    onAccent: '#ffffff',
    accent: palette.greenLight,
    danger: '#ff453a',
    warning: '#ff9f0a',
    success: palette.green,
  },
  border: {
    default: 'rgba(255,255,255,0.08)',
    subtle: 'rgba(255,255,255,0.04)',
    strong: 'rgba(255,255,255,0.18)',
    focus: palette.green,
    accent: palette.green,
  },
  shadow: {
    cardOpacity: 0.30,
    cardColor: '#000000',
    elevatedOpacity: 0.50,
    elevatedColor: '#000000',
  },
};

export type ThemeTokens = Tokens;
