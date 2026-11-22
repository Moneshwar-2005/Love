/**
 * LOVE Mobile Intelligence Service.
 * Manages conversation lifecycle, provider/model discovery, and real-time SSE token streaming.
 */

import {
  ChatRequestPayload,
  Conversation,
  ConversationDetail,
  IntelligenceStatus,
  Message,
  ModelInfo,
  ProviderStatus,
  StreamChunk,
} from '../types/intelligence';
import { mobileApiClient } from './apiClient';

export class MobileIntelligenceService {
  async listConversations(limit: number = 50, offset: number = 0): Promise<Conversation[]> {
    return await mobileApiClient.get<Conversation[]>(
      `/api/v1/intelligence/conversations?limit=${limit}&offset=${offset}`
    );
  }

  async createConversation(title?: string): Promise<Conversation> {
    return await mobileApiClient.post<Conversation>('/api/v1/intelligence/conversations', {
      title: title || 'New Mobile Conversation',
    });
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return await mobileApiClient.get<ConversationDetail>(`/api/v1/intelligence/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    await mobileApiClient.delete(`/api/v1/intelligence/conversations/${id}`);
  }

  async sendMessageSync(payload: ChatRequestPayload): Promise<Message> {
    return await mobileApiClient.post<Message>('/api/v1/intelligence/chat', payload);
  }

  async streamMessage(
    payload: ChatRequestPayload,
    callbacks: {
      onChunk: (chunk: StreamChunk) => void;
      onDone?: (fullText: string, finalChunk?: StreamChunk) => void;
      onCancel?: (accumulated: string) => void;
      onError?: (error: any) => void;
    },
    signal?: AbortSignal
  ): Promise<string> {
    let accumulated = '';
    let wasAborted = false;

    try {
      const reader = await mobileApiClient.fetchStream(
        '/api/v1/intelligence/chat',
        {
          ...payload,
          stream: true,
        },
        signal
      );

      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let lastChunk: StreamChunk | undefined;

      while (true) {
        if (signal?.aborted) {
          wasAborted = true;
          await reader.cancel();
          break;
        }

        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const jsonStr = trimmed.slice(6);
            if (jsonStr === '[DONE]') {
              continue;
            }
            try {
              const parsed: StreamChunk = JSON.parse(jsonStr);
              lastChunk = parsed;
              if (parsed.delta) {
                accumulated += parsed.delta;
                callbacks.onChunk(parsed);
              }
            } catch {
              // Non-JSON or keepalive line
            }
          }
        }
      }

      if (wasAborted || signal?.aborted) {
        if (callbacks.onCancel) {
          callbacks.onCancel(accumulated);
        }
        return accumulated;
      }

      if (callbacks.onDone) {
        callbacks.onDone(accumulated, lastChunk);
      }
      return accumulated;
    } catch (err: any) {
      if (signal?.aborted || err.name === 'AbortError') {
        if (callbacks.onCancel) {
          callbacks.onCancel(accumulated);
        }
        return accumulated;
      }
      if (callbacks.onError) {
        callbacks.onError(err);
      }
      throw err;
    }
  }

  async getStatus(): Promise<IntelligenceStatus> {
    return await mobileApiClient.get<IntelligenceStatus>('/api/v1/intelligence/status');
  }

  async listProviders(): Promise<ProviderStatus[]> {
    return await mobileApiClient.get<ProviderStatus[]>('/api/v1/intelligence/providers');
  }

  async listModels(provider?: string, localOnly: boolean = false): Promise<ModelInfo[]> {
    let url = `/api/v1/intelligence/models?local_only=${localOnly}`;
    if (provider) {
      url += `&provider=${encodeURIComponent(provider)}`;
    }
    return await mobileApiClient.get<ModelInfo[]>(url);
  }
}

export const mobileIntelligenceService = new MobileIntelligenceService();
