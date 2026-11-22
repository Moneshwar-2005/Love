import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiClient } from '../services/apiClient';
import { secureStorage } from '../services/storageAdapter';

describe('ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient('http://127.0.0.1:8000');
    vi.restoreAllMocks();
  });

  it('injects Authorization Bearer token when available', async () => {
    vi.spyOn(secureStorage, 'getItem').mockResolvedValue('test-access-token');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ success: true }),
    });
    global.fetch = mockFetch;

    const result = await client.get('/api/v1/test');

    expect(result).toEqual({ success: true });
    expect(mockFetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/v1/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-access-token',
        }),
      })
    );
  });

  it('refreshes token on 401 and replays request', async () => {
    let callCount = 0;
    vi.spyOn(secureStorage, 'getItem').mockImplementation(async (key: string) => {
      if (key === 'refresh_token') return 'mock-refresh-token';
      if (key === 'access_token') return callCount === 0 ? 'expired-token' : 'new-access-token';
      return null;
    });
    vi.spyOn(secureStorage, 'setItem').mockResolvedValue(true);

    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/refresh')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              access_token: 'new-access-token',
              refresh_token: 'new-refresh-token',
            }),
        });
      }

      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: 'Token expired' }),
        });
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ message: 'Success after retry' }),
      });
    });

    global.fetch = mockFetch;

    const data = await client.get('/api/v1/protected');
    expect(data).toEqual({ message: 'Success after retry' });
    expect(mockFetch).toHaveBeenCalledTimes(3); // 1: original 401, 2: refresh, 3: retried
  });

  it('handles network failure gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    await expect(client.get('/api/v1/health')).rejects.toEqual(
      expect.objectContaining({
        status: 0,
        message: expect.stringContaining('Network failure'),
      })
    );
  });
});
