import React, { useEffect, useRef, useState } from 'react';
import { Mic, Send, Square } from 'lucide-react';

interface ComposerProps {
  onSendMessage: (text: string) => void;
  onStopStreaming?: () => void;
  isStreaming: boolean;
  onOpenVoice: () => void;
  disabled?: boolean;
}

export const Composer: React.FC<ComposerProps> = ({
  onSendMessage,
  onStopStreaming,
  isStreaming,
  onOpenVoice,
  disabled = false,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on input height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;

    onSendMessage(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-4 bg-background-secondary/90 border-t border-border-subtle">
      <form onSubmit={handleSubmit} className="relative flex items-end gap-2 max-w-4xl mx-auto">
        {/* Voice Trigger Button */}
        <button
          type="button"
          onClick={onOpenVoice}
          className="p-2.5 rounded-xl bg-background-tertiary border border-border-subtle hover:border-cyan-500/50 hover:bg-cyan-500/10 text-slate-300 hover:text-cyan-400 transition-colors flex-shrink-0"
          title="Open Voice Interface"
        >
          <Mic className="w-4 h-4" />
        </button>

        {/* Text Input Container */}
        <div className="flex-1 min-w-0 rounded-xl bg-background-tertiary border border-border-subtle focus-within:border-cyan-500/70 focus-within:ring-1 focus-within:ring-cyan-500/20 transition-all flex items-center px-3 py-1.5">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask LOVE anything, execute tasks, or save memories... (Enter to send, Shift+Enter for newline)"
            disabled={disabled}
            className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 resize-none outline-none leading-relaxed custom-scrollbar max-h-40"
          />
        </div>

        {/* Action Button: Send or Stop */}
        {isStreaming ? (
          <button
            type="button"
            onClick={onStopStreaming}
            className="p-2.5 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-300 hover:bg-rose-500/30 transition-colors flex-shrink-0"
            title="Stop Generation"
          >
            <Square className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim() || disabled}
            className={`p-2.5 rounded-xl flex-shrink-0 transition-all ${
              input.trim() && !disabled
                ? 'bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-md shadow-cyan-500/25 hover:from-cyan-400 hover:to-indigo-500 cursor-pointer'
                : 'bg-background-tertiary text-slate-600 border border-border-subtle cursor-not-allowed'
            }`}
            title="Send Message"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>
    </div>
  );
};
