/**
 * LOVE Mobile Synchronization Service.
 * Connects to the backend event-based synchronization architecture.
 * Standalone mode is the default; multi-device synchronization requires explicit opt-in.
 */

import { SyncEvent, SyncSettings, SyncStatus } from '../types/sync';
import { mobileApiClient } from './apiClient';

export class MobileSyncService {
  async getStatus(): Promise<SyncStatus> {
    return await mobileApiClient.get<SyncStatus>('/api/v1/sync/status');
  }

  async getSettings(): Promise<SyncSettings> {
    return await mobileApiClient.get<SyncSettings>('/api/v1/sync/settings');
  }

  async updateSettings(settings: Partial<SyncSettings>): Promise<SyncSettings> {
    return await mobileApiClient.put<SyncSettings>('/api/v1/sync/settings', settings);
  }

  async pullEvents(cursor: number = 0, limit: number = 50): Promise<{ events: SyncEvent[]; next_cursor: number }> {
    return await mobileApiClient.get<{ events: SyncEvent[]; next_cursor: number }>(
      `/api/v1/sync/events?cursor=${cursor}&limit=${limit}`
    );
  }

  async acknowledgeCursor(cursor: number): Promise<{ success: boolean; confirmed_cursor: number }> {
    return await mobileApiClient.post<{ success: boolean; confirmed_cursor: number }>(
      '/api/v1/sync/cursor',
      { cursor }
    );
  }
}

export const mobileSyncService = new MobileSyncService();
