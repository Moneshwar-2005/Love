import React, { useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { SyncSettingsSection } from './SyncSettingsSection';
import { CheckCircle2, RefreshCw, Server, Sliders, Wifi, X } from 'lucide-react';

interface SettingsModalProps {
  onClose: () => void;
  initialTab?: 'connection' | 'sync';
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ onClose, initialTab = 'connection' }) => {
  const { user } = useAuth();
  const { refreshStatus } = useApp();
  const [activeTab, setActiveTab] = useState<'connection' | 'sync'>(initialTab);
  const [backendUrl, setBackendUrl] = useState<string>(apiClient.getBaseUrl());
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const startTime = performance.now();
      const res = await fetch(`${backendUrl.replace(/\/+$/, '')}/health`);
      const latency = Math.round(performance.now() - startTime);

      if (res.ok) {
        setTestResult({
          ok: true,
          message: `Connected successfully (${latency}ms round-trip)`,
        });
      } else {
        setTestResult({
          ok: false,
          message: `Server returned status ${res.status}`,
        });
      }
    } catch (err: any) {
      setTestResult({
        ok: false,
        message: `Connection failed: ${err.message || 'Cannot reach host'}`,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    apiClient.setBaseUrl(backendUrl);
    refreshStatus();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-background-secondary border border-border-subtle rounded-3xl shadow-2xl p-5 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-border-subtle mb-3">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-slate-100">Preferences & System Settings</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-background-tertiary text-slate-400 hover:text-white transition-colors"
            aria-label="Close settings"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mb-4 bg-background-tertiary/60 p-1 rounded-xl border border-border-subtle">
          <button
            type="button"
            onClick={() => setActiveTab('connection')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'connection'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            <span>Connection & Host</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sync')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'sync'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Wifi className="w-3.5 h-3.5" />
            <span>Cross-Device Sync</span>
          </button>
        </div>

        {/* Tab Contents */}
        <div className="flex-1 overflow-y-auto custom-scrollbar pr-1">
          {activeTab === 'connection' ? (
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  LOVE Backend API URL
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={backendUrl}
                    onChange={(e) => setBackendUrl(e.target.value)}
                    placeholder="http://127.0.0.1:8000"
                    className="flex-1 p-2.5 rounded-xl bg-background-tertiary border border-border-subtle text-slate-100 font-mono focus:border-cyan-500 outline-none"
                  />
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={isTesting}
                    className="px-3 py-2.5 rounded-xl bg-background-tertiary border border-border-subtle hover:bg-background-secondary text-slate-200 font-semibold transition flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
                    <span>Test</span>
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Configures the base URL for REST requests and SSE streaming.
                </p>
              </div>

              {testResult && (
                <div
                  className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
                    testResult.ok
                      ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                      : 'bg-rose-950/20 border-rose-500/40 text-rose-300'
                  }`}
                >
                  {testResult.ok ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  ) : (
                    <X className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              )}

              <div className="p-3.5 rounded-2xl bg-background-tertiary/40 border border-border-subtle space-y-2">
                <span className="font-semibold text-slate-200">Active Profile</span>
                <div className="text-slate-400 space-y-1">
                  <div>Owner: <span className="text-slate-200 font-mono">{user?.username}</span></div>
                  <div>Email: <span className="text-slate-200 font-mono">{user?.email}</span></div>
                  <div>Role: <span className="text-cyan-400 font-mono">{user?.is_owner ? 'Primary Owner' : 'Authorized User'}</span></div>
                </div>
              </div>
            </div>
          ) : (
            <SyncSettingsSection />
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-border-subtle flex items-center justify-end gap-2 mt-3">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:bg-background-tertiary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-600/25 transition-all"
          >
            Apply Settings
          </button>
        </div>
      </div>
    </div>
  );
};
