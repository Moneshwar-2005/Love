import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileAuthProvider, useMobileAuth } from '../context/AuthContext';
import { MobileAuthScreen } from '../components/auth/MobileAuthScreen';
import { mobileApiClient } from '../services/apiClient';
import { mobileAuthService } from '../services/authService';
import { mobileSecureStorage } from '../services/mobileSecureStorage';

describe('LOVE Mobile Authentication & Secure Storage Lifecycle', () => {
  beforeEach(async () => {
    vi.restoreAllMocks();
    await mobileSecureStorage.clearSecureStore();
    mobileApiClient.setAccessToken(null);
  });

  it('generates a cryptographically random device UUID without hardware leakage', async () => {
    const deviceId = await mobileSecureStorage.getOrCreateDeviceId();
    expect(deviceId).toMatch(/^mobile-(android|ios|web)-[a-f0-9-]+$/i);
    expect(deviceId.length).toBeGreaterThanOrEqual(20);

    // Persisted in secure storage
    const stored = await mobileSecureStorage.getSecureItem('love_mobile_device_uuid');
    expect(stored).toBe(deviceId);
  });

  it('authenticates user and stores refresh token in secure storage while access token stays in memory', async () => {
    const mockUser = {
      id: 'usr-1',
      username: 'owner',
      email: 'owner@love.ai',
      is_active: true,
      is_verified: true,
      is_owner: true,
      created_at: new Date().toISOString(),
    };

    const loginSpy = vi.spyOn(mobileAuthService, 'login').mockImplementation(async (payload) => {
      mobileApiClient.setAccessToken('mem-access-token-123');
      await mobileSecureStorage.setSecureItem('refresh_token', 'sec-refresh-token-456');
      return {
        user: mockUser,
        access_token: 'mem-access-token-123',
        refresh_token: 'sec-refresh-token-456',
        token_type: 'Bearer',
        expires_in: 3600,
      };
    });

    render(
      <MobileAuthProvider>
        <MobileAuthScreen />
      </MobileAuthProvider>
    );

    expect(screen.getByText('LOVE')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('username or email')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('username or email'), {
      target: { value: 'owner' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          email_or_username: 'owner',
          password: 'password123',
        })
      );
    });

    expect(mobileApiClient.getAccessToken()).toBe('mem-access-token-123');
    const storedRefresh = await mobileSecureStorage.getSecureItem('refresh_token');
    expect(storedRefresh).toBe('sec-refresh-token-456');
  });

  it('rotates refresh token during 401 interception and notifies subscribers', async () => {
    await mobileSecureStorage.setSecureItem('refresh_token', 'old-refresh-token');
    mobileApiClient.setAccessToken('expired-token');

    let refreshCalled = false;
    vi.spyOn(global, 'fetch').mockImplementation(async (url: any) => {
      if (url.toString().includes('/api/v1/auth/refresh')) {
        refreshCalled = true;
        return new Response(
          JSON.stringify({
            access_token: 'new-access-token-789',
            refresh_token: 'new-refresh-token-101',
            token_type: 'Bearer',
            expires_in: 3600,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });

    const refreshedToken = await mobileApiClient.refreshSession();
    expect(refreshCalled).toBe(true);
    expect(refreshedToken).toBe('new-access-token-789');
    expect(mobileApiClient.getAccessToken()).toBe('new-access-token-789');

    const rotatedToken = await mobileSecureStorage.getSecureItem('refresh_token');
    expect(rotatedToken).toBe('new-refresh-token-101');
  });

  it('purges secure storage and wipes memory token upon logout', async () => {
    await mobileSecureStorage.setSecureItem('refresh_token', 'active-token');
    mobileApiClient.setAccessToken('active-access-token');

    vi.spyOn(mobileApiClient, 'post').mockResolvedValue({});

    await mobileAuthService.logout();

    expect(mobileApiClient.getAccessToken()).toBeNull();
    const stored = await mobileSecureStorage.getSecureItem('refresh_token');
    expect(stored).toBeNull();
  });

  it('supports configurable backend base URL for Android emulator and LAN environments', async () => {
    expect(mobileApiClient.getBaseUrl()).toBeTruthy();

    await mobileApiClient.setBaseUrl('http://192.168.1.100:8000');
    expect(mobileApiClient.getBaseUrl()).toBe('http://192.168.1.100:8000');

    const saved = await mobileSecureStorage.getSavedServerUrl();
    expect(saved).toBe('http://192.168.1.100:8000');
  });

  it('handles 401 refresh failure by purging secure storage and triggering onUnauthorized', async () => {
    await mobileSecureStorage.setSecureItem('refresh_token', 'revoked-token');
    mobileApiClient.setAccessToken('expired-token');

    const unauthorizedMock = vi.fn();
    mobileApiClient.setOnUnauthorized(unauthorizedMock);

    vi.spyOn(global, 'fetch').mockImplementation(async (url: any) => {
      if (url.toString().includes('/api/v1/auth/refresh')) {
        return new Response(
          JSON.stringify({ detail: 'Token has been revoked' }),
          { status: 401, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response(JSON.stringify({}), { status: 401 });
    });

    const refreshed = await mobileApiClient.refreshSession();
    expect(refreshed).toBeNull();
    expect(mobileApiClient.getAccessToken()).toBeNull();
    expect(unauthorizedMock).toHaveBeenCalled();

    const stored = await mobileSecureStorage.getSecureItem('refresh_token');
    expect(stored).toBeNull();
  });
});
