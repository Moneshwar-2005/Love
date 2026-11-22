/**
 * LOVE Mobile Authentication Service.
 * Manages native login, registration, session restoration, device binding, and logout.
 */

import { Capacitor } from '@capacitor/core';
import { DeviceInfo, LoginPayload, LoginResponse, RegisterPayload, User } from '../types/auth';
import { mobileApiClient } from './apiClient';
import { mobileSecureStorage } from './mobileSecureStorage';

export class MobileAuthService {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    const deviceId = await mobileSecureStorage.getOrCreateDeviceId();
    const platform = Capacitor.getPlatform() === 'ios' ? 'ios' : 'android';
    const deviceName = platform === 'ios' ? 'LOVE Mobile (iOS)' : 'LOVE Mobile (Android)';

    const body: LoginPayload = {
      ...payload,
      device_identifier: deviceId,
      device_name: payload.device_name || deviceName,
      device_type: platform,
      client_version: '1.0.0',
    };

    const resp = await mobileApiClient.post<LoginResponse>('/api/v1/auth/login', body);

    if (resp.access_token) {
      mobileApiClient.setAccessToken(resp.access_token);
    }
    if (resp.refresh_token) {
      await mobileSecureStorage.setSecureItem('refresh_token', resp.refresh_token);
    }

    return resp;
  }

  async register(payload: RegisterPayload): Promise<User> {
    return await mobileApiClient.post<User>('/api/v1/auth/register', payload);
  }

  async refresh(): Promise<boolean> {
    const token = await mobileApiClient.refreshSession();
    return token !== null;
  }

  async logout(): Promise<void> {
    try {
      const storedRefreshToken = await mobileSecureStorage.getSecureItem('refresh_token');
      await mobileApiClient.post('/api/v1/auth/logout', {
        refresh_token: storedRefreshToken,
      });
    } catch (err) {
      console.warn('Backend logout call notification error:', err);
    } finally {
      await mobileSecureStorage.removeSecureItem('refresh_token');
      mobileApiClient.setAccessToken(null);
    }
  }

  async getMe(): Promise<User> {
    return await mobileApiClient.get<User>('/api/v1/auth/me');
  }

  async listDevices(): Promise<DeviceInfo[]> {
    const resp = await mobileApiClient.get<{ devices: DeviceInfo[]; total: number }>('/api/v1/devices');
    return resp.devices || [];
  }

  async revokeDevice(deviceId: string): Promise<void> {
    await mobileApiClient.delete(`/api/v1/devices/${deviceId}`);
  }
}

export const mobileAuthService = new MobileAuthService();
