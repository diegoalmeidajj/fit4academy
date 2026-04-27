/**
 * Theme entry point. Combines mode-aware semantic tokens with mode-invariant
 * scales (radius, spacing, typography). Use `useTheme()` everywhere.
 */

import { useColorScheme } from 'react-native';
import { useThemeMode } from '@/store/themeMode';
import { lightTokens, darkTokens, ThemeTokens, Mode } from './tokens';
import { palette } from './palette';

export const radius = {
  xs: 6,
  sm: 10,
  md: 14,
  lg: 20,
  xl: 28,
  xxl: 36,
  pill: 999,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const fontFamily = {
  display: 'SpaceGrotesk_700Bold',
  displayBold: 'SpaceGrotesk_800ExtraBold',
  body: 'DMSans_400Regular',
  bodyMedium: 'DMSans_500Medium',
  bodySemi: 'DMSans_600SemiBold',
  bodyBold: 'DMSans_700Bold',
} as const;

// Type tokens are NOT bound to fontFamily yet (we'd need the @expo-google-fonts
// pkg). Default to system; later we can swap to the Google Fonts when the
// package is installed.
export const type = {
  display: { fontSize: 40, fontWeight: '800' as const, letterSpacing: -1 },
  h1: { fontSize: 28, fontWeight: '700' as const, letterSpacing: -0.5 },
  h2: { fontSize: 22, fontWeight: '700' as const, letterSpacing: -0.4 },
  h3: { fontSize: 18, fontWeight: '700' as const },
  h4: { fontSize: 16, fontWeight: '600' as const },
  body: { fontSize: 15, fontWeight: '400' as const },
  bodyMedium: { fontSize: 15, fontWeight: '500' as const },
  bodyBold: { fontSize: 15, fontWeight: '700' as const },
  small: { fontSize: 13, fontWeight: '400' as const },
  caption: { fontSize: 12, fontWeight: '600' as const, letterSpacing: 0.4 },
  overline: { fontSize: 11, fontWeight: '700' as const, letterSpacing: 0.6 },
} as const;

export type Theme = {
  mode: Mode;
  tokens: ThemeTokens;
  palette: typeof palette;
  radius: typeof radius;
  spacing: typeof spacing;
  type: typeof type;
  fontFamily: typeof fontFamily;
};

export function useTheme(): Theme {
  const setting = useThemeMode(s => s.mode);
  const systemScheme = useColorScheme(); // 'light' | 'dark' | null
  const resolvedMode: Mode =
    setting === 'system'
      ? systemScheme === 'light'
        ? 'light'
        : 'dark'
      : setting;

  const tokens = resolvedMode === 'light' ? lightTokens : darkTokens;
  return { mode: resolvedMode, tokens, palette, radius, spacing, type, fontFamily };
}

// Re-export common items
export { palette } from './palette';
export type { ThemeTokens, Mode } from './tokens';
