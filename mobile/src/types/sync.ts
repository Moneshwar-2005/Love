export interface SyncStatus {
  sync_enabled: boolean;
  sync_mode: string;
  current_cursor: number;
  total_events: number;
  active_devices_count: number;
  server_time: string;
}

export interface SyncSettings {
  sync_enabled: boolean;
  sync_mode: string;
  auto_sync_interval_seconds: number;
  sync_on_change: boolean;
}

export interface SyncEvent {
  id: string;
  cursor: number;
  entity_type: string;
  entity_id: string;
  action: 'create' | 'update' | 'delete';
  payload: Record<string, any>;
  origin_device_id: string;
  created_at: string;
}
