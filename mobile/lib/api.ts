/**
 * HTTP client with automatic JWT handling.
 *
 * - Reads access token from secure storage
 * - On 401, tries refresh once and retries
 * - Surfaces a typed { ok, data, error } result so callers don't have to try/catch
 */
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { tokenStorage } from './storage';

/** API base URL.
 *
 * On web, the PWA is served by the same Flask process that hosts the API
 * (see app.py /app/* + /api/v1/*). Using a relative URL means we hit the
 * same origin → no CORS, works in production behind any domain.
 *
 * On native iOS/Android, Expo dev defaults to localhost which won't work
 * from a phone — so we read from app.json `extra.apiBaseUrl` and fall back
 * to a local network IP. In production native builds this should be set
 * via EAS environment variables.
 */
const fromConfig = (Constants.expoConfig?.extra as any)?.apiBaseUrl as string | undefined;

const API_BASE: string = (() => {
  if (Platform.OS === 'web') {
    // Same origin — works on Railway, localhost, or any deploy.
    return '';
  }
  return fromConfig || 'http://localhost:8080';
})();

type Result<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status: number };

async function rawFetch<T>(path: string, init: RequestInit, withAuth: boolean): Promise<Result<T>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  };
  if (withAuth) {
    const access = await tokenStorage.getAccess();
    if (access) headers['Authorization'] = `Bearer ${access}`;
  }
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch (e: any) {
    return { ok: false, error: e?.message || 'network_error', status: 0 };
  }
  let body: any = null;
  try {
    body = await resp.json();
  } catch {
    body = null;
  }
  if (!resp.ok) {
    return { ok: false, error: body?.error || `http_${resp.status}`, status: resp.status };
  }
  return { ok: true, data: body as T };
}

async function refreshAccess(): Promise<boolean> {
  const refresh = await tokenStorage.getRefresh();
  if (!refresh) return false;
  const r = await rawFetch<{ access_token: string }>(
    '/api/v1/auth/refresh',
    { method: 'POST', body: JSON.stringify({ refresh_token: refresh }) },
    /* withAuth */ false
  );
  if (!r.ok) return false;
  await tokenStorage.setAccess(r.data.access_token);
  return true;
}

export async function apiGet<T = any>(path: string): Promise<Result<T>> {
  let r = await rawFetch<T>(path, { method: 'GET' }, true);
  if (!r.ok && r.status === 401) {
    if (await refreshAccess()) {
      r = await rawFetch<T>(path, { method: 'GET' }, true);
    }
  }
  return r;
}

export async function apiPost<T = any>(path: string, body?: any, opts?: { auth?: boolean }): Promise<Result<T>> {
  const auth = opts?.auth !== false;
  const init: RequestInit = { method: 'POST', body: body ? JSON.stringify(body) : undefined };
  let r = await rawFetch<T>(path, init, auth);
  if (auth && !r.ok && r.status === 401) {
    if (await refreshAccess()) {
      r = await rawFetch<T>(path, init, true);
    }
  }
  return r;
}

export async function apiPatch<T = any>(path: string, body?: any): Promise<Result<T>> {
  const init: RequestInit = { method: 'PATCH', body: body ? JSON.stringify(body) : undefined };
  let r = await rawFetch<T>(path, init, true);
  if (!r.ok && r.status === 401) {
    if (await refreshAccess()) {
      r = await rawFetch<T>(path, init, true);
    }
  }
  return r;
}

// ─────────────── domain types ───────────────

export type LoginResponse = {
  success: boolean;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  member_id?: number;
  user_id?: number;
  role?: string;
};

export type Me =
  | {
      type: 'member';
      id: number;
      first_name: string;
      last_name: string;
      email: string;
      phone: string;
      photo_url: string;
      belt: string;
      stripes: number;
      membership_status: string;
      academy: { id: number; name: string; logo_url: string; primary_color: string; language: string } | null;
    }
  | {
      type: 'staff';
      id: number;
      username: string;
      name: string;
      email: string;
      role: string;
      photo_url: string;
      academy: { id: number; name: string; logo_url: string; language: string; currency: string } | null;
    };
