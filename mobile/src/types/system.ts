export interface HostMetrics {
  cpu_percent: number;
  ram: {
    used_gb: number;
    total_gb: number;
    percent: number;
  };
  gpu?: {
    available: boolean;
    name?: string;
    vram_used_gb?: number;
    vram_total_gb?: number;
    vram_percent?: number;
    utilization_percent?: number;
  } | null;
  local_model?: {
    is_running: boolean;
    service_name: string;
    latency_ms: number;
    error?: string | null;
  } | null;
  uptime_seconds: number;
  timestamp: string;
}

export interface DatabaseHealthInfo {
  engine: string;
  status: string;
  latency_ms: number;
  journal_mode: string;
  foreign_keys?: boolean;
  integrity_check?: string;
  schema_revision?: string;
  database_size_bytes?: number;
  table_counts?: Record<string, number>;
  last_backup?: {
    filename: string;
    created_at: string;
    size_bytes: number;
    is_valid: boolean;
    total_backups: number;
  } | null;
}

export interface DatabaseBackupResponse {
  success: boolean;
  backup: {
    filename: string;
    size_bytes?: number;
    sha256?: string;
    created_at?: string;
  };
}
