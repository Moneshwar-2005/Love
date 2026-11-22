import React, { useEffect, useRef } from 'react';
import { Message } from '../../types/intelligence';
import { MessageItem } from './MessageItem';
import { Sparkles, Terminal, Database, Calculator } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  streamingMessage: { id: string; content: string; provider?: string; model?: string } | null;
  onSelectPromptStarter: (prompt: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  streamingMessage,
  onSelectPromptStarter,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage?.content]);

  if (messages.length === 0 && !streamingMessage) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyan-600/20 to-indigo-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-4 shadow-xl shadow-cyan-500/10">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-1">How can LOVE help you today?</h2>
        <p className="text-sm text-slate-400 max-w-md mb-8">
          LOVE is your personal, sovereign AI assistant. Ask any question, execute safe work tasks, or manage memories.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-xl w-full text-left">
          <button
            onClick={() => onSelectPromptStarter('Calculate 18% of 45000 and explain the calculation.')}
            className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-cyan-500/50 hover:bg-background-tertiary transition-all group"
          >
            <div className="flex items-center gap-2 mb-1 text-cyan-400 text-xs font-semibold">
              <Calculator className="w-4 h-4" />
              <span>Safe Calculation</span>
            </div>
            <p className="text-xs text-slate-300">
              Calculate 18% of 45000 and explain the result.
            </p>
          </button>

          <button
            onClick={() => onSelectPromptStarter('Remember that my preferred stack is FastAPI, React, and PostgreSQL.')}
            className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-cyan-500/50 hover:bg-background-tertiary transition-all group"
          >
            <div className="flex items-center gap-2 mb-1 text-emerald-400 text-xs font-semibold">
              <Database className="w-4 h-4" />
              <span>Personal Memory</span>
            </div>
            <p className="text-xs text-slate-300">
              Remember that my preferred stack is FastAPI and React.
            </p>
          </button>

          <button
            onClick={() => onSelectPromptStarter('Analyze the current project architecture and explain model routing.')}
            className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-cyan-500/50 hover:bg-background-tertiary transition-all group"
          >
            <div className="flex items-center gap-2 mb-1 text-purple-400 text-xs font-semibold">
              <Terminal className="w-4 h-4" />
              <span>System Intelligence</span>
            </div>
            <p className="text-xs text-slate-300">
              Analyze the current project architecture and explain model routing.
            </p>
          </button>

          <button
            onClick={() => onSelectPromptStarter('What tools are registered in your work execution layer?')}
            className="p-3.5 rounded-xl bg-background-secondary border border-border-subtle hover:border-cyan-500/50 hover:bg-background-tertiary transition-all group"
          >
            <div className="flex items-center gap-2 mb-1 text-amber-400 text-xs font-semibold">
              <Sparkles className="w-4 h-4" />
              <span>Tool Discovery</span>
            </div>
            <p className="text-xs text-slate-300">
              What tools are registered in your work execution layer?
            </p>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}

      {streamingMessage && (
        <MessageItem
          message={{
            id: streamingMessage.id,
            conversation_id: '',
            role: 'assistant',
            content: streamingMessage.content,
            provider: streamingMessage.provider,
            model: streamingMessage.model,
            status: 'streaming',
            created_at: new Date().toISOString(),
          }}
          isStreaming={true}
        />
      )}

      <div ref={bottomRef} />
    </div>
  );
};
