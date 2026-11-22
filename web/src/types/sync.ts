export type SyncMode = 'standalone' | 'multi_device';

export interface SyncStatus {
  sync_enabled: boolean;
  sync_mode: SyncMode;
  current_cursor: number;
  total_events: number;
  active_devices_count: number;
  last_synced_at?: string | null;
  server_time: string;
}

export interface SyncSettings {
  sync_enabled: boolean;
  sync_mode: SyncMode;
  auto_sync_interval_seconds: number;
  conflict_resolution: string;
  updated_at: string;
}

export interface SyncSettingsUpdate {
  sync_enabled?: boolean;
  sync_mode?: SyncMode;
  auto_sync_interval_seconds?: number;
}

export interface DeviceItem {
  id: string;
  user_id: string;
  device_identifier: string;
  device_name: string;
  device_type: 'windows' | 'macos' | 'linux' | 'android' | 'ios' | 'web' | 'other';
  client_version?: string | null;
  is_trusted: boolean;
  is_revoked: boolean;
  revoked_at?: string | null;
  last_seen_at?: string | null;
  created_at: string;
}
