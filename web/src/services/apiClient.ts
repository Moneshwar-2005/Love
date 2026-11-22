export interface ApiError {
  status: number;
  message: string;
  detail?: any;
}

export class ApiClient {
  private baseUrl: string = 'http://127.0.0.1:8000';
  private accessToken: string | null = null;
  private isRefreshing: boolean = false;
  private refreshSubscribers: Array<(token: string | null) => void> = [];
  private onUnauthorizedCallback: (() => void) | null = null;

  constructor(customBaseUrl?: string) {
    if (customBaseUrl) {
      this.baseUrl = customBaseUrl.replace(/\/+$/, '');
    } else if (typeof window !== 'undefined' && (window as any).__LOVE_API_BASE_URL__) {
      this.baseUrl = (window as any).__LOVE_API_BASE_URL__.replace(/\/+$/, '');
    } else if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
      this.baseUrl = import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
    }
    if (typeof window !== 'undefined') {
      (window as any).apiClient = this;
    }
  }

  setBaseUrl(url: string) {
    this.baseUrl = url.replace(/\/+$/, '');
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  setOnUnauthorized(callback: () => void) {
    this.onUnauthorizedCallback = callback;
  }

  private onTokenRefreshed(newToken: string | null) {
    const subscribers = [...this.refreshSubscribers];
    this.refreshSubscribers = [];
    subscribers.forEach((callback) => {
      try {
        callback(newToken);
      } catch (err) {
        console.error('Error executing refresh subscriber:', err);
      }
    });
  }

  private addRefreshSubscriber(callback: (token: string | null) => void) {
    this.refreshSubscribers.push(callback);
  }

  async refreshSession(): Promise<string | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        this.accessToken = null;
        if (this.onUnauthorizedCallback) this.onUnauthorizedCallback();
        return null;
      }

      const data = await response.json();
      this.accessToken = data.access_token;
      return data.access_token;
    } catch (err) {
      console.warn('Refresh session network error:', err);
      this.accessToken = null;
      return null;
    }
  }

  async request<T = any>(
    path: string,
    options: RequestInit = {},
    retryOnAuthFailure: boolean = true
  ): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;

    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (this.accessToken && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include',
      });
    } catch (netErr: any) {
      throw {
        status: 0,
        message: `Network failure connecting to LOVE backend: ${netErr.message || netErr}`,
      } as ApiError;
    }

    // Handle 401 Unauthorized via refresh token
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

      // If refresh is already in-flight, await new token
      return new Promise<T>((resolve, reject) => {
        this.addRefreshSubscriber(async (newToken) => {
          if (newToken) {
            try {
              const res = await this.request<T>(path, options, false);
              resolve(res);
            } catch (retryErr) {
              reject(retryErr);
            }
          } else {
            reject({
              status: 401,
              message: 'Authentication session expired. Please log in again.',
            } as ApiError);
          }
        });
      });
    }

    if (!response.ok) {
      throw await this.buildError(response);
    }

    if (response.status === 204) {
      return {} as T;
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
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
      } else if (data.error?.message) {
        message = data.error.message;
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

  async fetchStream(path: string, body: any, signal?: AbortSignal): Promise<Response> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      throw await this.buildError(response);
    }
    return response;
  }
}

export const apiClient = new ApiClient();
