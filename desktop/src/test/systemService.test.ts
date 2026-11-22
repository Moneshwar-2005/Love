import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SystemService } from '../services/systemService';
import { apiClient } from '../services/apiClient';

describe('SystemService', () => {
  let system: SystemService;

  beforeEach(() => {
    system = new SystemService();
    vi.restoreAllMocks();
  });

  it('fetches live system hardware metrics', async () => {
    const mockMetrics = {
      cpu_percent: 12.5,
      ram: { used_gb: 8.0, total_gb: 16.0, percent: 50.0 },
      gpu: {
        available: true,
        name: 'NVIDIA GeForce GTX 1650',
        vram_used_gb: 1.0,
        vram_total_gb: 4.0,
        vram_percent: 25.0,
        utilization_percent: 15.0,
      },
      local_model: {
        is_running: true,
        service_name: 'ollama',
        latency_ms: 35.0,
        error: null,
      },
      uptime_seconds: 120.5,
      timestamp: '2026-11-20T06:00:00Z',
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockMetrics);

    const metrics = await system.getMetrics();
    expect(metrics).toEqual(mockMetrics);
    expect(getSpy).toHaveBeenCalledWith('/api/v1/system/metrics');
  });

  it('fetches unified system activity timeline', async () => {
    const mockActivity = {
      items: [
        {
          id: 'conv-1',
          event_type: 'conversation_created',
          title: 'Started Conversation',
          description: null,
          category: 'intelligence',
          timestamp: '2026-11-20T06:00:00Z',
          metadata: {},
        },
      ],
      total: 1,
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockActivity);

    const activity = await system.getActivity(10);
    expect(activity).toEqual(mockActivity);
    expect(getSpy).toHaveBeenCalledWith('/api/v1/system/activity?limit=10');
  });

  it('lists registered client devices', async () => {
    const mockDevices = {
      devices: [
        {
          id: 'dev-1',
          device_identifier: 'win-test-uuid',
          device_name: 'Main Rig',
          device_type: 'windows',
          client_version: '1.0.0',
          is_trusted: true,
          is_revoked: false,
          created_at: '2026-11-20T06:00:00Z',
        },
      ],
      total: 1,
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockDevices);

    const res = await system.listDevices();
    expect(res).toEqual(mockDevices);
    expect(getSpy).toHaveBeenCalledWith('/api/v1/devices');
  });

  it('fetches database architecture health and diagnostics', async () => {
    const mockDbHealth = {
      engine: 'sqlite',
      status: 'connected',
      latency_ms: 2.5,
      is_sqlite: true,
      is_postgresql: false,
      journal_mode: 'WAL',
      foreign_keys_enabled: true,
      integrity_status: 'ok',
      alembic_revision: 'c0e81b379d42',
      database_size_bytes: 350000,
      database_size_mb: 0.35,
      table_counts: { users: 4, tasks: 7 },
      wal_file_present: true,
      last_backup: null,
      timestamp: '2026-11-20T06:00:00Z',
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockDbHealth);

    const res = await system.getDatabaseHealth();
    expect(res).toEqual(mockDbHealth);
    expect(getSpy).toHaveBeenCalledWith('/api/v1/system/database');
  });

  it('triggers database backup creation', async () => {
    const mockBackupRes = {
      success: true,
      message: 'Backup created',
      backup: {
        backup_id: 'b1',
        filename: 'love_backup_test.db',
        backup_path: 'F:/LOVE/database/backups/love_backup_test.db',
        source_db: 'love.db',
        created_at: '2026-11-20T06:00:00Z',
        size_bytes: 350000,
        size_mb: 0.35,
        sha256: 'abc123hash',
        is_valid: true,
        integrity_status: 'ok',
        tables_count: 15,
      },
    };

    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockBackupRes);

    const res = await system.createDatabaseBackup();
    expect(res).toEqual(mockBackupRes);
    expect(postSpy).toHaveBeenCalledWith('/api/v1/system/database/backup', {});
  });
});
