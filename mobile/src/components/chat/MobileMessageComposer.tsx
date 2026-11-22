import React, { useState } from 'react';
import { useMobileApp } from '../../context/AppContext';
import { Mic, Send, Square } from 'lucide-react';

interface MobileMessageComposerProps {
  onSendMessage: (text: string) => void;
  onStopGeneration: () => void;
  onOpenVoice: () => void;
  disabled?: boolean;
}

export const MobileMessageComposer: React.FC<MobileMessageComposerProps> = ({
  onSendMessage,
  onStopGeneration,
  onOpenVoice,
  disabled = false,
}) => {
  const { assistantState } = useMobileApp();
  const [inputText, setInputText] = useState<string>('');

  const isStreaming = assistantState === 'thinking' || assistantState === 'speaking' || assistantState === 'executing';

  const handleSend = () => {
    if (!inputText.trim() || disabled) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-3 bg-background-secondary/90 backdrop-blur-md border-t border-border-subtle flex items-end gap-2 shrink-0">
      <div className="flex-1 bg-background-tertiary rounded-2xl border border-border-subtle focus-within:border-cyan-500/50 flex items-center px-3 py-1.5 transition">
        <textarea
          rows={1}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask LOVE anything..."
          disabled={disabled || isStreaming}
          className="w-full bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none resize-none max-h-24 py-1"
        />
      </div>

      {isStreaming ? (
        <button
          onClick={onStopGeneration}
          aria-label="Stop generation"
          className="w-10 h-10 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center justify-center shrink-0 hover:bg-rose-500/30 transition shadow-lg shadow-rose-500/10"
        >
          <Square className="w-4 h-4 fill-current" />
        </button>
      ) : inputText.trim() ? (
        <button
          onClick={handleSend}
          disabled={disabled}
          aria-label="Send message"
          className="w-10 h-10 rounded-2xl bg-cyan-500 text-slate-950 flex items-center justify-center shrink-0 hover:bg-cyan-400 transition shadow-lg shadow-cyan-500/20"
        >
          <Send className="w-4 h-4" />
        </button>
      ) : (
        <button
          onClick={onOpenVoice}
          disabled={disabled}
          aria-label="Open voice input"
          className="w-10 h-10 rounded-2xl bg-background-tertiary border border-border-subtle text-slate-300 hover:text-cyan-400 flex items-center justify-center shrink-0 transition"
        >
          <Mic className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
