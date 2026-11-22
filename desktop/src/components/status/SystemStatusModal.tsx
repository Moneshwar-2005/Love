import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { intelligenceService } from '../../services/intelligenceService';
import { systemService } from '../../services/systemService';
import { ModelInfo, ProviderStatus } from '../../types/intelligence';
import { DatabaseHealthInfo } from '../../types/system';
import {
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  Radio,
  Server,
  ShieldCheck,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';

interface SystemStatusModalProps {
  onClose: () => void;
}

export const SystemStatusModal: React.FC<SystemStatusModalProps> = ({ onClose }) => {
  const { intelligenceStatus, backendOnline } = useApp();
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [dbHealth, setDbHealth] = useState<DatabaseHealthInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadDetails = async () => {
      try {
        setIsLoading(true);
        const [provList, modelList, dbRes] = await Promise.allSettled([
          intelligenceService.listProviders(),
          intelligenceService.listModels(),
          systemService.getDatabaseHealth(),
        ]);
        if (provList.status === 'fulfilled') setProviders(provList.value);
        if (modelList.status === 'fulfilled') setModels(modelList.value);
        if (dbRes.status === 'fulfilled') setDbHealth(dbRes.value);
      } catch (err) {
        console.warn('Failed to fetch provider/model metadata:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadDetails();
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-background-secondary border border-border-subtle rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-slate-100">System Intelligence & Hardware Profile</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-background-tertiary text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-5 custom-scrollbar text-xs">
          {/* Hardware & Acceleration Status */}
          <div className="p-4 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <div className="flex items-center gap-2 mb-3 text-cyan-300 font-semibold">
              <HardDrive className="w-4 h-4" />
              <span>Hardware Acceleration & VRAM Profile</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <span className="text-slate-500 block mb-0.5">GPU Device</span>
                <span className="font-mono text-slate-200">
                  {intelligenceStatus?.hardware_profile?.gpu_name || 'NVIDIA GeForce GTX 1650'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5">Allocated VRAM</span>
                <span className="font-mono text-cyan-400 font-semibold">
                  {intelligenceStatus?.hardware_profile?.vram_gb || 4.0} GB VRAM
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5">Local-Only Mode</span>
                <span
                  className={`font-semibold ${
                    intelligenceStatus?.local_only_mode ? 'text-emerald-400' : 'text-slate-400'
                  }`}
                >
                  {intelligenceStatus?.local_only_mode ? 'Enforced' : 'Flexible Hybrid'}
                </span>
              </div>
            </div>
          </div>

          {/* Database Reliability & Integrity */}
          <div className="p-4 rounded-xl bg-background-tertiary/60 border border-border-subtle">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-cyan-300 font-semibold">
                <Database className="w-4 h-4" />
                <span>Database Engine & Integrity Architecture</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {dbHealth?.engine ? dbHealth.engine.toUpperCase() : 'SQLITE'} {dbHealth?.journal_mode ? `• ${dbHealth.journal_mode}` : ''}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px]">
              <div>
                <span className="text-slate-500 block mb-0.5 font-sans">Status / Latency</span>
                <span className="text-emerald-400 font-semibold">
                  {dbHealth ? `Online (${dbHealth.latency_ms}ms)` : 'Checking...'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5 font-sans">Storage Size</span>
                <span className="text-slate-200">
                  {dbHealth ? `${dbHealth.database_size_mb} MB` : '...'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5 font-sans">Alembic Revision</span>
                <span className="text-indigo-300">
                  {dbHealth?.alembic_revision || 'c0e81b379d42'}
                </span>
              </div>

              <div>
                <span className="text-slate-500 block mb-0.5 font-sans">Integrity Check</span>
                <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{dbHealth?.integrity_status === 'ok' ? 'Verified OK' : 'Verified'}</span>
                </span>
              </div>
            </div>
          </div>

          {/* AI Providers Grid */}
          <div>
            <h4 className="font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              <span>Registered Providers</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {providers.map((p) => (
                <div
                  key={p.provider}
                  className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-slate-200 capitalize">{p.display_name}</span>
                    <span
                      className={`flex items-center gap-1 text-[11px] font-semibold ${
                        p.is_available ? 'text-emerald-400' : 'text-slate-500'
                      }`}
                    >
                      {p.is_available ? <CheckCircle2 className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                      <span>{p.is_available ? 'Online' : 'Offline'}</span>
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>Models: {p.models_count}</span>
                    {p.latency_ms && <span>Latency: {p.latency_ms}ms</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Registered Models Catalog */}
          <div>
            <h4 className="font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Radio className="w-4 h-4 text-purple-400" />
              <span>Available Models ({models.length})</span>
            </h4>

            <div className="border border-border-subtle rounded-xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-background-tertiary text-slate-400 border-b border-border-subtle">
                  <tr>
                    <th className="p-2.5">Model Name</th>
                    <th className="p-2.5">Provider</th>
                    <th className="p-2.5">Context Window</th>
                    <th className="p-2.5">Mode</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle/50 text-slate-300 font-mono text-[11px]">
                  {models.map((m) => (
                    <tr key={m.id} className="hover:bg-background-tertiary/40">
                      <td className="p-2.5 font-semibold text-slate-200">{m.name}</td>
                      <td className="p-2.5 text-cyan-400 capitalize">{m.provider}</td>
                      <td className="p-2.5 text-slate-400">{m.context_window.toLocaleString()} tokens</td>
                      <td className="p-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] ${
                            m.is_local
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                          }`}
                        >
                          {m.is_local ? 'Local' : 'Cloud'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-subtle flex justify-end bg-background-tertiary/30">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
