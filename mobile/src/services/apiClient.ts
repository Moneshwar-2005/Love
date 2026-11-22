/**
 * LOVE Mobile API Client.
 * Implements ephemeral in-memory access token storage, native secure refresh token rotation,
 * dynamic base URL configuration (supporting Android emulator 10.0.2.2, LAN IPs, and HTTPS),
 * and SSE streaming for mobile assistant interactions.
 */

import { Capacitor } from '@capacitor/core';
import { mobileSecureStorage } from './mobileSecureStorage';

export interface ApiError {
  status: number;
  message: string;
  detail?: any;
}

export type RefreshSubscriber = (newToken: string | null) => void;

export class MobileApiClient {
  private baseUrl: string = 'https://192.168.0.176:8000';
  private accessToken: string | null = null;
  private isRefreshing: boolean = false;
  private refreshSubscribers: RefreshSubscriber[] = [];
  private onUnauthorizedCallback?: () => void;

  constructor() {
    this.initBaseUrl();
  }

  private async initBaseUrl() {
    if (typeof window !== 'undefined' && (window as any).__LOVE_API_BASE_URL__) {
      this.baseUrl = (window as any).__LOVE_API_BASE_URL__;
      return;
    }

    const saved = await mobileSecureStorage.getSavedServerUrl();
    if (saved && saved.trim()) {
      this.baseUrl = saved.trim().replace(/\/+$/, '');
      return;
    }

    if (Capacitor.getPlatform() === 'android') {
      try {
        const { Device } = await import('@capacitor/device');
        const info = await Device.getInfo();
        if (info.isVirtual) {
          // Android Emulator host loopback
          this.baseUrl = 'https://10.0.2.2:8000';
        } else {
          // Physical Android device connects to the host machine LAN IP over secure HTTPS
          this.baseUrl = 'https://192.168.0.176:8000';
        }
      } catch {
        this.baseUrl = 'https://10.0.2.2:8000';
      }
    } else {
      this.baseUrl = 'https://127.0.0.1:8000';
    }
  }

  public getBaseUrl(): string {
    return this.baseUrl || 'https://127.0.0.1:8000';
  }

  public async setBaseUrl(url: string): Promise<void> {
    const cleaned = url.trim().replace(/\/+$/, '');
    this.baseUrl = cleaned;
    await mobileSecureStorage.saveServerUrl(cleaned);
  }

  public setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  public getAccessToken(): string | null {
    return this.accessToken;
  }

  public setOnUnauthorized(callback: () => void) {
    this.onUnauthorizedCallback = callback;
  }

  private subscribeTokenRefresh(cb: RefreshSubscriber) {
    this.refreshSubscribers.push(cb);
  }

  private onTokenRefreshed(newToken: string | null) {
    const subscribers = [...this.refreshSubscribers];
    this.refreshSubscribers = [];
    subscribers.forEach((cb) => {
      try {
        cb(newToken);
      } catch (subErr) {
        console.warn('Refresh subscriber execution failed:', subErr);
      }
    });
  }

