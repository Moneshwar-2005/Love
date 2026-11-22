import { apiClient } from './apiClient';
import {
  AuthTokens,
  LoginPayload,
  LoginResponse,
  RegisterPayload,
  User,
} from '../types/auth';

export class AuthService {
  async register(payload: RegisterPayload): Promise<User> {
    return await apiClient.post<User>('/api/v1/auth/register', payload);
  }

  async login(payload: LoginPayload): Promise<LoginResponse> {
    // Generate or read persistent client-side installation ID for device registration
    let deviceIdentifier = localStorage.getItem('love_web_device_id');
    if (!deviceIdentifier) {
      if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        deviceIdentifier = `web-${crypto.randomUUID()}`;
      } else {
        deviceIdentifier = `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
      }
      localStorage.setItem('love_web_device_id', deviceIdentifier);
    }

    const enhancedPayload: LoginPayload = {
      ...payload,
      device_identifier: payload.device_identifier || deviceIdentifier,
      device_name: payload.device_name || 'LOVE Web Client',
      device_type: 'web',
      client_version: '1.0.0',
    };

    const res = await apiClient.post<LoginResponse>('/api/v1/auth/login', enhancedPayload);
    apiClient.setAccessToken(res.access_token);
    return res;
  }

  async refresh(): Promise<AuthTokens | null> {
    const token = await apiClient.refreshSession();
    if (!token) return null;
    return {
      access_token: token,
      token_type: 'Bearer',
      expires_in: 3600,
    };
  }

  async getMe(): Promise<User> {
    return await apiClient.get<User>('/api/v1/auth/me');
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout', {});
    } catch (err) {
      console.warn('Logout endpoint error (proceeding with local cleanup):', err);
    } finally {
      apiClient.setAccessToken(null);
    }
  }
}

export const authService = new AuthService();
