import { apiClient } from './apiClient';
import {
  DeviceItem,
  SyncSettings,
  SyncSettingsUpdate,
  SyncStatus,
} from '../types/sync';

export class SyncService {
  async getStatus(): Promise<SyncStatus> {
    return await apiClient.get<SyncStatus>('/api/v1/sync/status');
  }

  async getSettings(): Promise<SyncSettings> {
    return await apiClient.get<SyncSettings>('/api/v1/sync/settings');
  }

  async updateSettings(update: SyncSettingsUpdate): Promise<SyncSettings> {
    return await apiClient.put<SyncSettings>('/api/v1/sync/settings', update);
  }

  async listDevices(): Promise<DeviceItem[]> {
    return await apiClient.get<DeviceItem[]>('/api/v1/devices');
  }

  async revokeDevice(deviceId: string): Promise<void> {
    await apiClient.post(`/api/v1/devices/${deviceId}/revoke`, {});
  }
}

export const syncService = new SyncService();
