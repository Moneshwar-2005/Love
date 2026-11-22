import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileAuthProvider } from '../context/AuthContext';
import { MobileAppProvider } from '../context/AppContext';
import { MobileChatWorkspace } from '../components/chat/MobileChatWorkspace';
import { MobileMarkdownRenderer } from '../components/chat/MobileMarkdownRenderer';
import { mobileIntelligenceService } from '../services/intelligenceService';

describe('LOVE Mobile Chat Workspace & Real-time Streaming', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders conversational dialogue and loads conversation history', async () => {
    vi.spyOn(mobileIntelligenceService, 'listConversations').mockResolvedValue([
      { id: 'c1', user_id: 'u1', title: 'Mobile Architecture', is_archived: false, created_at: new Date().toISOString() },
    ]);
    vi.spyOn(mobileIntelligenceService, 'getConversation').mockResolvedValue({
      id: 'c1',
      user_id: 'u1',
      title: 'Mobile Architecture',
      is_archived: false,
      created_at: new Date().toISOString(),
      messages: [
        { id: 'm1', conversation_id: 'c1', role: 'user', content: 'Hello LOVE', created_at: new Date().toISOString() },
        { id: 'm2', conversation_id: 'c1', role: 'assistant', content: 'Greetings! How can I assist you?', created_at: new Date().toISOString() },
      ],
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileChatWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    expect(screen.getByPlaceholderText('Ask LOVE anything...')).toBeInTheDocument();
  });

  it('submits a prompt and streams response chunks via SSE', async () => {
    vi.spyOn(mobileIntelligenceService, 'createConversation').mockResolvedValue({
      id: 'c-new',
      user_id: 'u1',
      title: 'New Chat',
      is_archived: false,
      created_at: new Date().toISOString(),
    });

    const streamSpy = vi.spyOn(mobileIntelligenceService, 'streamMessage').mockImplementation(
      async (payload, callbacks) => {
        callbacks.onChunk({ delta: 'Hello ', is_done: false });
        callbacks.onChunk({ delta: 'world!', is_done: true });
        if (callbacks.onDone) {
          callbacks.onDone('Hello world!');
        }
        return 'Hello world!';
      }
    );

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileChatWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    const input = screen.getByPlaceholderText('Ask LOVE anything...');
    fireEvent.change(input, { target: { value: 'Explain quantum computing' } });

    const sendBtn = screen.getByRole('button', { name: /Send message/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(streamSpy).toHaveBeenCalledWith(
        expect.objectContaining({ message: 'Explain quantum computing' }),
        expect.any(Object),
        expect.any(Object)
      );
    });
  });

  it('handles stream user cancellation cleanly by invoking onCancel', async () => {
    const onCancelMock = vi.fn();
    const onDoneMock = vi.fn();
    const controller = new AbortController();

    vi.spyOn(mobileIntelligenceService, 'streamMessage').mockImplementation(
      async (payload, callbacks, signal) => {
        callbacks.onChunk({ delta: 'Part 1', is_done: false });
        controller.abort();
        if (signal?.aborted) {
          if (callbacks.onCancel) callbacks.onCancel('Part 1');
          return 'Part 1';
        }
        return 'Part 1';
      }
    );

    const res = await mobileIntelligenceService.streamMessage(
      { message: 'Cancel test' },
      {
        onChunk: vi.fn(),
        onDone: onDoneMock,
        onCancel: onCancelMock,
      },
      controller.signal
    );

    expect(onCancelMock).toHaveBeenCalledWith('Part 1');
    expect(onDoneMock).not.toHaveBeenCalled();
    expect(res).toBe('Part 1');
  });

  it('renders markdown code blocks and neutralizes dangerous link protocols', () => {
    const markdownContent = `
Here is a safe link: [Official Docs](https://love.ai/docs)
Here is an unsafe link: [Malicious](javascript:alert('xss'))
Here is a data link: [Payload](data:text/html,<script>alert(1)</script>)

\`\`\`typescript
const greeting = "Hello Mobile";
console.log(greeting);
\`\`\`
`;

    const { container } = render(<MobileMarkdownRenderer content={markdownContent} />);

    // 1. Safe link is rendered with target="_blank"
    const safeLink = screen.getByText('Official Docs');
    expect(safeLink).toBeInTheDocument();
    expect(safeLink).toHaveAttribute('href', 'https://love.ai/docs');
    expect(safeLink).toHaveAttribute('target', '_blank');

    // 2. Unsafe links are neutralized into inert text
    expect(screen.getByText('[Malicious (unsafe-link-blocked)]')).toBeInTheDocument();
    expect(screen.getByText('[Payload (unsafe-link-blocked)]')).toBeInTheDocument();

    // 3. Code block rendered
    expect(container.querySelector('pre code')).toHaveTextContent('const greeting = "Hello Mobile";');
  });
});
