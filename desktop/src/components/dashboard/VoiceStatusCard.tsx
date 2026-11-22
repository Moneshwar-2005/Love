import React from 'react';
import { VoiceStatus } from '../../types/voice';
import { AlertCircle, ArrowUpRight, CheckCircle2, Mic, MicOff, Radio, Volume2, XCircle } from 'lucide-react';

interface VoiceStatusCardProps {
  status: VoiceStatus | null;
  onNavigateToVoice: () => void;
}

export const VoiceStatusCard: React.FC<VoiceStatusCardProps> = ({
  status,
  onNavigateToVoice,
}) => {
  const stt = status?.stt;
  const tts = status?.tts;
  const wakeWord = status?.wake_word;

  return (
    <div className="p-5 rounded-2xl bg-background-secondary/90 border border-border-subtle shadow-xl backdrop-blur-md flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Mic className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Voice Engine & Speech</h3>
              <p className="text-[11px] text-slate-400">Speech-to-Text & Neural Synthesis</p>
            </div>
          </div>

          <button
            onClick={onNavigateToVoice}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 transition-all group"
          >
            <span>Open Voice</span>
            <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>

        {/* Wake-Word Honest Notice */}
        {!wakeWord?.model_available && (
          <div className="mb-3.5 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-[11px] text-amber-200 leading-snug">
              <strong>"Hey LOVE" wake-word disabled:</strong> Custom model <code className="text-[10px] text-amber-300">hey_love.onnx</code> is not present locally. Wake-word detection requires training.
            </div>
          </div>
        )}

        {/* Provider Breakdown */}
        <div className="space-y-2 mb-3.5">
          {/* STT Status */}
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <Radio className="w-3.5 h-3.5 text-cyan-400" />
              <div>
                <span className="font-semibold text-slate-200">Speech-to-Text (STT)</span>
                <div className="text-[10px] text-slate-400">
                  Provider: <strong className="text-slate-300">{stt?.active_provider || 'faster_whisper'}</strong>
                </div>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                stt?.is_available
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : 'bg-rose-500/15 text-rose-300'
              }`}
            >
              {stt?.is_available ? 'Available' : 'Unavailable (Mock STT)'}
            </span>
          </div>

          {/* TTS Status */}
          <div className="p-2.5 rounded-xl bg-background-tertiary/60 border border-border-subtle flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <Volume2 className="w-3.5 h-3.5 text-purple-400" />
              <div>
                <span className="font-semibold text-slate-200">Text-to-Speech (TTS)</span>
                <div className="text-[10px] text-slate-400">
                  Provider: <strong className="text-slate-300">{tts?.active_provider || 'mock'}</strong>
                </div>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                tts?.active_provider === 'mock'
                  ? 'bg-amber-500/15 text-amber-300'
                  : tts?.is_available
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : 'bg-rose-500/15 text-rose-300'
              }`}
            >
              {tts?.active_provider === 'mock' ? 'Mock (Simulated Audio)' : tts?.is_available ? 'Available' : 'Unavailable'}
            </span>
          </div>
        </div>

        {/* Security & Audio Privacy Notice */}
        <div className="grid grid-cols-2 gap-2 p-2 rounded-xl bg-background-tertiary/40 border border-border-subtle/70 text-[10px] text-slate-400">
          <div>
            <span className="text-slate-500 block mb-0.5">Audio Retention</span>
            <span className="font-medium text-slate-300">Ephemerally Processed</span>
          </div>
          <div>
            <span className="text-slate-500 block mb-0.5">Microphone Policy</span>
            <span className="font-medium text-slate-300">Push-to-Talk Explicit</span>
          </div>
        </div>
      </div>

      <div className="pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-border-subtle/60 mt-2">
        <span>Engine: <strong className="text-slate-300">{status?.is_enabled ? 'Active' : 'Disabled'}</strong></span>
        <span className="text-amber-400 font-semibold">Honest Capability Reporting</span>
      </div>
    </div>
  );
};
