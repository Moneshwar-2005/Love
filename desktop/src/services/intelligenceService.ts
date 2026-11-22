import { apiClient } from './apiClient';
import {
  Conversation,
  ConversationDetail,
  IntelligenceStatus,
  Message,
  ModelInfo,
  ProviderStatus,
  StreamChunk,
} from '../types/intelligence';

export interface ChatRequestPayload {
  message: string;
  conversation_id?: string;
  provider?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  local_only?: boolean;
}

export class IntelligenceService {
  async listConversations(limit: number = 30, offset: number = 0): Promise<Conversation[]> {
    return await apiClient.get<Conversation[]>(
      `/api/v1/intelligence/conversations?limit=${limit}&offset=${offset}`
    );
  }

  async createConversation(title?: string): Promise<Conversation> {
    return await apiClient.post<Conversation>('/api/v1/intelligence/conversations', {
      title: title || 'New Conversation',
    });
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return await apiClient.get<ConversationDetail>(`/api/v1/intelligence/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/intelligence/conversations/${id}`);
  }

  async sendMessageSync(payload: ChatRequestPayload): Promise<Message> {
    return await apiClient.post<Message>('/api/v1/intelligence/chat', payload);
  }

  async streamMessage(
    payload: ChatRequestPayload,
    callbacks: {
      onChunk: (chunk: StreamChunk) => void;
      onDone?: (fullText: string, finalChunk?: StreamChunk) => void;
      onError?: (error: any) => void;
    },
    signal?: AbortSignal
  ): Promise<string> {
    try {
      const response = await apiClient.fetchStream('/api/v1/intelligence/chat/stream', payload);
      if (!response.body) {
        throw new Error('ReadableStream not supported by backend response.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulated = '';
      let lastChunk: StreamChunk | undefined = undefined;

      while (true) {
        if (signal?.aborted) {
          await reader.cancel();
          break;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last partial line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const jsonStr = trimmed.slice(6);
            if (!jsonStr) continue;
            try {
              const chunk: StreamChunk = JSON.parse(jsonStr);
              lastChunk = chunk;
              if (chunk.delta) {
                accumulated += chunk.delta;
              }
              callbacks.onChunk(chunk);
              if (chunk.is_done) {
                break;
              }
            } catch (parseErr) {
              console.warn('Failed to parse SSE JSON chunk:', jsonStr, parseErr);
            }
          }
        }
      }

      callbacks.onDone?.(accumulated, lastChunk);
      return accumulated;
    } catch (err: any) {
      if (callbacks.onError) {
        callbacks.onError(err);
      }
      throw err;
    }
  }

  async listProviders(): Promise<ProviderStatus[]> {
    return await apiClient.get<ProviderStatus[]>('/api/v1/intelligence/providers');
  }

  async listModels(provider?: string, localOnly: boolean = false): Promise<ModelInfo[]> {
    let url = `/api/v1/intelligence/models?local_only=${localOnly}`;
    if (provider) {
      url += `&provider=${encodeURIComponent(provider)}`;
    }
    return await apiClient.get<ModelInfo[]>(url);
  }

  async getStatus(): Promise<IntelligenceStatus> {
    return await apiClient.get<IntelligenceStatus>('/api/v1/intelligence/status');
  }
}

export const intelligenceService = new IntelligenceService();
