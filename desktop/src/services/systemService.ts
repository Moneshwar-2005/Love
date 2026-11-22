import { apiClient } from './apiClient';
import {
  DatabaseBackupDetail,
  DatabaseHealthInfo,
  SystemActivityResponse,
  SystemMetrics,
} from '../types/system';

export interface DeviceInfo {
  id: string;
  device_identifier: string;
  device_name: string;
  device_type: string;
  client_version?: string | null;
  is_trusted: boolean;
  is_revoked: boolean;
  revoked_at?: string | null;
  last_seen_at?: string | null;
  created_at: string;
}

export interface DeviceListResponse {
  devices: DeviceInfo[];
  total: number;
}

export class SystemService {
  async getMetrics(): Promise<SystemMetrics> {
    return await apiClient.get<SystemMetrics>('/api/v1/system/metrics');
  }

  async getActivity(limit: number = 20): Promise<SystemActivityResponse> {
    return await apiClient.get<SystemActivityResponse>(`/api/v1/system/activity?limit=${limit}`);
  }

  async listDevices(): Promise<DeviceListResponse> {
    return await apiClient.get<DeviceListResponse>('/api/v1/devices');
  }

  async getDatabaseHealth(): Promise<DatabaseHealthInfo> {
    return await apiClient.get<DatabaseHealthInfo>('/api/v1/system/database');
  }

  async createDatabaseBackup(): Promise<{ success: boolean; message: string; backup: DatabaseBackupDetail }> {
    return await apiClient.post<{ success: boolean; message: string; backup: DatabaseBackupDetail }>(
      '/api/v1/system/database/backup',
      {}
    );
  }

  async listDatabaseBackups(): Promise<{ backups: DatabaseBackupDetail[]; total: number }> {
    return await apiClient.get<{ backups: DatabaseBackupDetail[]; total: number }>('/api/v1/system/database/backups');
  }
}

export const systemService = new SystemService();
