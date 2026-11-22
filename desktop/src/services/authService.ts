import { apiClient } from './apiClient';
import { secureStorage } from './storageAdapter';
import {
  LoginCredentials,
  RegisterCredentials,
  TokenRefreshResponse,
  TokenResponse,
  User,
} from '../types/auth';

export class AuthService {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const platform = typeof window !== 'undefined' && window.loveDesktop?.platform;
    const defaultDeviceType =
      platform === 'win32'
        ? 'windows'
        : platform === 'darwin'
        ? 'macos'
        : platform === 'linux'
        ? 'linux'
        : 'windows';

    const payload: Record<string, any> = {
      email_or_username: credentials.username_or_email,
      password: credentials.password,
      device_name: credentials.device_name || 'LOVE Desktop App',
      device_type: credentials.device_type || defaultDeviceType,
    };

    const data = await apiClient.post<TokenResponse>('/api/v1/auth/login', payload);

    if (data.access_token) {
      await secureStorage.setItem('access_token', data.access_token);
      await secureStorage.setItem('refresh_token', data.refresh_token);
      await secureStorage.setItem('user_info', JSON.stringify(data.user));
    }

    return data;
  }

  async register(credentials: RegisterCredentials): Promise<User> {
    const payload: Record<string, any> = {
      email: credentials.email,
      username: credentials.username,
      password: credentials.password,
    };
    if (credentials.full_name) {
      payload.full_name = credentials.full_name;
    }
    if (credentials.setup_token) {
      payload.setup_token = credentials.setup_token;
    }

    return await apiClient.post<User>('/api/v1/auth/register', payload);
  }

  async logout(): Promise<void> {
    const refreshToken = await secureStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await apiClient.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      } catch (err) {
        console.warn('Backend logout call returned error (session will be cleared locally):', err);
      }
    }
    await secureStorage.clear();
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const user = await apiClient.get<User>('/api/v1/auth/me');
      await secureStorage.setItem('user_info', JSON.stringify(user));
      return user;
    } catch {
      const cached = await secureStorage.getItem('user_info');
      if (cached) {
        try {
          return JSON.parse(cached);
        } catch {
          return null;
        }
      }
      return null;
    }
  }

  async hasValidSession(): Promise<boolean> {
    const token = await secureStorage.getItem('access_token');
    return !!token;
  }

  async getStoredTokens(): Promise<{ access_token: string | null; refresh_token: string | null }> {
    return {
      access_token: await secureStorage.getItem('access_token'),
      refresh_token: await secureStorage.getItem('refresh_token'),
    };
  }
}

export const authService = new AuthService();
