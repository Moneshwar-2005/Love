import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { voiceService } from '../../services/voiceService';
import { VoiceChatResponse, VoiceStatus } from '../../types/voice';
import { AudioRecorder } from './AudioRecorder';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Info,
  Mic,
  Volume2,
  VolumeX,
} from 'lucide-react';

export const VoiceWorkspace: React.FC = () => {
  const { setAssistantState } = useApp();
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [latestTurn, setLatestTurn] = useState<VoiceChatResponse | null>(null);
  const [turnHistory, setTurnHistory] = useState<VoiceChatResponse[]>([]);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const fetchStatus = async () => {
    try {
      const status = await voiceService.getStatus();
      setVoiceStatus(status);
    } catch (err) {
      console.warn('Failed to fetch voice status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleAudioReady = async (audioBlob: Blob) => {
    try {
      setIsProcessing(true);
      setAssistantState('thinking');

      const turn = await voiceService.sendVoiceTurn(audioBlob);
      setLatestTurn(turn);
      setTurnHistory((prev) => [turn, ...prev]);

      if (turn.audio_base64) {
        setIsPlayingAudio(true);
        setAssistantState('speaking');
        const audioSrc = `data:audio/${turn.audio_format || 'wav'};base64,${turn.audio_base64}`;
        if (audioPlayerRef.current) {
          audioPlayerRef.current.src = audioSrc;
          audioPlayerRef.current.play().catch((err) => {
            console.warn('Audio auto-play prevented by browser policy:', err);
            setIsPlayingAudio(false);
            setAssistantState('idle');
          });
        }
      } else {
        setAssistantState('idle');
      }
    } catch (err: any) {
      console.error('Voice processing error:', err);
      alert(`Voice processing failed: ${err.message || 'Error occurred'}`);
      setAssistantState('idle');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto p-3 sm:p-6 custom-scrollbar">
      {/* Hidden Audio Player for Speech Playback */}
      <audio
        ref={audioPlayerRef}
        onEnded={() => {
          setIsPlayingAudio(false);
          setAssistantState('idle');
        }}
        onError={() => {
          setIsPlayingAudio(false);
          setAssistantState('idle');
        }}
        className="hidden"
      />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Mic className="w-5 h-5 text-purple-400" />
            <h1 className="text-lg sm:text-xl font-bold text-slate-100">Voice Engine & Speech Interaction</h1>
          </div>
          <p className="text-xs text-slate-400">
            Push-to-talk speech recognition, neural voice synthesis, and conversation turns.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-xl text-xs font-mono font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20">
            {voiceStatus?.personality.preferred_accent || 'British RP'}
          </span>
        </div>
      </div>

      {/* Acoustic Model Honesty Disclosure */}
      <div className="mb-6 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-slate-300">
        <div className="flex items-center gap-2 text-amber-400 font-semibold mb-1">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>Wake-Word Status Notice</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Continuous wake-word listening ("Hey LOVE") requires a calibrated acoustic ONNX model (<code className="text-amber-300">hey_love.onnx</code>). In browser clients, always-on listening is intentionally disabled for user privacy. Use the push-to-talk microphone button below for authenticated on-demand voice turns.
        </p>
      </div>

      {/* Central Audio Recording Interface */}
      <div className="flex-1 flex flex-col items-center justify-center py-6 mb-6">
        <div className="p-8 rounded-3xl bg-background-secondary/80 border border-border-subtle shadow-2xl flex flex-col items-center max-w-sm w-full">
          <AudioRecorder onAudioReady={handleAudioReady} disabled={isProcessing} />

          {isProcessing && (
            <div className="mt-4 flex items-center gap-2 text-xs text-cyan-400 animate-pulse">
              <div className="w-2 h-2 rounded-full bg-cyan-400" />
              <span>Transcribing and synthesizing response...</span>
            </div>
          )}

          {isPlayingAudio && (
            <div className="mt-4 flex items-center gap-2 text-xs text-purple-400 animate-pulse font-medium">
              <Volume2 className="w-4 h-4" />
              <span>LOVE is speaking...</span>
            </div>
          )}
        </div>
      </div>

      {/* Latest Voice Conversation Turn */}
      {latestTurn && (
        <div className="mb-6 p-4 rounded-2xl bg-background-secondary border border-border-subtle">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Latest Voice Turn
          </h3>
          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-background-tertiary border border-border-subtle">
              <span className="text-[10px] text-slate-500 font-semibold block mb-1">You said:</span>
              <p className="text-slate-100 font-medium">"{latestTurn.user_text || 'No transcription'}"</p>
            </div>

            <div className="p-3 rounded-xl bg-cyan-950/20 border border-cyan-500/30">
              <span className="text-[10px] text-cyan-400 font-semibold block mb-1">LOVE responded:</span>
              <p className="text-cyan-100">{latestTurn.assistant_text || 'No response'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Provider Diagnostics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div className="p-3.5 rounded-2xl bg-background-secondary border border-border-subtle">
          <span className="text-slate-400 block mb-1">Speech Recognition (STT)</span>
          <span className="font-semibold text-slate-200 capitalize">
            {voiceStatus?.stt.name || voiceStatus?.stt_active_provider || 'Whisper Local'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">
            Status: {voiceStatus?.stt.is_available ? 'Ready' : 'Mock/Configured'}
          </span>
        </div>

        <div className="p-3.5 rounded-2xl bg-background-secondary border border-border-subtle">
          <span className="text-slate-400 block mb-1">Speech Synthesis (TTS)</span>
          <span className="font-semibold text-slate-200 capitalize">
            {voiceStatus?.tts.name || voiceStatus?.tts_active_provider || 'Piper Local Neural'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">
            Status: {voiceStatus?.tts.is_available ? 'Ready' : 'Configured'}
          </span>
        </div>
      </div>
    </div>
  );
};
