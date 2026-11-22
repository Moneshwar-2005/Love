import React, { useState } from 'react';
import { mobileVoiceService } from '../../services/voiceService';
import { Mic, MicOff, Volume2, X } from 'lucide-react';

interface MobileVoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscriptionComplete: (text: string) => void;
}

export const MobileVoiceModal: React.FC<MobileVoiceModalProps> = ({
  isOpen,
  onClose,
  onTranscriptionComplete,
}) => {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [transcribedText, setTranscribedText] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleStartRecording = async () => {
    setErrorMsg(null);
    setTranscribedText('');
    try {
      await mobileVoiceService.startRecording();
      setIsRecording(true);
    } catch (err: any) {
      setErrorMsg(err.message || 'Microphone permission was denied.');
    }
  };

  const handleStopRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);
    setIsProcessing(true);

    try {
      const blob = await mobileVoiceService.stopRecording();
      const res = await mobileVoiceService.transcribeAudio(blob);
      if (res && res.text) {
        setTranscribedText(res.text);
        onTranscriptionComplete(res.text);
      } else {
        setErrorMsg('No speech detected in audio capture.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Voice transcription failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/75 backdrop-blur-sm">
      <div className="w-full sm:max-w-md bg-background-secondary border-t sm:border border-border-subtle rounded-t-3xl sm:rounded-3xl p-6 flex flex-col items-center text-center space-y-6 shadow-2xl">
        {/* Header */}
        <div className="w-full flex items-center justify-between">
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold">
            <Volume2 className="w-4 h-4" />
            <span>Push-to-Talk Voice Engine</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close voice modal"
            className="p-1 rounded-lg text-slate-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Visual Pulse / Indicator */}
        <div className="relative flex items-center justify-center my-4">
          <div
            className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 ${
              isRecording
                ? 'bg-rose-500/20 text-rose-400 ring-4 ring-rose-500/30 animate-pulse'
                : isProcessing
                ? 'bg-cyan-500/20 text-cyan-400 ring-4 ring-cyan-500/30'
                : 'bg-background-tertiary text-slate-300'
            }`}
          >
            {isRecording ? <Mic className="w-12 h-12" /> : <MicOff className="w-10 h-10" />}
          </div>
        </div>

        {/* State text */}
        <div className="space-y-1">
          <h3 className="text-base font-bold text-white">
            {isRecording
              ? 'Listening...'
              : isProcessing
              ? 'Transcribing Speech...'
              : 'Tap to Speak to LOVE'}
          </h3>
          <p className="text-xs text-slate-400 max-w-xs">
            {isRecording
              ? 'Tap Stop when finished speaking'
              : isProcessing
              ? 'Analyzing sovereign speech model...'
              : 'Hold or tap the mic button to capture speech'}
          </p>
        </div>

        {/* Transcribed Output */}
        {transcribedText && (
          <div className="w-full p-3 rounded-2xl bg-background-tertiary/60 border border-border-subtle text-xs text-cyan-300 text-left">
            <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Transcription</span>
            "{transcribedText}"
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="w-full p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs text-left">
            {errorMsg}
          </div>
        )}

        {/* Controls */}
        <div className="w-full flex items-center justify-center gap-3">
          {isRecording ? (
            <button
              onClick={handleStopRecording}
              className="w-full py-3 rounded-2xl bg-rose-500 text-white font-bold text-xs hover:bg-rose-400 transition shadow-lg shadow-rose-500/20"
            >
              Stop Recording & Send
            </button>
          ) : (
            <button
              onClick={handleStartRecording}
              disabled={isProcessing}
              className="w-full py-3 rounded-2xl bg-cyan-500 text-slate-950 font-bold text-xs hover:bg-cyan-400 transition disabled:opacity-50 shadow-lg shadow-cyan-500/20"
            >
              {isProcessing ? 'Processing...' : 'Start Speaking'}
            </button>
          )}
        </div>

        {/* Privacy notice */}
        <p className="text-[10px] text-slate-500">
          Privacy Policy: Raw audio recordings are never stored permanently on device or server.
        </p>
      </div>
    </div>
  );
};
