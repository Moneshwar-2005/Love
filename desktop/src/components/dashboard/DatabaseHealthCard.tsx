import React, { useState } from 'react';
import { DatabaseHealthInfo } from '../../types/system';
import { systemService } from '../../services/systemService';
import {
  CheckCircle2,
  Database,
  HardDrive,
  RefreshCw,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface DatabaseHealthCardProps {
  dbHealth: DatabaseHealthInfo | null;
  isLoading: boolean;
  onRefresh?: () => void;
}

export const DatabaseHealthCard: React.FC<DatabaseHealthCardProps> = ({
  dbHealth,
  isLoading,
  onRefresh,
}) => {
  const [isBackingUp, setIsBackingUp] = useState<boolean>(false);
  const [backupNotice, setBackupNotice] = useState<string | null>(null);

  const handleBackupNow = async () => {
    try {
      setIsBackingUp(true);
      setBackupNotice(null);
      const res = await systemService.createDatabaseBackup();
      if (res.success) {
        setBackupNotice(`Backup ${res.backup.filename} created & verified.`);
        if (onRefresh) {
          onRefresh();
        }
      }
    } catch (err: any) {
      setBackupNotice(`Backup error: ${err.message || 'Failed'}`);
    } finally {
      setIsBackingUp(false);
    }
  };

  const totalRows = dbHealth
    ? Object.values(dbHealth.table_counts || {}).reduce((acc, c) => acc + c, 0)
    : 0;

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Database Engine & Integrity</h3>
              <p className="text-[11px] text-slate-400">Hardened SQLite Architecture & Automated Backups</p>
            </div>
          </div>

          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            {dbHealth?.engine ? dbHealth.engine.toUpperCase() : 'SQLITE'} {dbHealth?.journal_mode ? `• ${dbHealth.journal_mode}` : ''}
          </span>
        </div>

        {/* Status Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          {/* Engine & Latency */}
          <div className="p-3 rounded-xl bg-background-tertiary/70 border border-border-subtle/60 flex flex-col justify-between">
            <span className="text-[10px] text-slate-400 font-medium">Connectivity</span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-bold font-mono text-emerald-400">
                {dbHealth ? `${dbHealth.latency_ms} ms` : 'Checking...'}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 mt-1">Zero Latency Local</span>
          </div>

          {/* Database Size */}
          <div className="p-3 rounded-xl bg-background-tertiary/70 border border-border-subtle/60 flex flex-col justify-between">
            <span className="text-[10px] text-slate-400 font-medium">Database Size</span>
            <span className="text-xs font-bold font-mono text-slate-200 mt-1">
              {dbHealth ? `${dbHealth.database_size_mb} MB` : '...'}
            </span>
            <span className="text-[10px] text-slate-500 mt-1">
              {dbHealth?.wal_file_present ? 'WAL Sidecar Active' : 'Self-Contained'}
            </span>
          </div>

          {/* Alembic Revision */}
          <div className="p-3 rounded-xl bg-background-tertiary/70 border border-border-subtle/60 flex flex-col justify-between">
            <span className="text-[10px] text-slate-400 font-medium">Alembic Head</span>
            <span className="text-xs font-bold font-mono text-indigo-300 mt-1 truncate">
              {dbHealth?.alembic_revision ? dbHealth.alembic_revision.slice(0, 10) : 'None'}
            </span>
            <span className="text-[10px] text-slate-500 mt-1">Linear Migrations</span>
          </div>

          {/* Integrity Status */}
          <div className="p-3 rounded-xl bg-background-tertiary/70 border border-border-subtle/60 flex flex-col justify-between">
            <span className="text-[10px] text-slate-400 font-medium">Integrity Check</span>
            <div className="flex items-center gap-1.5 mt-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-bold text-emerald-400">
                {dbHealth?.integrity_status === 'ok' ? 'Verified OK' : 'Pending'}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 mt-1">FKs Enforced</span>
          </div>
        </div>

        {/* Records & Backup Snapshot Summary */}
        <div className="p-3 rounded-xl bg-background-tertiary/40 border border-border-subtle/40 mb-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-cyan-400 flex-shrink-0" />
            <span className="text-slate-300">
              <strong className="text-white font-mono">{Object.keys(dbHealth?.table_counts || {}).length}</strong> Tables •{' '}
              <strong className="text-white font-mono">{totalRows}</strong> Total Records
            </span>
          </div>

          <div className="text-[11px] text-slate-400">
            Last Backup:{' '}
            {dbHealth?.last_backup ? (
              <span className="text-slate-200 font-mono">
                {dbHealth.last_backup.filename.replace('love_backup_', '').replace('.db', '')} ({Math.round(dbHealth.last_backup.size_bytes / 1024)} KB)
              </span>
            ) : (
              <span className="text-amber-400">No backups yet</span>
            )}
          </div>
        </div>

        {/* Backup Feedback Notice */}
        {backupNotice && (
          <div className="mb-3 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{backupNotice}</span>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-border-subtle/40 text-xs">
        <span className="text-[11px] text-slate-500 flex items-center gap-1">
          <Zap className="w-3 h-3 text-cyan-400" />
          WAL Mode & Busy Timeout 10s
        </span>

        <button
          onClick={handleBackupNow}
          disabled={isBackingUp || isLoading}
          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-medium text-[11px] transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isBackingUp ? 'animate-spin' : ''}`} />
          <span>{isBackingUp ? 'Creating Backup...' : 'Backup Database'}</span>
        </button>
      </div>
    </div>
  );
};
