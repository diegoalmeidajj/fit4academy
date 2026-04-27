/**
 * Backwards-compat shim. Existing screens import { colors, radius, spacing, type, shadow }
 * from '@/lib/theme' — these used to be dark-mode hardcoded values. We now have
 * a proper light/dark system in '@/lib/theme/index.ts' with semantic tokens.
 *
 * This shim continues to expose the old shape (mapped to dark tokens) so untouched
 * screens keep working. New code should `import { useTheme } from '@/lib/theme'`
 * and access `theme.tokens.bg.canvas`, etc.
 */

// Re-export the new theme system (so `useTheme` works from this module too)
export {
  useTheme,
  radius,
  spacing,
  type,
  fontFamily,
  palette,
} from './theme/index';
export type { Theme, ThemeTokens, Mode } from './theme/index';

import { darkTokens } from './theme/tokens';
import { palette as P } from './theme/palette';

// Legacy `colors` object — points to dark-mode values for screens that haven't migrated.
export const colors = {
  green: P.green,
  greenDark: P.greenDark,
  greenDeep: P.greenDeep,
  greenLight: P.greenLight,
  cyan: P.cyan,

  bgDeep: P.slate950,
  bgDark: P.slate900,
  bgCardDark: P.slate800,
  bgCardLight: P.white,
  bgInput: P.slate50,

  textStrong: P.slate900,
  textDefault: P.slate600,
  textMuted: P.slate400,
  textDisabled: P.slate300,
  textOnDark: P.slate200,

  border: P.slate200,
  borderDark: 'rgba(255,255,255,0.10)',

  success: P.green,
  warning: '#f59e0b',
  danger: '#ef4444',
  info: P.cyan,

  white: P.white,
  black: P.black,
  transparent: 'transparent',
} as const;

export const shadow = {
  cta: {
    shadowColor: P.green,
    shadowOpacity: 0.25,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  card: {
    shadowColor: '#000',
    shadowOpacity: darkTokens.shadow.cardOpacity,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
} as const;

// Legacy fonts alias (for screens importing fonts/type from old shape)
export { fontFamily as fonts } from './theme/index';
