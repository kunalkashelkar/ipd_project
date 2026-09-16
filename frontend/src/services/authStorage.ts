// ============================================================
// Auth Storage Abstraction — Phase 1 Isolation Barrier
// ============================================================
// Centralizes all authentication token access into a single module.
// In Phase 2, this can be seamlessly upgraded to httpOnly cookies
// or secure in-memory storage without touching any application components.
// ============================================================

const AUTH_STORAGE_KEY = 'auth-storage';

export interface StoredSession {
  token: string | null;
  refreshToken: string | null;
  user: any | null;
}

export const authStorage = {
  getAccessToken(): string | null {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed?.state?.token || null;
    } catch {
      return null;
    }
  },

  setAccessToken(token: string): void {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : { state: {} };
      if (!parsed.state) parsed.state = {};
      parsed.state.token = token;
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(parsed));
    } catch {
      // Ignore
    }
  },

  getRefreshToken(): string | null {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed?.state?.refreshToken || null;
    } catch {
      return null;
    }
  },

  getUser(): any | null {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed?.state?.user || null;
    } catch {
      return null;
    }
  },

  setUser(user: any): void {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : { state: {} };
      if (!parsed.state) parsed.state = {};
      parsed.state.user = user;
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(parsed));
    } catch {
      // Ignore
    }
  },

  getActiveOrganizationId(): string | null {
    try {
      return localStorage.getItem('active-org-id');
    } catch {
      return null;
    }
  },

  setActiveOrganizationId(orgId: string | null): void {
    try {
      if (orgId) {
        localStorage.setItem('active-org-id', orgId);
      } else {
        localStorage.removeItem('active-org-id');
      }
    } catch {
      // Ignore
    }
  },

  clearSession(): void {
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      localStorage.removeItem('active-org-id');
    } catch {
      // Ignore storage clear errors
    }
  },

  isAuthenticated(): boolean {
    return Boolean(this.getAccessToken());
  },
};
