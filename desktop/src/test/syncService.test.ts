import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SyncService } from '../services/syncService';
import { apiClient } from '../services/apiClient';

describe('SyncService', () => {
  let service: SyncService;

  beforeEach(() => {
    service = new SyncService();
    vi.restoreAllMocks();
  });

  it('retrieves synchronization status', async () => {
    const mockStatus = {
      sync_enabled: true,
      sync_mode: 'multi_device' as const,
      current_cursor: 42,
      total_events: 42,
      active_devices_count: 2,
      last_synced_at: '2026-11-20T06:00:00Z',
      server_time: '2026-11-20T06:01:00Z',
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockStatus);

    const status = await service.getStatus();
    expect(status).toEqual(mockStatus);
    expect(getSpy).toHaveBeenCalledWith('/api/v1/sync/status');
  });

  it('updates sync settings between standalone and multi-device', async () => {
    const mockSettings = {
      sync_enabled: true,
      sync_mode: 'multi_device' as const,
      auto_sync_interval_seconds: 15,
      conflict_resolution: 'last_write_wins',
      updated_at: '2026-11-20T06:00:00Z',
    };

    const putSpy = vi.spyOn(apiClient, 'put').mockResolvedValue(mockSettings);

    const updated = await service.updateSettings({ sync_enabled: true, sync_mode: 'multi_device' });
    expect(updated).toEqual(mockSettings);
    expect(putSpy).toHaveBeenCalledWith('/api/v1/sync/settings', {
      sync_enabled: true,
      sync_mode: 'multi_device',
    });
  });

  it('retrieves delta changes with sinceCursor and optional echo suppression', async () => {
    const mockChanges = {
      changes: [
        {
          cursor: 10,
          event_id: 'ev-10',
          entity_type: 'conversation',
          entity_id: 'conv-10',
          action: 'created',
          origin_device_id: 'dev-other',
          payload: { title: 'Cross Device Thread' },
          created_at: '2026-11-20T06:00:00Z',
        },
      ],
      since_cursor: 9,
      latest_cursor: 10,
      has_more: false,
      count: 1,
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockChanges);

    const res = await service.getChanges(9, 50, 'dev-my-rig');
    expect(res).toEqual(mockChanges);
    expect(getSpy).toHaveBeenCalledWith(
      '/api/v1/sync/changes?since_cursor=9&limit=50&exclude_device_id=dev-my-rig'
    );
  });

  it('acknowledges processed sequence cursor and revokes authorized device', async () => {
    const mockAck = { status: 'acknowledged', cursor: 15 };
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockAck);

    const ack = await service.acknowledge(15, 'device-1');
    expect(ack.status).toBe('acknowledged');
    expect(postSpy).toHaveBeenCalledWith('/api/v1/sync/acknowledge', {
      cursor: 15,
      device_id: 'device-1',
    });

    const mockRevokedDevice = {
      id: 'dev-to-revoke',
      user_id: 'user-1',
      device_identifier: 'ident-1',
      device_name: 'Stolen Tablet',
      device_type: 'android' as const,
      is_trusted: false,
      is_revoked: true,
      revoked_at: '2026-11-20T06:05:00Z',
      created_at: '2026-11-20T05:00:00Z',
    };
    const delSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(mockRevokedDevice);

    const revoked = await service.revokeDevice('dev-to-revoke');
    expect(revoked.is_revoked).toBe(true);
    expect(delSpy).toHaveBeenCalledWith('/api/v1/devices/dev-to-revoke');
  });
});
