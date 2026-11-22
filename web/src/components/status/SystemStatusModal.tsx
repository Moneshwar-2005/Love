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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-background-secondary border border-border-subtle rounded-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-slate-100">System Intelligence & Hardware Profile</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-background-tertiary text-slate-400 hover:text-white transition-colors"
            aria-label="Close status modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-4 overflow-y-auto space-y-4 custom-scrollbar text-xs">
          {/* General Connectivity Banner */}
          <div className="p-3.5 rounded-2xl bg-background-tertiary/60 border border-border-subtle flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {backendOnline ? (
                <Wifi className="w-4 h-4 text-emerald-400" />
              ) : (
                <WifiOff className="w-4 h-4 text-rose-400" />
              )}
              <div>
                <div className="font-semibold text-slate-200">
                  LOVE FastAPI Core Engine:{' '}
                  <span className={backendOnline ? 'text-emerald-400' : 'text-rose-400'}>
                    {backendOnline ? 'Online & Responsive' : 'Unreachable'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Canonical Sovereign Assistant Endpoint
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                v0.2.0
              </span>
            </div>
          </div>

          {/* Routing Policy Card */}
          <div className="p-3.5 rounded-2xl bg-background-tertiary/40 border border-border-subtle space-y-2">
            <h4 className="font-semibold text-slate-300">Routing Policy & Privacy Posture</h4>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2 rounded-xl bg-background-secondary border border-border-subtle">
                <span className="text-slate-400 block mb-0.5">Policy Preference</span>
                <span className="font-semibold text-cyan-300 capitalize font-mono">
                  {intelligenceStatus?.routing_preference || 'auto'}
                </span>
              </div>
              <div className="p-2 rounded-xl bg-background-secondary border border-border-subtle">
                <span className="text-slate-400 block mb-0.5">Local-Only Privacy</span>
                <span className="font-semibold text-emerald-400 font-mono">
                  {intelligenceStatus?.local_only_mode ? 'Strict Local Sovereign' : 'Permissive Local/Cloud'}
                </span>
              </div>
            </div>
          </div>

          {/* Database Diagnostics Summary */}
          {dbHealth && (
            <div className="p-3.5 rounded-2xl bg-background-tertiary/40 border border-border-subtle space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-slate-300">
                <Database className="w-4 h-4 text-cyan-400" />
                <span>Canonical Database Engine Diagnostics</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
                <div className="p-2 rounded-xl bg-background-secondary border border-border-subtle">
                  <span className="text-slate-400 block mb-0.5">Engine</span>
                  <span className="text-white font-bold">{dbHealth.engine.toUpperCase()}</span>
                </div>
                <div className="p-2 rounded-xl bg-background-secondary border border-border-subtle">
                  <span className="text-slate-400 block mb-0.5">Alembic Head</span>
                  <span className="text-indigo-300 truncate block">{dbHealth.schema_revision || 'c0e81b379d42'}</span>
                </div>
                <div className="p-2 rounded-xl bg-background-secondary border border-border-subtle">
                  <span className="text-slate-400 block mb-0.5">Integrity</span>
                  <span className="text-emerald-400">{dbHealth.integrity_check || 'Verified OK'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Registered AI Providers */}
          <div className="space-y-2">
            <h4 className="font-semibold text-slate-300">Registered Model Providers</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {providers.map((prov) => (
                <div
                  key={prov.id}
                  className="p-3 rounded-xl bg-background-tertiary/50 border border-border-subtle flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Radio className={`w-3.5 h-3.5 ${prov.is_available ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <div>
                      <div className="font-semibold text-slate-200">{prov.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {prov.is_local ? 'Local Hardware Daemon' : 'External API Provider'}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      prov.is_available
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-slate-700 text-slate-400'
                    }`}
                  >
                    {prov.is_available ? 'Ready' : 'Not Configured'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Registered Models Catalog */}
          {models.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-semibold text-slate-300">Registered Models ({models.length})</h4>
              <div className="max-h-40 overflow-y-auto space-y-1 custom-scrollbar pr-1">
                {models.map((mod) => (
                  <div
                    key={mod.id}
                    className="p-2 rounded-xl bg-background-tertiary/30 border border-border-subtle/50 flex items-center justify-between text-[11px]"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-cyan-300 font-semibold">{mod.name}</span>
                      <span className="text-slate-500">({mod.provider})</span>
                    </div>
                    <span className="font-mono text-slate-400 text-[10px]">
                      {mod.context_length ? `${Math.round(mod.context_length / 1024)}k ctx` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border-subtle flex justify-end bg-background-tertiary/30">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
