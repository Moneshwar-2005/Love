import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthService } from '../services/authService';
import { apiClient } from '../services/apiClient';
import { secureStorage } from '../services/storageAdapter';

describe('AuthService', () => {
  let auth: AuthService;

  beforeEach(() => {
    auth = new AuthService();
    vi.restoreAllMocks();
  });

  it('authenticates user and securely stores access and refresh tokens', async () => {
    const mockTokenResponse = {
      access_token: 'valid_access_jwt',
      refresh_token: 'valid_refresh_jwt',
      token_type: 'Bearer',
      expires_in: 900,
      user: {
        id: 'usr-1',
        email: 'owner@example.com',
        username: 'love_owner',
        role: 'owner',
        is_active: true,
        is_owner: true,
        created_at: new Date().toISOString(),
      },
    };

    vi.spyOn(apiClient, 'post').mockResolvedValue(mockTokenResponse);
    const setItemSpy = vi.spyOn(secureStorage, 'setItem').mockResolvedValue(true);

    const res = await auth.login({
      username_or_email: 'love_owner',
      password: 'StrongPassword123!',
    });

    expect(res.user.username).toBe('love_owner');
    expect(setItemSpy).toHaveBeenCalledWith('access_token', 'valid_access_jwt');
    expect(setItemSpy).toHaveBeenCalledWith('refresh_token', 'valid_refresh_jwt');
    expect(setItemSpy).toHaveBeenCalledWith('user_info', JSON.stringify(mockTokenResponse.user));
  });

  it('logs out and clears secure token vault', async () => {
    vi.spyOn(secureStorage, 'getItem').mockResolvedValue('refresh_jwt');
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue({ message: 'Logged out' });
    const clearSpy = vi.spyOn(secureStorage, 'clear').mockResolvedValue(true);

    await auth.logout();

    expect(postSpy).toHaveBeenCalledWith('/api/v1/auth/logout', { refresh_token: 'refresh_jwt' });
    expect(clearSpy).toHaveBeenCalled();
  });

  it('checks hasValidSession based on stored access token', async () => {
    vi.spyOn(secureStorage, 'getItem').mockResolvedValueOnce('token_exists').mockResolvedValueOnce(null);

    expect(await auth.hasValidSession()).toBe(true);
    expect(await auth.hasValidSession()).toBe(false);
  });
});
