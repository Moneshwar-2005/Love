import React, { useEffect, useState } from 'react';
import { syncService } from '../../services/syncService';
import { DeviceItem, SyncSettings, SyncStatus } from '../../types/sync';
import {
  AlertCircle,
  CheckCircle2,
  Globe,
  HardDrive,
  Laptop,
  RefreshCw,
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
      await loadData();
      setSuccessMsg(
        enableMultiDevice
          ? 'Multi-Device Sync mode activated.'
          : 'Reverted to Standalone Sovereign mode.'
      );
    } catch (err: any) {
      setError(err?.message || 'Failed to update sync mode.');
    } finally {
      setUpdating(false);
    }
  };

  const handleRevokeDevice = async (deviceId: string) => {
    if (!window.confirm('Revoke this device? Its refresh tokens will be revoked immediately.')) {
      return;
    }
    try {
      setRevokingId(deviceId);
      setError(null);
      await syncService.revokeDevice(deviceId);
      await loadData();
      setSuccessMsg('Device authorization revoked.');
    } catch (err: any) {
      setError(err?.message || 'Failed to revoke device.');
    } finally {
      setRevokingId(null);
    }
  };

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center p-8 text-xs text-slate-400">
        <RefreshCw className="w-4 h-4 animate-spin mr-2 text-cyan-400" />
        <span>Loading synchronization profile...</span>
      </div>
    );
  }

  const isMultiDevice = settings?.sync_mode === 'multi_device';

  return (
    <div className="space-y-4 text-xs">
      {/* Informational Posture Banner */}
      <div className="p-3.5 rounded-2xl bg-cyan-950/20 border border-cyan-500/30 text-slate-300 space-y-1.5">
        <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs">
          <Globe className="w-4 h-4 flex-shrink-0" />
          <span>Web Client Synchronization Posture</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          This web application communicates directly with your canonical LOVE backend. Multi-device state synchronization synchronizes delta events between authorized clients without external third-party cloud brokers.
        </p>
      </div>

      {error && (
        <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Mode Selector Card */}
      <div className="p-3.5 rounded-2xl bg-background-tertiary/60 border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-semibold text-slate-200">Synchronization Architecture Mode</h4>
            <p className="text-[11px] text-slate-400">
              Default is Standalone Sovereign (zero background network chatter)
            </p>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
              isMultiDevice
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }`}
          >
            {settings?.sync_mode || 'standalone'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleToggleMode(false)}
            disabled={updating || !isMultiDevice}
            className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
              !isMultiDevice
                ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                : 'bg-background-secondary border-border-subtle text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center gap-1.5 font-semibold text-xs mb-1">
              <WifiOff className="w-3.5 h-3.5" />
              <span>Standalone Mode</span>
            </div>
            <p className="text-[10px] opacity-80">Local only, no client sync overhead</p>
          </button>

          <button
            type="button"
            onClick={() => handleToggleMode(true)}
            disabled={updating || isMultiDevice}
            className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
              isMultiDevice
                ? 'bg-indigo-950/20 border-indigo-500/40 text-indigo-300'
                : 'bg-background-secondary border-border-subtle text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center gap-1.5 font-semibold text-xs mb-1">
              <Wifi className="w-3.5 h-3.5" />
              <span>Multi-Device Sync</span>
            </div>
            <p className="text-[10px] opacity-80">Delta sync stream for companion clients</p>
          </button>
        </div>
      </div>

      {/* Sync Stream Telemetry */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
          <span className="text-[10px] text-slate-400 block mb-0.5">Stream Cursor</span>
          <span className="font-mono font-bold text-cyan-400 text-xs">
            #{status?.current_cursor ?? 0}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
          <span className="text-[10px] text-slate-400 block mb-0.5">Recorded Events</span>
          <span className="font-mono font-bold text-indigo-300 text-xs">
            {status?.total_events ?? 0}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle text-center">
          <span className="text-[10px] text-slate-400 block mb-0.5">Active Devices</span>
          <span className="font-mono font-bold text-emerald-400 text-xs">
            {status?.active_devices_count ?? devices.length}
          </span>
        </div>
      </div>

      {/* Authorized Hardware Devices */}
      <div className="space-y-2">
        <h4 className="font-semibold text-slate-300">Authorized Hardware Devices ({devices.length})</h4>
        <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar pr-1">
          {devices.length === 0 ? (
            <p className="text-slate-500 text-xs">No devices registered.</p>
          ) : (
            devices.map((dev) => (
              <div
                key={dev.id}
                className={`p-2.5 rounded-xl border flex items-center justify-between text-xs ${
                  dev.is_revoked
                    ? 'bg-rose-950/10 border-rose-500/20 opacity-60'
                    : 'bg-background-tertiary/50 border-border-subtle'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  {dev.device_type === 'android' || dev.device_type === 'ios' ? (
                    <Smartphone className="w-4 h-4 text-purple-400 flex-shrink-0" />
                  ) : dev.device_type === 'web' ? (
                    <Globe className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  ) : (
                    <Laptop className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  )}
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-200 truncate flex items-center gap-1.5">
                      <span>{dev.device_name}</span>
                      {dev.is_revoked && (
                        <span className="text-[9px] font-bold text-rose-400 uppercase bg-rose-500/20 px-1 py-0.2 rounded">
                          Revoked
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono truncate">
                      {dev.device_identifier}
                    </div>
                  </div>
                </div>

                {!dev.is_revoked && (
                  <button
                    type="button"
                    onClick={() => handleRevokeDevice(dev.id)}
                    disabled={revokingId === dev.id}
                    className="p-1 hover:text-rose-400 text-slate-400 rounded transition"
                    title="Revoke Device"
                    aria-label={`Revoke device ${dev.device_name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
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
