import React, { useEffect, useRef, useState } from 'react';
import { useMobileApp } from '../../context/AppContext';
import { ConversationDetail, Message } from '../../types/intelligence';
import { mobileIntelligenceService } from '../../services/intelligenceService';
import { MobileConversationDrawer } from './MobileConversationDrawer';
import { MobileMarkdownRenderer } from './MobileMarkdownRenderer';
import { MobileMessageComposer } from './MobileMessageComposer';
import { MobileVoiceModal } from '../voice/MobileVoiceModal';
import { Menu, Plus } from 'lucide-react';

export const MobileChatWorkspace: React.FC = () => {
  const { activeConversationId, setActiveConversationId, assistantState, setAssistantState } = useMobileApp();
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState<string>('');
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isVoiceOpen, setIsVoiceOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const loadConversation = async (id: string) => {
    try {
      setIsLoading(true);
      const detail: ConversationDetail = await mobileIntelligenceService.getConversation(id);
      setMessages(detail.messages || []);
    } catch (err) {
      console.warn('Failed to load conversation messages:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeConversationId) {
      loadConversation(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  const handleNewConversation = async () => {
    try {
      const conv = await mobileIntelligenceService.createConversation();
      setActiveConversationId(conv.id);
      setMessages([]);
    } catch (err) {
      console.warn('Failed to create new conversation:', err);
    }
  };

  const handleSendMessage = async (text: string) => {
    let convId = activeConversationId;
    if (!convId) {
      try {
        const conv = await mobileIntelligenceService.createConversation(
          text.slice(0, 30) + (text.length > 30 ? '...' : '')
        );
        convId = conv.id;
        setActiveConversationId(conv.id);
      } catch (err) {
        console.warn('Auto conversation create failed:', err);
        return;
      }
    }

    const userMessage: Message = {
      id: `usr-${Date.now()}`,
      conversation_id: convId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setStreamingContent('');
    setAssistantState('thinking');

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await mobileIntelligenceService.streamMessage(
        {
          message: text,
          conversation_id: convId,
        },
        {
          onChunk: (chunk) => {
            setAssistantState('speaking');
            setStreamingContent((prev) => prev + chunk.delta);
          },
          onDone: (fullText, finalChunk) => {
            const assistantMessage: Message = {
              id: finalChunk?.message_id || `asst-${Date.now()}`,
              conversation_id: convId!,
              role: 'assistant',
              content: fullText,
              provider: finalChunk?.provider,
              model: finalChunk?.model,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMessage]);
            setStreamingContent('');
            setAssistantState('idle');
          },
          onCancel: (accumulated) => {
            if (accumulated) {
              const cancelledMessage: Message = {
                id: `asst-stopped-${Date.now()}`,
                conversation_id: convId!,
                role: 'assistant',
                content: `${accumulated}\n\n*[Generation stopped by user]*`,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, cancelledMessage]);
            }
            setStreamingContent('');
            setAssistantState('idle');
          },
          onError: (err) => {
            console.warn('Stream message error:', err);
            setAssistantState('idle');
          },
        },
        controller.signal
      );
    } catch {
      setAssistantState('idle');
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      {/* Top action strip for Drawer & New Chat */}
      <div className="px-3 py-1.5 bg-background-secondary/60 border-b border-border-subtle flex items-center justify-between text-xs shrink-0">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="flex items-center gap-1.5 py-1 px-2 rounded-lg text-slate-300 hover:bg-background-tertiary transition"
        >
          <Menu className="w-4 h-4 text-cyan-400" />
          <span className="text-[11px] font-medium">Conversations</span>
        </button>

        <button
          onClick={handleNewConversation}
          className="flex items-center gap-1 py-1 px-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-semibold text-[11px] hover:bg-cyan-500/20 transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-500">Loading conversation history...</div>
        ) : messages.length === 0 && !streamingContent ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16 space-y-3 px-4">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center font-bold text-lg">
              L
            </div>
            <h2 className="text-sm font-bold text-white">How can LOVE assist you today?</h2>
            <p className="text-xs text-slate-400 max-w-xs">
              Sovereign personal AI with persistent memory, autonomous work planning, and local inference.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-3.5 ${
                      isUser
                        ? 'bg-cyan-600 text-white rounded-br-sm'
                        : 'bg-background-secondary border border-border-subtle rounded-bl-sm'
                    }`}
                  >
                    <MobileMarkdownRenderer content={msg.content} />
                  </div>
                  {msg.provider && (
                    <span className="text-[9px] text-slate-500 font-mono mt-1 px-1">
                      {msg.model || msg.provider}
                    </span>
                  )}
                </div>
              );
            })}

            {streamingContent && (
              <div className="flex flex-col items-start">
                <div className="max-w-[85%] rounded-2xl p-3.5 bg-background-secondary border border-cyan-500/30 rounded-bl-sm">
                  <MobileMarkdownRenderer content={streamingContent} />
                  <span className="inline-block w-1.5 h-3.5 ml-1 bg-cyan-400 animate-pulse align-middle" />
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Composer */}
      <MobileMessageComposer
        onSendMessage={handleSendMessage}
        onStopGeneration={handleStopGeneration}
        onOpenVoice={() => setIsVoiceOpen(true)}
      />

      {/* Slide-out Drawer */}
      <MobileConversationDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        activeConversationId={activeConversationId}
        onSelectConversation={(id) => setActiveConversationId(id)}
        onNewConversation={handleNewConversation}
      />

      {/* Voice Push-to-Talk Modal */}
      <MobileVoiceModal
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        onTranscriptionComplete={(text) => {
          setIsVoiceOpen(false);
          handleSendMessage(text);
        }}
      />
    </div>
  );
};
