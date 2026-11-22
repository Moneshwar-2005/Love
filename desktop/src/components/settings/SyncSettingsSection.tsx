import React, { useEffect, useState } from 'react';
import { syncService } from '../../services/syncService';
import { DeviceItem, SyncSettings, SyncStatus } from '../../types/sync';
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  Globe,
  HardDrive,
  Laptop,
  Layers,
  RefreshCw,
  ShieldAlert,
  Smartphone,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react';

export const SyncSettingsSection: React.FC = () => {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [settings, setSettings] = useState<SyncSettings | null>(null);
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [updating, setUpdating] = useState<boolean>(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [st, sett, devList] = await Promise.all([
        syncService.getStatus(),
        syncService.getSettings(),
        syncService.listDevices(),
      ]);
      setStatus(st);
      setSettings(sett);
      setDevices(devList);
    } catch (err: any) {
      setError(err?.message || 'Failed to load synchronization settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleMode = async (enableMultiDevice: boolean) => {
    try {
      setUpdating(true);
      setError(null);
      setSuccessMsg(null);
      const updated = await syncService.updateSettings({
        sync_enabled: enableMultiDevice,
        sync_mode: enableMultiDevice ? 'multi_device' : 'standalone',
      });
      setSettings(updated);
      setSuccessMsg(
        enableMultiDevice
          ? 'Switched to Multi-Device Mode. Authorized devices will now synchronize state changes.'
          : 'Switched to Standalone Mode. Assistant operates locally with zero cloud network calls.'
      );
      // Refresh status
      const st = await syncService.getStatus();
      setStatus(st);
    } catch (err: any) {
      setError(err?.message || 'Failed to update operational mode.');
    } finally {
      setUpdating(false);
    }
  };

  const handleRevokeDevice = async (device: DeviceItem) => {
    if (device.is_revoked) return;
    const confirm = window.confirm(
      `Revoke access for "${device.device_name}" (${device.device_type})?\n\nThis will immediately terminate all active sessions and block the device from connecting or synchronizing.`
    );
    if (!confirm) return;

    try {
      setRevokingId(device.id);
      setError(null);
      await syncService.revokeDevice(device.id);
      setSuccessMsg(`Successfully revoked access for ${device.device_name}.`);
      // Reload devices list & status
      const [devList, st] = await Promise.all([
        syncService.listDevices(),
        syncService.getStatus(),
      ]);
      setDevices(devList);
      setStatus(st);
    } catch (err: any) {
      setError(err?.message || 'Failed to revoke device authorization.');
    } finally {
      setRevokingId(null);
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'windows':
      case 'macos':
      case 'linux':
        return <Laptop className="w-4 h-4 text-cyan-400" />;
      case 'android':
      case 'ios':
        return <Smartphone className="w-4 h-4 text-emerald-400" />;
      case 'web':
        return <Globe className="w-4 h-4 text-indigo-400" />;
      default:
        return <Cpu className="w-4 h-4 text-slate-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-slate-400 text-xs gap-2">
        <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
        <span>Loading synchronization status...</span>
      </div>
    );
  }

  const isMultiDevice = settings?.sync_mode === 'multi_device';

  return (
    <div className="space-y-4 text-xs">
      {/* Alert Messages */}
      {error && (
        <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Operational Mode Card */}
      <div className="p-4 rounded-xl bg-background-tertiary/70 border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isMultiDevice ? (
              <Wifi className="w-4 h-4 text-cyan-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-emerald-400" />
            )}
            <span className="font-bold text-slate-100 text-sm">Operational Architecture Mode</span>
          </div>

          <div className="flex items-center gap-2 bg-background-secondary p-1 rounded-xl border border-border-subtle">
            <button
              type="button"
              onClick={() => handleToggleMode(false)}
              disabled={updating || !isMultiDevice}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                !isMultiDevice
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Standalone
            </button>
            <button
              type="button"
              onClick={() => handleToggleMode(true)}
              disabled={updating || isMultiDevice}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                isMultiDevice
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Multi-Device
            </button>
          </div>
        </div>

        <p className="text-slate-400 leading-relaxed text-[11px]">
          {isMultiDevice ? (
            <>
              <strong className="text-cyan-300">Multi-Device Mode Active:</strong> State changes
              (conversations, approved memories, tasks, preferences) are sequenced via a monotonic
              cursor and synchronized across authorized companion clients.
            </>
          ) : (
            <>
              <strong className="text-emerald-300">Standalone Mode Active:</strong> LOVE operates
              exclusively on this workstation using local SQLite storage. All cloud sync requests are
              disabled, preserving complete network privacy and zero external dependency.
            </>
          )}
        </p>

        {/* Architectural Posture Notice */}
        <div className="p-2.5 rounded-lg bg-blue-500/5 border border-blue-500/20 text-slate-300 text-[11px] leading-relaxed flex items-start gap-2">
          <Layers className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-blue-300 block">Workstation Architectural Posture:</span>
            This desktop client connects directly to the canonical local backend. Background delta-sync workers and push synchronization are implemented for secondary/companion clients (such as companion mobile apps). The desktop workstation remains the primary canonical host.
          </div>
        </div>

        {/* Sync Telemetry Grid */}
        <div className="grid grid-cols-4 gap-2 pt-1 border-t border-border-subtle/50">
          <div className="p-2 rounded-lg bg-background-secondary/80 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block uppercase font-medium">Sequence Cursor</span>
            <span className="text-xs font-mono font-bold text-cyan-400">
              #{status?.current_cursor ?? 0}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-background-secondary/80 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block uppercase font-medium">Total Events</span>
            <span className="text-xs font-mono font-bold text-slate-200">
              {status?.total_events ?? 0}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-background-secondary/80 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block uppercase font-medium">Active Devices</span>
            <span className="text-xs font-mono font-bold text-emerald-400">
              {status?.active_devices_count ?? 1}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-background-secondary/80 border border-border-subtle">
            <span className="text-[10px] text-slate-400 block uppercase font-medium">Conflict Policy</span>
            <span className="text-xs font-mono font-bold text-purple-400">
              LWW
            </span>
          </div>
        </div>
      </div>

      {/* Authorized Devices Section */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5">
            <HardDrive className="w-3.5 h-3.5 text-blue-400" />
            <span className="font-bold text-slate-200 text-xs">Authorized Client Installations</span>
          </div>
          <button
            onClick={loadData}
            type="button"
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar pr-1">
          {devices.length === 0 ? (
            <div className="p-3 text-center text-slate-500 rounded-xl bg-background-tertiary">
              No registered devices found.
            </div>
          ) : (
            devices.map((device) => (
              <div
                key={device.id}
                className={`p-2.5 rounded-xl border flex items-center justify-between gap-3 transition-colors ${
                  device.is_revoked
                    ? 'bg-rose-500/5 border-rose-500/20 opacity-70'
                    : 'bg-background-tertiary/60 border-border-subtle'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 rounded-lg bg-background-secondary shrink-0">
                    {getDeviceIcon(device.device_type)}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200 truncate">{device.device_name}</span>
                      {device.is_revoked ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          REVOKED
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          AUTHORIZED
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      <span className="uppercase">{device.device_type}</span>
                      <span>•</span>
                      <span>v{device.client_version || '0.2.0'}</span>
                      {device.last_seen_at && (
                        <>
                          <span>•</span>
                          <span>Seen {new Date(device.last_seen_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {!device.is_revoked && (
                  <button
                    type="button"
                    onClick={() => handleRevokeDevice(device)}
                    disabled={revokingId === device.id}
                    title="Immediately terminate sessions and block device"
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-all shrink-0 disabled:opacity-50"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>{revokingId === device.id ? 'Revoking...' : 'Revoke'}</span>
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
