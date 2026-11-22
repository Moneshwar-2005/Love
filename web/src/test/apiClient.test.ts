import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiClient } from '../services/apiClient';

describe('Web ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient('http://127.0.0.1:8000');
    vi.restoreAllMocks();
  });

  it('injects in-memory Authorization Bearer token and includes credentials', async () => {
    client.setAccessToken('mem-access-token');

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
        credentials: 'include',
        headers: expect.objectContaining({
          Authorization: 'Bearer mem-access-token',
        }),
      })
    );
  });

  it('refreshes token on 401 using HttpOnly cookie and replays request', async () => {
    let callCount = 0;
    client.setAccessToken('expired-token');

    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/refresh')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              access_token: 'new-rotated-access-token',
              token_type: 'Bearer',
              expires_in: 3600,
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
        json: () => Promise.resolve({ message: 'Success after automatic refresh' }),
      });
    });

    global.fetch = mockFetch;

    const data = await client.get('/api/v1/protected');
    expect(data).toEqual({ message: 'Success after automatic refresh' });
    expect(client.getAccessToken()).toBe('new-rotated-access-token');
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it('triggers onUnauthorized callback when refresh fails', async () => {
    const unauthSpy = vi.fn();
    client.setOnUnauthorized(unauthSpy);
    client.setAccessToken('invalid-token');

    const mockFetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/refresh')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: 'Refresh session revoked' }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Unauthorized' }),
      });
    });
    global.fetch = mockFetch;

    await expect(client.get('/api/v1/protected')).rejects.toEqual(
      expect.objectContaining({
        status: 401,
      })
    );
    expect(unauthSpy).toHaveBeenCalled();
    expect(client.getAccessToken()).toBeNull();
  });

  it('handles network failure gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Connection refused'));

    await expect(client.get('/api/v1/health')).rejects.toEqual(
      expect.objectContaining({
        status: 0,
        message: expect.stringContaining('Network failure connecting to LOVE backend'),
      })
    );
  });

  it('fetchStream passes text/event-stream accept header and credentials', async () => {
    client.setAccessToken('stream-token');
    const mockResponse = {
      ok: true,
      status: 200,
      body: {} as any,
    };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    const res = await client.fetchStream('/api/v1/intelligence/chat/stream', {
      message: 'Hello',
    });
    expect(res).toBe(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/v1/intelligence/chat/stream',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          Accept: 'text/event-stream',
          Authorization: 'Bearer stream-token',
        }),
      })
    );
  });
});
