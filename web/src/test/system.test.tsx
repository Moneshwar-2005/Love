import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { CommandDashboard } from '../components/dashboard/CommandDashboard';
import { DatabaseHealthCard } from '../components/dashboard/DatabaseHealthCard';
import { SystemStatusModal } from '../components/status/SystemStatusModal';
import { systemService } from '../services/systemService';
import { syncService } from '../services/syncService';
import { intelligenceService } from '../services/intelligenceService';

describe('Web System Observability & Database Health', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders command dashboard telemetry and database status', async () => {
    vi.spyOn(systemService, 'getMetrics').mockResolvedValue({
      cpu_percent: 22.5,
      ram: { used_gb: 4.2, total_gb: 16.0, percent: 26.25 },
      gpu: { available: true, name: 'GTX 1650', vram_used_gb: 1.2, vram_total_gb: 4.0, vram_percent: 30.0, utilization_percent: 15 },
      local_model: { is_running: true, service_name: 'ollama', latency_ms: 12.5, error: null },
      uptime_seconds: 3600,
      timestamp: new Date().toISOString(),
    });

    vi.spyOn(systemService, 'getDatabaseHealth').mockResolvedValue({
      engine: 'sqlite',
      status: 'healthy',
      latency_ms: 0.8,
      journal_mode: 'wal',
      foreign_keys: true,
      integrity_check: 'ok',
      schema_revision: 'c0e81b379d42',
      database_size_bytes: 524288,
      table_counts: { users: 1, conversations: 5, messages: 24, memories: 8, tasks: 3 },
      last_backup: {
        filename: 'love_backup_20261120_095038.db',
        created_at: new Date().toISOString(),
        size_bytes: 524288,
        is_valid: true,
        total_backups: 2,
      },
    });

    vi.spyOn(syncService, 'getStatus').mockResolvedValue({
      sync_enabled: false,
      sync_mode: 'standalone',
      current_cursor: 42,
      total_events: 42,
      active_devices_count: 1,
      server_time: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <AppProvider>
          <CommandDashboard onNavigate={vi.fn()} onOpenSettings={vi.fn()} />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Command & Observability Dashboard')).toBeInTheDocument();
      expect(screen.getByText(/Host Hardware & Resources/i)).toBeInTheDocument();
      expect(screen.getByText(/Database Engine & Integrity/i)).toBeInTheDocument();
      expect(screen.getByText(/Verified OK/i)).toBeInTheDocument();
      expect(screen.getByText(/Total Records/i)).toBeInTheDocument();
    });
  });

  it('triggers on-demand database backup and shows verification notice', async () => {
    const mockDb = {
      engine: 'sqlite',
      status: 'healthy',
      latency_ms: 0.5,
      journal_mode: 'wal',
      schema_revision: 'c0e81b379d42',
      table_counts: { users: 1, memories: 3 },
    };

    const backupSpy = vi.spyOn(systemService, 'createDatabaseBackup').mockResolvedValue({
      success: true,
      backup: {
        filename: 'love_backup_20261120_120000.db',
        sha256: 'mock-hash',
      },
    });

    render(<DatabaseHealthCard dbHealth={mockDb} isLoading={false} />);

    expect(screen.getByText('Backup Database')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Backup Database'));

    await waitFor(() => {
      expect(backupSpy).toHaveBeenCalled();
      expect(screen.getByText(/Backup love_backup_20261120_120000.db created & verified/i)).toBeInTheDocument();
    });
  });

  it('renders system status modal with provider catalog', async () => {
    vi.spyOn(systemService, 'getDatabaseHealth').mockResolvedValue({
      engine: 'sqlite',
      status: 'healthy',
      latency_ms: 0.8,
      journal_mode: 'wal',
      foreign_keys: true,
      integrity_check: 'ok',
      schema_revision: 'c0e81b379d42',
      database_size_bytes: 524288,
      table_counts: { users: 1 },
    });
    vi.spyOn(intelligenceService, 'listProviders').mockResolvedValue([
      { id: 'ollama', name: 'Ollama Local Engine', is_configured: true, is_available: true, is_local: true, default_model: 'qwen' },
    ]);
    vi.spyOn(intelligenceService, 'listModels').mockResolvedValue([
      { id: 'qwen:latest', name: 'Qwen 2.5 7B', provider: 'ollama', context_length: 32768, is_local: true, capabilities: ['chat'] },
    ]);

    render(
      <AuthProvider>
        <AppProvider>
          <SystemStatusModal onClose={vi.fn()} />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('System Intelligence & Hardware Profile')).toBeInTheDocument();
      expect(screen.getByText('Ollama Local Engine')).toBeInTheDocument();
      expect(screen.getByText('Qwen 2.5 7B')).toBeInTheDocument();
    });
  });
});
