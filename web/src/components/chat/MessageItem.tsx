import React, { useState } from 'react';
import { Message } from '../../types/intelligence';
import { MarkdownRenderer } from './MarkdownRenderer';
import { Bot, Check, Copy, Cpu, Clock, User } from 'lucide-react';

interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, isStreaming = false }) => {
  const isAssistant = message.role === 'assistant';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedTime = new Date(message.created_at || Date.now()).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className={`group flex gap-3 px-3 sm:px-4 py-3 rounded-2xl transition-colors ${
        isAssistant
          ? 'bg-background-secondary/80 border border-border-subtle/60'
          : 'bg-background-tertiary/40 border border-transparent'
      }`}
      data-testid={`message-${message.role}`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 pt-0.5">
        {isAssistant ? (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
            <Bot className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-slate-700 flex items-center justify-center text-slate-300">
            <User className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Message Body & Metadata */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-200">
              {isAssistant ? 'LOVE' : 'You'}
            </span>
            <span className="text-[10px] text-slate-500">{formattedTime}</span>
          </div>

          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-background-tertiary text-slate-400 hover:text-slate-200 transition-opacity"
            title="Copy message"
            aria-label="Copy message text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Content */}
        <div className="text-slate-200 text-sm leading-relaxed break-words">
          <MarkdownRenderer content={message.content} />
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-cyan-400 animate-pulse ml-0.5 align-middle" />
          )}
        </div>

        {/* Assistant Metadata Footer */}
        {isAssistant && (message.provider || message.latency_ms || message.tokens_completion) && (
          <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-border-subtle/40 text-[11px] text-slate-400">
            {message.provider && (
              <span className="flex items-center gap-1 font-mono text-cyan-400">
                <Cpu className="w-3 h-3" />
                <span>{message.provider}{message.model ? ` / ${message.model}` : ''}</span>
              </span>
            )}

            {message.latency_ms && (
              <span className="flex items-center gap-1 text-slate-400">
                <Clock className="w-3 h-3" />
                <span>{message.latency_ms}ms</span>
              </span>
            )}

            {message.tokens_completion && (
              <span className="text-slate-500 font-mono">
                {message.tokens_completion} tokens
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
