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
  is_sqlite: boolean;
  is_postgresql: boolean;
  journal_mode: string | null;
  foreign_keys_enabled: boolean;
  integrity_status: string;
  alembic_revision: string | null;
  database_size_bytes: number;
  database_size_mb: number;
  table_counts: Record<string, number>;
  wal_file_present: boolean;
  last_backup: LastBackupDetail | null;
  timestamp: string;
}

export interface DatabaseBackupDetail {
  backup_id: string;
  filename: string;
  backup_path: string;
  source_db: string;
  created_at: string;
  size_bytes: number;
  size_mb: number;
  sha256: string;
  is_valid: boolean;
  integrity_status: string;
  alembic_revision?: string | null;
  tables_count: number;
  table_counts?: Record<string, number>;
}

