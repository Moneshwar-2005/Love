import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { voiceService } from '../../services/voiceService';
import { VoiceChatResponse, VoiceStatus } from '../../types/voice';
import { AudioRecorder } from './AudioRecorder';
import {
  Activity,
  AlertCircle,
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
  const [wakeWordActive, setWakeWordActive] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [latestTurn, setLatestTurn] = useState<VoiceChatResponse | null>(null);
  const [turnHistory, setTurnHistory] = useState<VoiceChatResponse[]>([]);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const fetchStatus = async () => {
    try {
      const status = await voiceService.getStatus();
      setVoiceStatus(status);
      const isWakeWordOn = status.wake_word ? status.wake_word.active : !!status.wake_word_active;
      setWakeWordActive(isWakeWordOn);
    } catch (err) {
      console.warn('Failed to fetch voice status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const isModelAvailable = voiceStatus?.wake_word?.model_available ?? false;

  const handleToggleWakeWord = async () => {
    if (!isModelAvailable) {
      alert(
        'Wake-word activation is unavailable: The custom acoustic model "hey_love.onnx" is not installed on this system. You must train or provide the custom model before wake-word listening can be enabled.'
      );
      return;
    }

    try {
      const nextState = !wakeWordActive;
      await voiceService.toggleWakeWord(nextState, true);
      setWakeWordActive(nextState);
    } catch (err: any) {
      console.error('Failed to toggle wake word:', err);
      alert(`Wake-word toggle failed: ${err.message || 'Error occurred'}`);
    }
  };

  const handleAudioReady = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setAssistantState('thinking');

    try {
      const result = await voiceService.sendVoiceTurn(audioBlob);
      setLatestTurn(result);
      setTurnHistory((prev) => [result, ...prev]);

      // Resolve audio base64 from synthesis result or fallback
      const audioBase64 = result.synthesis?.audio_base64 || result.audio_base64;
      const audioFormat = result.synthesis?.format || result.format || 'audio/wav';

      if (audioBase64) {
        setAssistantState('speaking');
        playAudioBase64(audioBase64, audioFormat);
      } else {
        setAssistantState('idle');
      }
    } catch (err: any) {
      console.error('Voice turn processing failed:', err);
      alert(`Voice processing failed: ${err.message || 'Error occurred'}`);
      setAssistantState('idle');
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudioBase64 = (base64Data: string, format: string) => {
    try {
      const audioUrl = `data:${format};base64,${base64Data}`;
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
      const audio = new Audio(audioUrl);
      audioPlayerRef.current = audio;
      setIsPlayingAudio(true);

      audio.onended = () => {
        setIsPlayingAudio(false);
        setAssistantState('idle');
      };
      audio.onerror = () => {
        setIsPlayingAudio(false);
        setAssistantState('idle');
      };
      audio.play();
    } catch (err) {
      console.error('Failed to play audio:', err);
      setIsPlayingAudio(false);
      setAssistantState('idle');
    }
  };

  const sttName = voiceStatus?.stt?.name || voiceStatus?.stt_active_provider || 'faster_whisper';
  const ttsName = voiceStatus?.tts?.name || voiceStatus?.tts_active_provider || 'piper';
  const profileName = voiceStatus?.personality?.name || voiceStatus?.active_personality_profile || 'assistant';
  const isTtsMock = voiceStatus?.tts?.active_provider === 'mock' || ttsName.toLowerCase().includes('mock');
  const isSttMock = voiceStatus?.stt?.active_provider === 'mock' || sttName.toLowerCase().includes('mock');

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden p-6 custom-scrollbar">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-border-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Mic className="w-5 h-5 text-purple-400" />
            <h1 className="text-xl font-bold text-slate-100">Voice Engine & Speech</h1>
          </div>
          <p className="text-xs text-slate-400">
            End-to-end speech recognition, neural TTS synthesis, and wake-word monitoring.
          </p>
        </div>

        {/* Wake Word Switch */}
        <div className="flex items-center gap-3 px-3.5 py-2 rounded-xl bg-background-secondary border border-border-subtle">
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-slate-300">"Hey LOVE" Wake Word</span>
            <span className="text-[10px] text-slate-500">
              {isModelAvailable ? 'Custom acoustic model ready' : 'Model hey_love.onnx not installed'}
            </span>
          </div>

          <button
            onClick={handleToggleWakeWord}
            disabled={!isModelAvailable}
            title={
              !isModelAvailable
                ? 'Wake-word detection is disabled because hey_love.onnx is not present locally.'
                : 'Toggle wake-word acoustic listening'
            }
            className={`w-10 h-5 flex items-center rounded-full p-1 transition-colors ${
              !isModelAvailable
                ? 'bg-slate-800 cursor-not-allowed opacity-50'
                : wakeWordActive
                ? 'bg-cyan-500 cursor-pointer'
                : 'bg-slate-700 cursor-pointer'
            }`}
          >
            <div
              className={`bg-white w-3.5 h-3.5 rounded-full shadow-md transform transition-transform ${
                wakeWordActive ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Wake-word Model Missing Banner (Honest reporting) */}
      {!isModelAvailable && (
        <div className="mb-5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-300">
          <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold block">Wake-Word Detection Inactive</span>
            <span>
              The wake-word acoustic model (<code>hey_love.onnx</code>) is not installed. To prevent false activations or unauthorized continuous listening, wake-word monitoring is disabled. Voice turns can be initiated directly below via the microphone button.
            </span>
          </div>
        </div>
      )}

      {/* Subsystem Provider Badges */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="p-3 rounded-xl bg-background-secondary border border-border-subtle">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">
            STT Provider
          </span>
          <span className="text-xs font-mono text-cyan-400">
            {sttName} {isSttMock && <span className="text-amber-400 text-[10px]">(Mock STT)</span>}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-background-secondary border border-border-subtle">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">
            TTS Provider
          </span>
          <span className="text-xs font-mono text-purple-400">
            {ttsName} {isTtsMock && <span className="text-amber-400 text-[10px]">(Mock TTS)</span>}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-background-secondary border border-border-subtle">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">
            Voice Profile
          </span>
          <span className="text-xs font-mono text-emerald-400">
            {profileName}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-background-secondary border border-border-subtle">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block mb-1">
            Local-Only Mode
          </span>
          <span
            className={`text-xs font-mono ${
              voiceStatus?.local_only_mode ? 'text-emerald-400' : 'text-slate-400'
            }`}
          >
            {voiceStatus?.local_only_mode ? 'Enforced' : 'Flexible'}
          </span>
        </div>
      </div>

      {/* Center Interactive Microphone Area */}
      <div className="my-4 flex flex-col items-center justify-center p-8 rounded-2xl bg-gradient-to-b from-background-secondary to-background border border-border-subtle">
        <AudioRecorder onAudioReady={handleAudioReady} disabled={isProcessing} />

        {isProcessing && (
          <div className="mt-4 flex items-center gap-2 text-xs text-cyan-400 animate-pulse">
            <Activity className="w-4 h-4" />
            <span>Transcribing speech and generating response...</span>
          </div>
        )}

        {isPlayingAudio && (
          <div className="mt-4 flex items-center gap-2 text-xs text-purple-400 animate-pulse">
            <Volume2 className="w-4 h-4" />
            <span>LOVE is speaking...</span>
          </div>
        )}
      </div>

      {/* Latest Conversational Turn */}
      {latestTurn && (
        <div className="mb-6 p-4 rounded-xl bg-background-secondary border border-cyan-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-300">Latest Voice Turn</span>
            <span className="text-[11px] font-mono text-slate-500">
              {latestTurn.latency_ms || latestTurn.processing_time_ms}ms total
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-lg bg-background-tertiary border border-border-subtle">
              <span className="text-slate-400 font-semibold block mb-0.5">You said:</span>
              <p className="text-slate-100 font-medium">
                "{latestTurn.user_text || latestTurn.transcription?.text || latestTurn.transcript}"
              </p>
            </div>

            <div className="p-2.5 rounded-lg bg-cyan-950/20 border border-cyan-500/20">
              <span className="text-cyan-400 font-semibold block mb-0.5">LOVE replied:</span>
              <p className="text-slate-200">
                {latestTurn.assistant_text || latestTurn.reply_text}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
