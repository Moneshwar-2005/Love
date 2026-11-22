import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { intelligenceService } from '../../services/intelligenceService';
import { Message } from '../../types/intelligence';
import { Composer } from './Composer';
import { MessageList } from './MessageList';

interface StreamingState {
  id: string;
  content: string;
  provider?: string;
  model?: string;
}

export const ChatWorkspace: React.FC = () => {
  const {
    activeConversationId,
    setActiveConversationId,
    setAssistantState,
    setCurrentView,
    refreshPendingCounts,
  } = useApp();

  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingMessage, setStreamingMessage] = useState<StreamingState | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load conversation messages
  const loadMessages = async (convId: string) => {
    try {
      setIsLoading(true);
      const detail = await intelligenceService.getConversation(convId);
      setMessages(detail.messages || []);
    } catch (err) {
      console.warn('Failed to load conversation details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeConversationId) {
      loadMessages(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    let convId = activeConversationId;
    if (!convId) {
      try {
        const newConv = await intelligenceService.createConversation(
          text.slice(0, 30) || 'New Conversation'
        );
        convId = newConv.id;
        setActiveConversationId(newConv.id);
      } catch (err) {
        console.error('Failed to create new conversation:', err);
        return;
      }
    }

    // 1. Optimistic User Message
    const userMsg: Message = {
      id: `local-user-${Date.now()}`,
      conversation_id: convId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // 2. Prepare streaming state
    setAssistantState('thinking');
    const streamMsgId = `stream-${Date.now()}`;
    setStreamingMessage({
      id: streamMsgId,
      content: '',
    });

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      let firstChunkReceived = false;
      let finalProvider: string | undefined = undefined;
      let finalModel: string | undefined = undefined;

      await intelligenceService.streamMessage(
        {
          message: text,
          conversation_id: convId,
        },
        {
          onChunk: (chunk) => {
            if (!firstChunkReceived) {
              firstChunkReceived = true;
              setAssistantState('thinking');
            }
            if (chunk.provider) finalProvider = chunk.provider;
            if (chunk.model) finalModel = chunk.model;

            setStreamingMessage((prev) => {
              if (!prev) return null;
              return {
                ...prev,
                content: prev.content + (chunk.delta || ''),
                provider: chunk.provider || prev.provider,
                model: chunk.model || prev.model,
              };
            });
          },
          onDone: (accumulated, lastChunk) => {
            const assistantMsg: Message = {
              id: lastChunk?.message_id || `msg-${Date.now()}`,
              conversation_id: convId!,
              role: 'assistant',
              content: accumulated,
              provider: lastChunk?.provider || finalProvider,
              model: lastChunk?.model || finalModel,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingMessage(null);
            setAssistantState('idle');
            refreshPendingCounts();
          },
          onCancel: (accumulated) => {
            if (accumulated && accumulated.trim()) {
              const cancelledMsg: Message = {
                id: `cancelled-${Date.now()}`,
                conversation_id: convId!,
                role: 'assistant',
                content: `${accumulated}\n\n*[Generation stopped by user]*`,
                provider: finalProvider,
                model: finalModel,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, cancelledMsg]);
            }
            setStreamingMessage(null);
            setAssistantState('idle');
          },
          onError: (err) => {
            console.error('Streaming error:', err);
            const errorMsg: Message = {
              id: `err-${Date.now()}`,
              conversation_id: convId!,
              role: 'assistant',
              content: `⚠️ Error generating response: ${err.message || 'Unknown error occurred'}`,
              created_at: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMsg]);
            setStreamingMessage(null);
            setAssistantState('idle');
          },
        },
        controller.signal
      );
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Failed to complete message stream:', err);
      }
      setStreamingMessage(null);
      setAssistantState('idle');
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (streamingMessage) {
      const partialMsg: Message = {
        id: streamingMessage.id,
        conversation_id: activeConversationId || '',
        role: 'assistant',
        content: streamingMessage.content + ' [Generation stopped by user]',
        provider: streamingMessage.provider,
        model: streamingMessage.model,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, partialMsg]);
      setStreamingMessage(null);
      setAssistantState('idle');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden relative">
      <MessageList
        messages={messages}
        streamingMessage={streamingMessage}
        onSelectPromptStarter={handleSendMessage}
      />

      <Composer
        onSendMessage={handleSendMessage}
        onStopStreaming={handleStopStreaming}
        isStreaming={!!streamingMessage}
        onOpenVoice={() => setCurrentView('voice')}
        disabled={isLoading}
      />
    </div>
  );
};
