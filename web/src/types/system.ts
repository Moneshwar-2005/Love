export interface RamMetrics {
  used_gb: number;
  total_gb: number;
  percent: number;
}

export interface GpuMetrics {
  available: boolean;
  name: string;
  vram_used_gb: number | null;
  vram_total_gb: number | null;
  vram_percent: number | null;
  utilization_percent: number | null;
}

export interface LocalModelStatus {
  is_running: boolean;
  service_name: string;
  latency_ms: number | null;
  error: string | null;
}

export interface SystemMetrics {
  cpu_percent: number;
  ram: RamMetrics;
  gpu: GpuMetrics;
  local_model: LocalModelStatus;
  uptime_seconds: number;
  timestamp: string;
}

export type ActivityCategory = 'intelligence' | 'work' | 'memory' | 'voice' | 'security';

export interface SystemActivityItem {
  id: string;
  event_type: string;
  title: string;
  description: string | null;
  category: ActivityCategory;
  timestamp: string;
  metadata: Record<string, any>;
}

export interface SystemActivityResponse {
  items: SystemActivityItem[];
  total: number;
}

export interface LastBackupDetail {
  filename: string;
  created_at: string;
  size_bytes: number;
  is_valid: boolean;
  total_backups: number;
}

export interface DatabaseHealthInfo {
  engine: string;
  status: string;
  latency_ms: number;
  journal_mode?: string | null;
  foreign_keys?: boolean;
  integrity_check?: string;
  schema_revision?: string | null;
  database_size_bytes?: number;
  table_counts?: Record<string, number>;
  last_backup?: LastBackupDetail | null;
}
