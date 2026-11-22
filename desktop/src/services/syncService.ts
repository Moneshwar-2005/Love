/**
 * Cross-Device State Synchronization & Device Management API service (Phase 09).
 */

import { apiClient } from './apiClient';
import {
  DeviceItem,
  DeviceListResponse,
  SyncChangesResponse,
  SyncSettings,
  SyncSettingsUpdate,
  SyncStatus,
} from '../types/sync';

export class SyncService {
  /**
   * Retrieves high-level synchronization status and sequence cursor.
   */
  async getStatus(): Promise<SyncStatus> {
    return await apiClient.get<SyncStatus>('/api/v1/sync/status');
  }

  /**
   * Retrieves synchronization settings (mode, polling interval, etc.).
   */
  async getSettings(): Promise<SyncSettings> {
    return await apiClient.get<SyncSettings>('/api/v1/sync/settings');
  }

  /**
   * Modifies synchronization mode or parameters.
   */
  async updateSettings(update: SyncSettingsUpdate): Promise<SyncSettings> {
    return await apiClient.put<SyncSettings>('/api/v1/sync/settings', update);
  }

  /**
   * Retrieves incremental changes strictly after sinceCursor.
   */
  async getChanges(
    sinceCursor: number = 0,
    limit: number = 50,
    excludeDeviceId?: string
  ): Promise<SyncChangesResponse> {
    let url = `/api/v1/sync/changes?since_cursor=${sinceCursor}&limit=${limit}`;
    if (excludeDeviceId) {
      url += `&exclude_device_id=${encodeURIComponent(excludeDeviceId)}`;
    }
    return await apiClient.get<SyncChangesResponse>(url);
  }

  /**
   * Acknowledges that client has processed changes up to cursor.
   */
  async acknowledge(cursor: number, deviceId?: string): Promise<{ status: string; cursor: number }> {
    return await apiClient.post<{ status: string; cursor: number }>('/api/v1/sync/acknowledge', {
      cursor,
      device_id: deviceId,
    });
  }

  /**
   * Lists all client devices registered under the user account.
   */
  async listDevices(): Promise<DeviceItem[]> {
    const res = await apiClient.get<DeviceListResponse>('/api/v1/devices');
    return res.devices || [];
  }

  /**
   * Revokes authorization for a specific client device.
   */
  async revokeDevice(deviceId: string): Promise<DeviceItem> {
    return await apiClient.delete<DeviceItem>(`/api/v1/devices/${deviceId}`);
  }
}

export const syncService = new SyncService();
