import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { IdentityStateCard } from '../components/dashboard/IdentityStateCard';
import { HardwareMetricsCard } from '../components/dashboard/HardwareMetricsCard';
import { ActivityTimeline } from '../components/dashboard/ActivityTimeline';
import { DatabaseHealthCard } from '../components/dashboard/DatabaseHealthCard';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { SystemActivityItem, SystemMetrics } from '../types/system';

describe('Command Dashboard Components', () => {
  it('renders IdentityStateCard with assistant state and model routing info', async () => {
    await act(async () => {
      render(
        <AuthProvider>
          <AppProvider>
            <IdentityStateCard
              lastUpdated={new Date('2026-11-20T06:00:00Z')}
              isLoading={false}
              onRefresh={vi.fn()}
              uptimeSeconds={3600}
              onNavigate={vi.fn()}
            />
          </AppProvider>
        </AuthProvider>
      );
    });

    expect(screen.getByText('LOVE Command Core')).toBeInTheDocument();
    expect(screen.getByText('SOVEREIGN AI')).toBeInTheDocument();
    expect(screen.getByText('1h 0m')).toBeInTheDocument();
    expect(screen.getByText('Active Model:')).toBeInTheDocument();
  });

  it('renders HardwareMetricsCard with live CPU, RAM, and GPU readings', () => {
    const mockMetrics: SystemMetrics = {
      cpu_percent: 18.5,
      ram: { used_gb: 10.5, total_gb: 16.0, percent: 65.6 },
      gpu: {
        available: true,
        name: 'NVIDIA GeForce GTX 1650',
        vram_used_gb: 0.85,
        vram_total_gb: 4.0,
        vram_percent: 21.2,
        utilization_percent: 14.0,
      },
      local_model: {
        is_running: true,
        service_name: 'ollama',
        latency_ms: 45.2,
        error: null,
      },
      uptime_seconds: 3600,
      timestamp: new Date().toISOString(),
    };

    render(<HardwareMetricsCard metrics={mockMetrics} isLoading={false} />);

    expect(screen.getByText('Host Hardware & Resources')).toBeInTheDocument();
    expect(screen.getByText('19%')).toBeInTheDocument(); // CPU rounded
    expect(screen.getByText(/10.5 GB \/ 16 GB \(66%\)/)).toBeInTheDocument(); // RAM
    expect(screen.getByText(/0.85 GB \/ 4 GB \(21%\)/)).toBeInTheDocument(); // VRAM
    expect(screen.getByText('NVIDIA GeForce GTX 1650')).toBeInTheDocument();
    expect(screen.getByText('14%')).toBeInTheDocument(); // GPU util
    expect(screen.getByText(/Active \(45ms\)/)).toBeInTheDocument(); // Ollama
  });

  it('renders ActivityTimeline with genuine events and filter badges', () => {
    const mockEvents: SystemActivityItem[] = [
      {
        id: 'ev-1',
        event_type: 'task_created',
        title: 'Task Created: Calculate ROI',
        description: 'Arithmetic analysis task',
        category: 'work',
        timestamp: '2026-11-20T06:15:00Z',
        metadata: {},
      },
      {
        id: 'ev-2',
        event_type: 'memory_saved',
        title: 'Memory Saved (Personal)',
        description: 'User prefers dark mode',
        category: 'memory',
        timestamp: '2026-11-20T06:14:00Z',
        metadata: {},
      },
    ];

    render(<ActivityTimeline items={mockEvents} isLoading={false} />);

    expect(screen.getByText('Unified Activity Timeline')).toBeInTheDocument();
    expect(screen.getByText('Task Created: Calculate ROI')).toBeInTheDocument();
    expect(screen.getByText('Arithmetic analysis task')).toBeInTheDocument();
    expect(screen.getByText('Memory Saved (Personal)')).toBeInTheDocument();
    expect(screen.getByText('User prefers dark mode')).toBeInTheDocument();
    expect(screen.getByText('Showing 2 of 2 Recorded')).toBeInTheDocument();
  });

  it('renders DatabaseHealthCard with engine, WAL, and integrity metrics', () => {
    const mockDbHealth = {
      engine: 'sqlite',
      status: 'connected',
      latency_ms: 3.2,
      is_sqlite: true,
      is_postgresql: false,
      journal_mode: 'WAL',
      foreign_keys_enabled: true,
      integrity_status: 'ok',
      alembic_revision: 'c0e81b379d42',
      database_size_bytes: 356352,
      database_size_mb: 0.34,
      table_counts: { users: 4, tasks: 7, memories: 2 },
      wal_file_present: true,
      last_backup: {
        filename: 'love_backup_20261120_095038.db',
        created_at: '2026-11-20T09:50:38Z',
        size_bytes: 356352,
        is_valid: true,
        total_backups: 2,
      },
      timestamp: '2026-11-20T09:50:38Z',
    };

    render(<DatabaseHealthCard dbHealth={mockDbHealth} isLoading={false} />);

    expect(screen.getByText('Database Engine & Integrity')).toBeInTheDocument();
    expect(screen.getByText('SQLITE • WAL')).toBeInTheDocument();
    expect(screen.getByText('3.2 ms')).toBeInTheDocument();
    expect(screen.getByText('0.34 MB')).toBeInTheDocument();
    expect(screen.getByText('c0e81b379d')).toBeInTheDocument();
    expect(screen.getByText('Verified OK')).toBeInTheDocument();
    expect(screen.getByText(/Total Records/)).toBeInTheDocument();
    expect(screen.getByText('Backup Database')).toBeInTheDocument();
  });
});
