import React, { useEffect, useState } from 'react';
import { useMobileAuth } from '../../context/AuthContext';
import { DeviceInfo } from '../../types/auth';
import { NotificationPreferences } from '../../types/notification';
import { SyncSettings } from '../../types/sync';
import { mobileApiClient } from '../../services/apiClient';
import { mobileAuthService } from '../../services/authService';
import { biometricService } from '../../services/biometricService';
import { mobileNotificationService } from '../../services/notificationService';
import { mobileSyncService } from '../../services/syncService';
import {
  Bell,
  Fingerprint,
  Globe,
  HardDrive,
  LogOut,
  RefreshCw,
  Shield,
  Smartphone,
  Trash2,
  User,
  Volume2,
} from 'lucide-react';

export const MobileSettingsScreen: React.FC = () => {
  const { user, logout, isBiometricSupported, isBiometricEnabled } = useMobileAuth();
  const [serverUrl, setServerUrl] = useState<string>(mobileApiClient.getBaseUrl());
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [biometricActive, setBiometricActive] = useState<boolean>(isBiometricEnabled);
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences>({
    enabled: false,
    task_approvals: true,
    task_completions: true,
    security_alerts: true,
  });
  const [syncSettings, setSyncSettings] = useState<SyncSettings>({
    sync_enabled: false,
    sync_mode: 'standalone',
    auto_sync_interval_seconds: 60,
    sync_on_change: false,
  });
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadSettingsData = async () => {
    setIsLoading(true);
    try {
      const [devList, nPrefs, sSettings] = await Promise.allSettled([
        mobileAuthService.listDevices(),
        mobileNotificationService.getPreferences(),
        mobileSyncService.getSettings(),
      ]);
      if (devList.status === 'fulfilled') setDevices(devList.value);
      if (nPrefs.status === 'fulfilled') setNotifPrefs(nPrefs.value);
      if (sSettings.status === 'fulfilled') setSyncSettings(sSettings.value);
    } catch (err) {
      console.warn('Failed to load settings data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSettingsData();
  }, []);

  const handleSaveServerUrl = async () => {
    if (!serverUrl.trim()) return;
    await mobileApiClient.setBaseUrl(serverUrl.trim());
    setStatusMsg('Server URL updated successfully.');
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleToggleBiometrics = async () => {
    if (!isBiometricSupported) return;
    if (biometricActive) {
      await biometricService.disableBiometricUnlock();
      setBiometricActive(false);
      setStatusMsg('Biometric unlock disabled.');
    } else {
      const success = await biometricService.enableBiometricUnlock();
      if (success) {
        setBiometricActive(true);
        setStatusMsg('Biometric unlock enabled.');
      } else {
        setStatusMsg('Biometric verification failed.');
      }
    }
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleToggleNotifications = async () => {
    const updated = { ...notifPrefs, enabled: !notifPrefs.enabled };
    if (updated.enabled) {
      await mobileNotificationService.requestPermission();
    }
    setNotifPrefs(updated);
    await mobileNotificationService.savePreferences(updated);
    setStatusMsg(`Push notifications ${updated.enabled ? 'enabled' : 'disabled'}.`);
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleToggleSync = async () => {
    const updated: SyncSettings = {
      ...syncSettings,
      sync_enabled: !syncSettings.sync_enabled,
      sync_mode: !syncSettings.sync_enabled ? 'multi_device' : 'standalone',
    };
    try {
      const res = await mobileSyncService.updateSettings(updated);
      setSyncSettings(res);
      setStatusMsg(`Sync mode: ${res.sync_mode}.`);
    } catch {
      setStatusMsg('Failed to update sync settings.');
    }
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleRevokeDevice = async (deviceId: string) => {
    try {
      await mobileAuthService.revokeDevice(deviceId);
      setDevices((prev) => prev.filter((d) => d.id !== deviceId));
      setStatusMsg('Device revoked successfully.');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch {
      setStatusMsg('Failed to revoke device.');
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-background">
      {/* Title */}
      <div>
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          <span>Mobile Device & Security Settings</span>
        </h2>
        <p className="text-[11px] text-slate-400">Manage credentials, biometrics, sync & authorized clients</p>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs">
          {statusMsg}
        </div>
      )}

      {/* Profile Card */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 flex items-center justify-center font-bold text-sm">
            {user?.username?.slice(0, 1).toUpperCase() || 'U'}
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-white truncate">{user?.username}</h3>
            <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
            {user?.is_owner && (
              <span className="inline-block mt-0.5 px-1.5 py-0.2 rounded text-[9px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                Primary Owner
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Backend Server URL Config */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-2">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-slate-200">Backend Server Connection</h3>
        </div>
        <p className="text-[10px] text-slate-400">
          Android Emulator: <code className="text-cyan-300">http://10.0.2.2:8000</code> • Physical Device / LAN:{' '}
          <code className="text-cyan-300">http://192.168.x.x:8000</code>
        </p>
        <div className="flex items-center gap-2 pt-1">
          <input
            type="url"
            value={serverUrl}
            onChange={(e) => setServerUrl(e.target.value)}
            className="flex-1 px-3 py-2 rounded-xl bg-background-tertiary border border-border-subtle text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
          />
          <button
            onClick={handleSaveServerUrl}
            className="px-3 py-2 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs hover:bg-cyan-400 transition"
          >
            Save
          </button>
        </div>
      </div>

      {/* Biometric Security */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Fingerprint className="w-4 h-4 text-cyan-400" />
            <div>
              <h3 className="text-xs font-bold text-slate-200">Biometric Unlock</h3>
              <p className="text-[10px] text-slate-400">Fingerprint / Face ID session gating</p>
            </div>
          </div>
          <button
            onClick={handleToggleBiometrics}
            disabled={!isBiometricSupported}
            className={`w-11 h-6 rounded-full transition-colors relative flex items-center p-0.5 ${
              biometricActive ? 'bg-cyan-500' : 'bg-slate-700'
            } ${!isBiometricSupported ? 'opacity-40 cursor-not-allowed' : ''}`}
          >
            <span
              className={`w-5 h-5 rounded-full bg-white transition-transform ${
                biometricActive ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
        {!isBiometricSupported && (
          <p className="text-[10px] text-slate-500 italic">
            Biometric authentication is not supported or not enrolled on this device.
          </p>
        )}
      </div>

      {/* Push Notifications */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-cyan-400" />
            <div>
              <h3 className="text-xs font-bold text-slate-200">Push Notifications</h3>
              <p className="text-[10px] text-slate-400">Pending approvals and task completion alerts</p>
            </div>
          </div>
          <button
            onClick={handleToggleNotifications}
            className={`w-11 h-6 rounded-full transition-colors relative flex items-center p-0.5 ${
              notifPrefs.enabled ? 'bg-cyan-500' : 'bg-slate-700'
            }`}
          >
            <span
              className={`w-5 h-5 rounded-full bg-white transition-transform ${
                notifPrefs.enabled ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
        <p className="text-[10px] text-slate-500">
          Remote FCM/APNs delivery requires server credentials (currently classified as{' '}
          <span className="text-amber-400 font-mono">NOT CONFIGURED</span>).
        </p>
      </div>

      {/* Synchronization */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4 text-cyan-400" />
            <div>
              <h3 className="text-xs font-bold text-slate-200">Cross-Device Synchronization</h3>
              <p className="text-[10px] text-slate-400">Mode: {syncSettings.sync_mode}</p>
            </div>
          </div>
          <button
            onClick={handleToggleSync}
            className={`w-11 h-6 rounded-full transition-colors relative flex items-center p-0.5 ${
              syncSettings.sync_enabled ? 'bg-cyan-500' : 'bg-slate-700'
            }`}
          >
            <span
              className={`w-5 h-5 rounded-full bg-white transition-transform ${
                syncSettings.sync_enabled ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
        <p className="text-[10px] text-slate-500">
          Standalone mode keeps all state local to this device; multi-device sync mirrors cursors across authorized devices.
        </p>
      </div>

      {/* Authorized Devices List */}
      <div className="p-4 rounded-2xl bg-background-secondary border border-border-subtle space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-slate-200">Authorized Client Devices ({devices.length})</h3>
          </div>
          <button
            onClick={loadSettingsData}
            aria-label="Refresh devices"
            className="p-1 text-slate-400 hover:text-cyan-400 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="space-y-2">
          {devices.map((d) => (
            <div
              key={d.id}
              className="p-2.5 rounded-xl bg-background-tertiary/70 border border-border-subtle flex items-center justify-between text-xs"
            >
              <div>
                <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <span>{d.device_name}</span>
                  <span className="text-[9px] px-1 py-0.2 rounded bg-background-secondary text-slate-400 font-mono uppercase">
                    {d.device_type}
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate max-w-[200px]">
                  ID: {d.device_identifier}
                </div>
              </div>
              {!d.is_revoked && (
                <button
                  onClick={() => handleRevokeDevice(d.id)}
                  aria-label="Revoke device"
                  className="p-1.5 text-slate-500 hover:text-rose-400 transition"
                  title="Revoke device access"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Logout Action */}
      <div className="pt-2">
        <button
          onClick={logout}
          className="w-full py-3 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 font-bold text-xs hover:bg-rose-500/20 flex items-center justify-center gap-2 transition"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out of LOVE Mobile</span>
        </button>
      </div>
    </div>
  );
};
