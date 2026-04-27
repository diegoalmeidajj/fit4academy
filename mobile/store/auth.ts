/**
 * Auth store. Holds the bootstrapped subject (member or staff or none).
 * Persistence of tokens lives in lib/storage.ts; this store reflects the
 * in-memory, currently-logged-in user.
 */
import { create } from 'zustand';
import { apiGet, apiPost, LoginResponse, Me } from '@/lib/api';
import { tokenStorage } from '@/lib/storage';

type Status = 'booting' | 'anonymous' | 'authenticated';

type AuthState = {
  status: Status;
  me: Me | null;
  bootstrap: () => Promise<void>;
  loginMember: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  loginStaff: (username: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  signupMemberWithPin: (pin: string, email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  refreshMe: () => Promise<void>;
  logout: () => Promise<void>;
};

async function _persistTokens(resp: LoginResponse, subjectType: 'member' | 'staff') {
  await tokenStorage.save(resp.access_token, resp.refresh_token, subjectType);
}

export const useAuth = create<AuthState>((set, get) => ({
  status: 'booting',
  me: null,

  async bootstrap() {
    const access = await tokenStorage.getAccess();
    if (!access) {
      set({ status: 'anonymous', me: null });
      return;
    }
    const r = await apiGet<Me>('/api/v1/me');
    if (r.ok) {
      set({ status: 'authenticated', me: r.data });
    } else {
      await tokenStorage.clear();
      set({ status: 'anonymous', me: null });
    }
  },

  async loginMember(email, password) {
    const r = await apiPost<LoginResponse>(
      '/api/v1/auth/member/login',
      { email, password },
      { auth: false }
    );
    if (!r.ok) return { ok: false, error: r.error };
    await _persistTokens(r.data, 'member');
    await get().refreshMe();
    return { ok: true };
  },

  async loginStaff(username, password) {
    const r = await apiPost<LoginResponse>(
      '/api/v1/auth/staff/login',
      { username, password },
      { auth: false }
    );
    if (!r.ok) return { ok: false, error: r.error };
    await _persistTokens(r.data, 'staff');
    await get().refreshMe();
    return { ok: true };
  },

  async signupMemberWithPin(pin, email, password) {
    const r = await apiPost<LoginResponse>(
      '/api/v1/auth/member/signup-with-pin',
      { pin, email, password },
      { auth: false }
    );
    if (!r.ok) return { ok: false, error: r.error };
    await _persistTokens(r.data, 'member');
    await get().refreshMe();
    return { ok: true };
  },

  async refreshMe() {
    const r = await apiGet<Me>('/api/v1/me');
    if (r.ok) {
      set({ status: 'authenticated', me: r.data });
    } else {
      await tokenStorage.clear();
      set({ status: 'anonymous', me: null });
    }
  },

  async logout() {
    try {
      await apiPost('/api/v1/auth/logout', {});
    } catch {}
    await tokenStorage.clear();
    set({ status: 'anonymous', me: null });
  },
}));
