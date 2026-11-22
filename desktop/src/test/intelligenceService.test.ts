import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IntelligenceService } from '../services/intelligenceService';
import { apiClient } from '../services/apiClient';

describe('IntelligenceService', () => {
  let intelligence: IntelligenceService;

  beforeEach(() => {
    intelligence = new IntelligenceService();
    vi.restoreAllMocks();
  });

  it('lists conversations and creates conversation', async () => {
    const mockConversations = [
      { id: 'c1', user_id: 'u1', title: 'Conversation 1', is_archived: false, created_at: '' },
    ];
    vi.spyOn(apiClient, 'get').mockResolvedValue(mockConversations);
    vi.spyOn(apiClient, 'post').mockResolvedValue({
      id: 'c2',
      user_id: 'u1',
      title: 'New Chat',
      is_archived: false,
      created_at: '',
    });

    const list = await intelligence.listConversations();
    expect(list).toHaveLength(1);
    expect(list[0].title).toBe('Conversation 1');

    const created = await intelligence.createConversation('New Chat');
    expect(created.id).toBe('c2');
  });

  it('streams response chunks via SSE reader and dispatches onChunk & onDone', async () => {
    const sseLines = [
      'data: {"conversation_id": "c1", "message_id": "m1", "delta": "Hello", "role": "assistant", "is_done": false, "status": "streaming"}\n\n',
      'data: {"conversation_id": "c1", "message_id": "m1", "delta": " world!", "role": "assistant", "is_done": true, "status": "completed"}\n\n',
    ];

    const encoder = new TextEncoder();
    let index = 0;

    const mockReadableStream = {
      getReader: () => ({
        read: async () => {
          if (index < sseLines.length) {
            const value = encoder.encode(sseLines[index++]);
            return { done: false, value };
          }
          return { done: true, value: undefined };
        },
        cancel: vi.fn(),
      }),
    };

    vi.spyOn(apiClient, 'fetchStream').mockResolvedValue({
      body: mockReadableStream,
    } as any);

    const receivedDeltas: string[] = [];
    let completedText = '';

    await intelligence.streamMessage(
      { message: 'Hi' },
      {
        onChunk: (chunk) => {
          receivedDeltas.push(chunk.delta);
        },
        onDone: (fullText) => {
          completedText = fullText;
        },
      }
    );

    expect(receivedDeltas).toEqual(['Hello', ' world!']);
    expect(completedText).toBe('Hello world!');
  });
});
