/**
 * Brand palette — sourced from BRAND_PLAYBOOK.md §8. Single source of truth.
 * These are *raw* color values. Use semantic tokens via useTheme() in UI code.
 */

export const palette = {
  // Brand
  green: '#00DC82',
  greenDark: '#00B368',
  greenDeep: '#059669',
  greenLight: '#6ee7b7',
  greenSoft: '#dcfce7',
  greenTint: '#ecfdf5',
  cyan: '#22d3ee',

  // Neutrals (slate scale)
  slate50: '#f8fafc',
  slate100: '#f1f5f9',
  slate200: '#e2e8f0',
  slate300: '#cbd5e1',
  slate400: '#94a3b8',
  slate500: '#64748b',
  slate600: '#475569',
  slate700: '#334155',
  slate800: '#1e293b',
  slate900: '#0f172a',
  slate950: '#0a0f1a',

  // Semantic
  amber500: '#f59e0b',
  amber400: '#fbbf24',
  red500: '#ef4444',
  red400: '#f87171',

  // Common
  white: '#ffffff',
  black: '#000000',
  transparent: 'transparent',
} as const;

export type Palette = typeof palette;