  /**
   * Refreshes the session using the rotated token from native secure storage.
   */
  public async refreshSession(): Promise<string | null> {
    const storedRefreshToken = await mobileSecureStorage.getSecureItem('refresh_token');
    if (!storedRefreshToken) {
      this.accessToken = null;
      if (this.onUnauthorizedCallback) {
        this.onUnauthorizedCallback();
      }
      return null;
    }

    try {
      const url = `${this.getBaseUrl()}/api/v1/auth/refresh`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          refresh_token: storedRefreshToken,
        }),
      });

      if (!response.ok) {
        // Failed refresh (revoked, expired, device revoked)
        await mobileSecureStorage.removeSecureItem('refresh_token');
        this.accessToken = null;
        if (this.onUnauthorizedCallback) {
          this.onUnauthorizedCallback();
        }
        return null;
      }

      const data = await response.json();
      if (data.access_token) {
        this.accessToken = data.access_token;
        if (data.refresh_token) {
          await mobileSecureStorage.setSecureItem('refresh_token', data.refresh_token);
        }
        return data.access_token;
      }

      return null;
    } catch (err) {
      console.warn('Network error during mobile session refresh:', err);
      return null;
    }
  }

  /**
   * Core HTTP request handler with automatic 401 interception & retry.
   */
  public async request<T>(
    path: string,
    options: RequestInit = {},
    retryOnAuthFailure: boolean = true
  ): Promise<T> {
    const fullUrl = `${this.getBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
    const headers = new Headers(options.headers || {});

    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }

    if (this.accessToken && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${this.accessToken}`);
    }

    let response: Response;
    try {
      response = await fetch(fullUrl, {
        ...options,
        headers,
      });
    } catch (netErr: any) {
      throw {
        status: 0,
        message: `Network failure connecting to LOVE backend: ${netErr.message || netErr}`,
      } as ApiError;
    }

    // Intercept 401 Unauthorized
    if (
      response.status === 401 &&
      retryOnAuthFailure &&
      !path.includes('/auth/login') &&
      !path.includes('/auth/refresh')
    ) {
      if (!this.isRefreshing) {
        this.isRefreshing = true;
        let newToken: string | null = null;
        try {
          newToken = await this.refreshSession();
        } finally {
          this.isRefreshing = false;
          this.onTokenRefreshed(newToken);
        }

        if (newToken) {
          return this.request<T>(path, options, false);
        } else {
          throw await this.buildError(response);
        }
      }

      // If refresh already in progress, wait in subscriber queue
      return new Promise<T>((resolve, reject) => {
        this.subscribeTokenRefresh(async (newToken) => {
          if (newToken) {
            try {
              const res = await this.request<T>(path, options, false);
              resolve(res);
            } catch (err) {
              reject(err);
            }
          } else {
            reject({
              status: 401,
              message: 'Mobile session expired. Please authenticate again.',
            } as ApiError);
          }
        });
      });
    }

    if (!response.ok) {
      throw await this.buildError(response);
    }

    // 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  }

  private async buildError(response: Response): Promise<ApiError> {
    let detail: any = null;
    let message = `API request failed with status ${response.status}`;

    try {
      const errJson = await response.json();
      if (errJson.error && errJson.error.message) {
        message = errJson.error.message;
        detail = errJson.error;
      } else if (errJson.detail) {
        if (typeof errJson.detail === 'string') {
          message = errJson.detail;
        } else if (Array.isArray(errJson.detail) && errJson.detail.length > 0) {
          const first = errJson.detail[0];
          const loc = Array.isArray(first.loc) ? first.loc.map(String).join('.') : '';
          const type = String(first.type || '');
          if (loc.includes('username')) {
            if (type.includes('pattern')) {
              message = 'Please enter a valid username (alphanumeric, underscores, and hyphens only).';
            } else if (type.includes('too_short')) {
              message = 'Username must be at least 3 characters.';
            } else {
              message = 'Please enter a valid username.';
            }
          } else if (loc.includes('email')) {
            message = 'Please enter a valid email address.';
          } else if (loc.includes('password')) {
            if (type.includes('too_short')) {
              message = 'Password must be at least 8 characters.';
            } else {
              message = 'Please enter a valid password.';
            }
          } else {
            message = 'Please complete the required fields with valid values.';
          }
        } else {
          message = 'Please complete the required fields.';
        }
        detail = errJson.detail;
      }
    } catch {
      // Body not JSON
    }

    return {
      status: response.status,
      message,
      detail,
    };
  }

  public get<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' });
  }

  public post<T>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    let payload = body;

    if (body !== undefined && !(body instanceof FormData) && !(body instanceof Blob)) {
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
      payload = JSON.stringify(body);
    }

    return this.request<T>(path, {
      ...options,
      method: 'POST',
      headers,
      body: payload,
    });
  }

  public put<T>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    let payload = body;

    if (body !== undefined && !(body instanceof FormData)) {
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
      payload = JSON.stringify(body);
    }

    return this.request<T>(path, {
      ...options,
      method: 'PUT',
      headers,
      body: payload,
    });
  }

  public patch<T>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    let payload = body;

    if (body !== undefined && !(body instanceof FormData)) {
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
      payload = JSON.stringify(body);
    }

    return this.request<T>(path, {
      ...options,
      method: 'PATCH',
      headers,
      body: payload,
    });
  }

  public delete<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' });
  }

  /**
   * Real-time Server-Sent Events (SSE) Stream for Assistant dialogue.
   */
  public async fetchStream(
    path: string,
    body: any,
    signal?: AbortSignal
  ): Promise<ReadableStreamDefaultReader<Uint8Array>> {
    const fullUrl = `${this.getBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
    const headers = new Headers({
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    });

    if (this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`);
    }

    const response = await fetch(fullUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      throw await this.buildError(response);
    }

    if (!response.body) {
      throw new Error('Response body is null, SSE stream unavailable');
    }

    return response.body.getReader();
  }
}

export const mobileApiClient = new MobileApiClient();
