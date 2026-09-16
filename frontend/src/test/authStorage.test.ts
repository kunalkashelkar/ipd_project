import { describe, it, expect, beforeEach } from 'vitest';
import { authStorage } from '../services/authStorage';

describe('AuthStorage Service', () => {
  beforeEach(() => {
    authStorage.clearSession();
  });

  it('stores and retrieves access tokens cleanly', () => {
    expect(authStorage.getAccessToken()).toBeNull();
    authStorage.setAccessToken('test-jwt-token-xyz');
    expect(authStorage.getAccessToken()).toBe('test-jwt-token-xyz');
    expect(authStorage.isAuthenticated()).toBe(true);
  });

  it('stores and clears user data', () => {
    const user = {
      id: 'usr_1',
      email: 'analyst@example.com',
      full_name: 'Security Analyst',
      role: 'security_analyst',
      is_active: true,
      created_at: new Date().toISOString(),
    };
    authStorage.setUser(user);
    expect(authStorage.getUser()).toEqual(user);

    authStorage.clearSession();
    expect(authStorage.getAccessToken()).toBeNull();
    expect(authStorage.getUser()).toBeNull();
    expect(authStorage.isAuthenticated()).toBe(false);
  });
});
