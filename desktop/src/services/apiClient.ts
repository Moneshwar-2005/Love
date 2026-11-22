import { secureStorage } from './storageAdapter';

export interface ApiError {
  status: number;
  message: string;
  detail?: any;
}

export class ApiClient {
  private baseUrl: string = 'http://127.0.0.1:8000';
  private isRefreshing: boolean = false;
  private refreshSubscribers: Array<(token: string | null) => void> = [];

  constructor(customBaseUrl?: string) {
    if (customBaseUrl) {
      this.baseUrl = customBaseUrl;
    }
  }

  setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/+$/, '');
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private onTokenRefreshed(newToken: string | null) {
    this.refreshSubscribers.forEach((callback) => callback(newToken));
    this.refreshSubscribers = [];
  }

  private addRefreshSubscriber(callback: (token: string | null) => void) {
    this.refreshSubscribers.push(callback);
  }

  private async refreshTokens(): Promise<string | null> {
    const refreshToken = await secureStorage.getItem('refresh_token');
    if (!refreshToken) {
      await secureStorage.clear();
      return null;
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        await secureStorage.clear();
        return null;
      }

      const data = await response.json();
      await secureStorage.setItem('access_token', data.access_token);
      await secureStorage.setItem('refresh_token', data.refresh_token);
      return data.access_token;
    } catch (err) {
      console.error('Failed to refresh tokens:', err);
      await secureStorage.clear();
      return null;
    }
  }

  async request<T = any>(
    path: string,
    options: RequestInit = {},
    retryOnAuthFailure: boolean = true
  ): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    const token = await secureStorage.getItem('access_token');

    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    let response: Response;
    try {
      response = await fetch(url, { ...options, headers });
    } catch (netErr: any) {
      throw {
        status: 0,
        message: `Network failure connecting to LOVE backend: ${netErr.message || netErr}`,
      } as ApiError;
    }

    // Handle token expiration & automatic refresh
    if (response.status === 401 && retryOnAuthFailure && !path.includes('/auth/login') && !path.includes('/auth/refresh')) {
      if (!this.isRefreshing) {
        this.isRefreshing = true;
        const newToken = await this.refreshTokens();
        this.isRefreshing = false;
        this.onTokenRefreshed(newToken);

        if (newToken) {
          headers['Authorization'] = `Bearer ${newToken}`;
          const retryRes = await fetch(url, { ...options, headers });
          if (!retryRes.ok) {
            throw await this.buildError(retryRes);
          }
          return await retryRes.json();
        }
      } else {
        // Wait for token refresh to resolve
        return new Promise((resolve, reject) => {
          this.addRefreshSubscriber(async (newToken) => {
            if (!newToken) {
              reject({ status: 401, message: 'Session expired. Please log in again.' });
              return;
            }
            try {
              headers['Authorization'] = `Bearer ${newToken}`;
              const retryRes = await fetch(url, { ...options, headers });
              if (!retryRes.ok) {
                reject(await this.buildError(retryRes));
              } else {
                resolve(await retryRes.json());
              }
            } catch (err) {
              reject(err);
            }
          });
        });
      }
    }

    if (!response.ok) {
      throw await this.buildError(response);
    }

    // Check if JSON response
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return (await response.json()) as T;
    }

    return (await response.text()) as unknown as T;
  }

  private async buildError(response: Response): Promise<ApiError> {
    let detail: any = null;
    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      detail = data;
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
      } else if (data.message) {
        message = data.message;
      }
    } catch {
      message = response.statusText || message;
    }

    return {
      status: response.status,
      message,
      detail,
    };
  }

  get<T = any>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' });
  }

  post<T = any>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    const isFormData = body instanceof FormData;
    return this.request<T>(path, {
      ...options,
      method: 'POST',
      body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  put<T = any>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  delete<T = any>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' });
  }

  async fetchStream(path: string, body: any): Promise<Response> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    const token = await secureStorage.getItem('access_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw await this.buildError(response);
    }
    return response;
  }
}

export const apiClient = new ApiClient();
