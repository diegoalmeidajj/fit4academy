/**
 * Token storage. Uses expo-secure-store on native (Keychain / Keystore),
 * falls back to in-memory on web.
 */
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const KEY_ACCESS = 'f4a.access_token';
const KEY_REFRESH = 'f4a.refresh_token';
const KEY_SUB_TYPE = 'f4a.subject_type';

const memory: Record<string, string | null> = {};

const isWeb = Platform.OS === 'web';

async function set(key: string, value: string | null) {
  if (isWeb) {
    memory[key] = value;
    if (value === null) {
      try { localStorage.removeItem(key); } catch {}
    } else {
      try { localStorage.setItem(key, value); } catch {}
    }
    return;
  }
  if (value === null) {
    await SecureStore.deleteItemAsync(key);
  } else {
    await SecureStore.setItemAsync(key, value);
  }
}

async function get(key: string): Promise<string | null> {
  if (isWeb) {
    if (memory[key] !== undefined) return memory[key];
    try { return localStorage.getItem(key); } catch { return null; }
  }
  return await SecureStore.getItemAsync(key);
}

export const tokenStorage = {
  async save(access: string, refresh: string, subjectType: 'member' | 'staff') {
    await set(KEY_ACCESS, access);
    await set(KEY_REFRESH, refresh);
    await set(KEY_SUB_TYPE, subjectType);
  },
  async getAccess() { return get(KEY_ACCESS); },
  async getRefresh() { return get(KEY_REFRESH); },
  async getSubjectType(): Promise<'member' | 'staff' | null> {
    const v = await get(KEY_SUB_TYPE);
    return (v === 'member' || v === 'staff') ? v : null;
  },
  async setAccess(access: string) { await set(KEY_ACCESS, access); },
  async clear() {
    await set(KEY_ACCESS, null);
    await set(KEY_REFRESH, null);
    await set(KEY_SUB_TYPE, null);
  },
};
