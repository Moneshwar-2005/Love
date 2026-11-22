import { apiClient } from './apiClient';
import {
  DatabaseHealthInfo,
  SystemActivityResponse,
  SystemMetrics,
} from '../types/system';

export class SystemService {
  async getMetrics(): Promise<SystemMetrics> {
    return await apiClient.get<SystemMetrics>('/api/v1/system/metrics');
  }

  async getActivity(limit: number = 20, category?: string): Promise<SystemActivityResponse> {
    let url = `/api/v1/system/activity?limit=${limit}`;
    if (category) {
      url += `&category=${encodeURIComponent(category)}`;
    }
    return await apiClient.get<SystemActivityResponse>(url);
  }

  async getDatabaseHealth(): Promise<DatabaseHealthInfo> {
    return await apiClient.get<DatabaseHealthInfo>('/api/v1/system/database');
  }

  async createDatabaseBackup(): Promise<any> {
    return await apiClient.post('/api/v1/system/database/backup', {});
  }
}

export const systemService = new SystemService();
