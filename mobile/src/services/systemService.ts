/**
 * LOVE Mobile System Observability & Database Health Service.
 */

import { DatabaseBackupResponse, DatabaseHealthInfo, HostMetrics } from '../types/system';
import { mobileApiClient } from './apiClient';

export class MobileSystemService {
  async getMetrics(): Promise<HostMetrics> {
    return await mobileApiClient.get<HostMetrics>('/api/v1/system/metrics');
  }

  async getDatabaseHealth(): Promise<DatabaseHealthInfo> {
    return await mobileApiClient.get<DatabaseHealthInfo>('/api/v1/system/database/health');
  }

  async createDatabaseBackup(): Promise<DatabaseBackupResponse> {
    return await mobileApiClient.post<DatabaseBackupResponse>('/api/v1/system/database/backup');
  }
}

export const mobileSystemService = new MobileSystemService();
