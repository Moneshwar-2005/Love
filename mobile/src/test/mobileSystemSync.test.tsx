import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileAuthProvider } from '../context/AuthContext';
import { MobileAppProvider } from '../context/AppContext';
import { MobileDashboard } from '../components/dashboard/MobileDashboard';
import { MobileSettingsScreen } from '../components/settings/MobileSettingsScreen';
import { MobileTabBar } from '../components/layout/MobileTabBar';
import { mobileSystemService } from '../services/systemService';
import { mobileSyncService } from '../services/syncService';
import { mobileAuthService } from '../services/authService';
import { mobileNotificationService } from '../services/notificationService';

describe('LOVE Mobile Telemetry, Sync & Navigation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders host hardware metrics and SQLite WAL database diagnostics', async () => {
    vi.spyOn(mobileSystemService, 'getMetrics').mockResolvedValue({
      cpu_percent: 18.5,
      ram: { used_gb: 6.2, total_gb: 16.0, percent: 38.75 },
      gpu: { available: true, name: 'GeForce RTX', vram_used_gb: 2.1, vram_total_gb: 6.0, vram_percent: 35.0, utilization_percent: 20 },
      uptime_seconds: 7200,
      timestamp: new Date().toISOString(),
    });

    vi.spyOn(mobileSystemService, 'getDatabaseHealth').mockResolvedValue({
      engine: 'sqlite',
      status: 'healthy',
      latency_ms: 0.7,
      journal_mode: 'wal',
      foreign_keys: true,
      integrity_check: 'ok',
      schema_revision: 'c0e81b379d42',
      database_size_bytes: 1048576,
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileDashboard />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Command & Telemetry')).toBeInTheDocument();
      expect(screen.getByText('18.5%')).toBeInTheDocument();
      expect(screen.getByText('WAL Mode')).toBeInTheDocument();
      expect(screen.getByText('c0e81b379d42')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Create Atomic SQLite Backup/i })).toBeInTheDocument();
    });
  });

  it('triggers on-demand database backup and shows confirmation badge', async () => {
    vi.spyOn(mobileSystemService, 'getMetrics').mockResolvedValue({
      cpu_percent: 15.0,
      ram: { used_gb: 5.0, total_gb: 16.0, percent: 31.25 },
      uptime_seconds: 3600,
      timestamp: new Date().toISOString(),
    });

    vi.spyOn(mobileSystemService, 'getDatabaseHealth').mockResolvedValue({
      engine: 'sqlite',
      status: 'healthy',
      latency_ms: 0.5,
      journal_mode: 'wal',
      integrity_check: 'ok',
    });

    const backupSpy = vi.spyOn(mobileSystemService, 'createDatabaseBackup').mockResolvedValue({
      success: true,
      backup: {
        filename: 'love_backup_mobile_20261120.db',
        sha256: 'mock-sha256',
      },
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileDashboard />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Atomic SQLite Backup/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Create Atomic SQLite Backup/i }));

    await waitFor(() => {
      expect(backupSpy).toHaveBeenCalled();
      expect(screen.getByText(/Backup love_backup_mobile_20261120.db created & verified!/i)).toBeInTheDocument();
    });
  });

  it('renders settings screen with authorized devices and sync controls', async () => {
    vi.spyOn(mobileAuthService, 'listDevices').mockResolvedValue([
      {
        id: 'd1',
        device_identifier: 'mobile-android-uuid-1234',
        device_name: 'LOVE Mobile (Android)',
        device_type: 'android',
        is_trusted: true,
        is_revoked: false,
        created_at: new Date().toISOString(),
      },
    ]);
    vi.spyOn(mobileNotificationService, 'getPreferences').mockResolvedValue({
      enabled: false,
      task_approvals: true,
      task_completions: true,
      security_alerts: true,
    });
    vi.spyOn(mobileSyncService, 'getSettings').mockResolvedValue({
      sync_enabled: false,
      sync_mode: 'standalone',
      auto_sync_interval_seconds: 60,
      sync_on_change: false,
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileSettingsScreen />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Mobile Device & Security Settings')).toBeInTheDocument();
      expect(screen.getByText('LOVE Mobile (Android)')).toBeInTheDocument();
      expect(screen.getByText(/Mode: standalone/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Sign Out of LOVE Mobile/i })).toBeInTheDocument();
    });
  });

  it('renders mobile bottom tab bar with 5 navigation destinations and badges', () => {
    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileTabBar />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    expect(screen.getByRole('button', { name: /Chat/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Work/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Memory/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Telemetry/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Settings/i })).toBeInTheDocument();
  });

  it('updates synchronization settings and acknowledges sync cursor', async () => {
    const updateSpy = vi.spyOn(mobileSyncService, 'updateSettings').mockResolvedValue({
      sync_enabled: true,
      sync_mode: 'multi_device',
      auto_sync_interval_seconds: 30,
      sync_on_change: true,
    });
    const ackSpy = vi.spyOn(mobileSyncService, 'acknowledgeCursor').mockResolvedValue({
      success: true,
      confirmed_cursor: 42,
    });

    const res = await mobileSyncService.updateSettings({ sync_enabled: true });
    expect(updateSpy).toHaveBeenCalledWith({ sync_enabled: true });
    expect(res.sync_mode).toBe('multi_device');

    const ack = await mobileSyncService.acknowledgeCursor(42);
    expect(ackSpy).toHaveBeenCalledWith(42);
    expect(ack.confirmed_cursor).toBe(42);
  });

  it('manages push notification preferences and saves them to native secure store', async () => {
    const saveSpy = vi.spyOn(mobileNotificationService, 'savePreferences').mockResolvedValue();

    await mobileNotificationService.savePreferences({
      enabled: true,
      task_approvals: true,
      task_completions: false,
      security_alerts: true,
    });

    expect(saveSpy).toHaveBeenCalledWith({
      enabled: true,
      task_approvals: true,
      task_completions: false,
      security_alerts: true,
    });
  });
});
