/**
 * Theme mode preference: 'system' (follow OS), 'light', or 'dark'.
 * Persisted via the same secure storage we use for tokens.
 */
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const KEY = 'f4a.theme_mode';
type ModeSetting = 'system' | 'light' | 'dark';

const isWeb = Platform.OS === 'web';

async function persist(value: ModeSetting) {
  if (isWeb) {
    try { localStorage.setItem(KEY, value); } catch {}
    return;
  }
  await SecureStore.setItemAsync(KEY, value);
}

async function load(): Promise<ModeSetting> {
  try {
    const v = isWeb
      ? (typeof localStorage !== 'undefined' ? localStorage.getItem(KEY) : null)
      : await SecureStore.getItemAsync(KEY);
    if (v === 'system' || v === 'light' || v === 'dark') return v;
  } catch {}
  return 'system';
}

type State = {
  mode: ModeSetting;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setMode: (m: ModeSetting) => Promise<void>;
};

export const useThemeMode = create<State>((set) => ({
  mode: 'dark',
  hydrated: false,
  async hydrate() {
    const m = await load();
    set({ mode: m, hydrated: true });
  },
  async setMode(m) {
    set({ mode: m });
    await persist(m);
  },
}));
