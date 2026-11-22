import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { DeviceInfo } from '../../services/systemService';
import { syncService } from '../../services/syncService';
import { SyncStatus } from '../../types/sync';
import {
  CheckCircle2,
  KeyRound,
  Laptop,
  Lock,
  Shield,
  ShieldCheck,
  UserCheck,
  Wifi,
  WifiOff,
} from 'lucide-react';

interface SecurityDeviceCardProps {
  devices: DeviceInfo[];
  onOpenSettings: () => void;
}

export const SecurityDeviceCard: React.FC<SecurityDeviceCardProps> = ({
  devices,
  onOpenSettings,
}) => {
  const { user } = useAuth();
  const isElectron = typeof window !== 'undefined' && !!window.loveDesktop?.isElectron;
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);

  useEffect(() => {
    let isMounted = true;
    syncService
      .getStatus()
      .then((st) => {
        if (isMounted) setSyncStatus(st);
      })
      .catch(() => {
        // graceful offline fallback
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const isMultiDevice = syncStatus?.sync_mode === 'multi_device';

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Security & Devices</h3>
              <p className="text-[11px] text-slate-400">Hardware Vault & Cross-Device Sync</p>
            </div>
          </div>

          <button
            onClick={onOpenSettings}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 transition-all"
          >
            <span>Device Settings</span>
          </button>
        </div>

        {/* Security Posture Grid */}
        <div className="grid grid-cols-2 gap-2 mb-3.5">
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <div className="flex items-center gap-1.5 mb-1">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Credential Vault</span>
            </div>
            <span className="text-xs font-semibold text-slate-200">
              {isElectron ? 'Windows DPAPI Encrypted' : 'Session Memory Vault'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <div className="flex items-center gap-1.5 mb-1">
              {isMultiDevice ? (
                <Wifi className="w-3.5 h-3.5 text-cyan-400" />
              ) : (
                <WifiOff className="w-3.5 h-3.5 text-emerald-400" />
              )}
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Sync Architecture</span>
            </div>
            <span className="text-xs font-semibold text-slate-200">
              {isMultiDevice
                ? `Multi-Device (#${syncStatus?.current_cursor ?? 0})`
                : 'Standalone (Local SQLite)'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <div className="flex items-center gap-1.5 mb-1">
              <Shield className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Renderer Sandbox</span>
            </div>
            <span className="text-xs font-semibold text-slate-200">
              Context Isolated (No fs/Node)
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <div className="flex items-center gap-1.5 mb-1">
              <KeyRound className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Token Security</span>
            </div>
            <span className="text-xs font-semibold text-slate-200">
              Automatic 401 Rotation
            </span>
          </div>
        </div>

        {/* Authorized Devices Overview */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-slate-400 uppercase font-semibold tracking-wider px-1">
            <span>Authorized Hardware Devices</span>
            <span className="font-mono text-cyan-400">{devices.length} Registered</span>
          </div>
          <div className="space-y-1.5 max-h-28 overflow-y-auto custom-scrollbar pr-1">
            {devices.length === 0 ? (
              <div className="p-2 rounded-xl bg-background-tertiary text-center text-xs text-slate-500">
                Current workstation session
              </div>
            ) : (
              devices.slice(0, 3).map((d) => (
                <div
                  key={d.id}
                  className="p-2 rounded-xl bg-background-tertiary/40 border border-border-subtle text-xs flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <Laptop className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-200 truncate">{d.device_name}</div>
                      <div className="text-[10px] text-slate-500 capitalize">
                        {d.device_type} • v{d.client_version || '1.0'}
                      </div>
                    </div>
                  </div>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                      d.is_trusted
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : 'bg-slate-500/15 text-slate-400'
                    }`}
                  >
                    {d.is_trusted ? 'Trusted' : 'Active'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-border-subtle/60 mt-2">
        <span>Zero Plaintext Disk Exposure</span>
        <span className="text-emerald-400 font-semibold">Strict CSP Enforced</span>
      </div>
    </div>
  );
};
