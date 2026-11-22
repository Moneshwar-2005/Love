import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { ChatWorkspace } from '../components/chat/ChatWorkspace';
import { intelligenceService } from '../services/intelligenceService';
import { MarkdownRenderer } from '../components/chat/MarkdownRenderer';

describe('Web Chat Workspace & SSE Streaming', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders prompt starters in empty state', async () => {
    vi.spyOn(intelligenceService, 'getConversation').mockResolvedValue({
      id: 'conv-1',
      user_id: 'usr-1',
      title: 'New Conversation',
      is_archived: false,
      created_at: new Date().toISOString(),
      messages: [],
    });

    render(
      <AuthProvider>
        <AppProvider>
          <ChatWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/How can LOVE assist you today\?/i)).toBeInTheDocument();
      expect(screen.getByText(/Safe Calculation/i)).toBeInTheDocument();
      expect(screen.getByText(/Personal Memory/i)).toBeInTheDocument();
    });
  });

  it('renders markdown with code block and copy action safely without XSS', () => {
    const rawContent = "Here is a code snippet:\n```python\nprint('Hello LOVE')\n```\nAnd **bold** text.";
    render(<MarkdownRenderer content={rawContent} />);

    expect(screen.getByText("print('Hello LOVE')")).toBeInTheDocument();
    expect(screen.getByText('bold')).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Copy'));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("print('Hello LOVE')\n");
  });

  it('submits a message and streams response tokens', async () => {
    vi.spyOn(intelligenceService, 'createConversation').mockResolvedValue({
      id: 'conv-123',
      user_id: 'usr-1',
      title: 'Math Question',
      is_archived: false,
      created_at: new Date().toISOString(),
    });
    vi.spyOn(intelligenceService, 'getConversation').mockResolvedValue({
      id: 'conv-123',
      user_id: 'usr-1',
      title: 'Math Question',
      is_archived: false,
      created_at: new Date().toISOString(),
      messages: [],
    });

    const streamSpy = vi.spyOn(intelligenceService, 'streamMessage').mockImplementation(
      async (_payload, callbacks) => {
        callbacks.onChunk({ delta: '18% of 45000 is ', is_done: false, provider: 'ollama', model: 'qwen' });
        callbacks.onChunk({ delta: '8100.', is_done: true });
        if (callbacks.onDone) {
          callbacks.onDone('18% of 45000 is 8100.', { message_id: 'msg-99', delta: '', is_done: true, provider: 'ollama', model: 'qwen' });
        }
        return '18% of 45000 is 8100.';
      }
    );

    render(
      <AuthProvider>
        <AppProvider>
          <ChatWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    const input = screen.getByPlaceholderText(/Ask LOVE anything/i);
    fireEvent.change(input, { target: { value: 'Calculate 18% of 45000' } });
    fireEvent.click(screen.getByTitle('Send Message'));

    await waitFor(() => {
      expect(streamSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Calculate 18% of 45000',
        }),
        expect.any(Object),
        expect.any(Object)
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/18% of 45000 is 8100/i)).toBeInTheDocument();
    });
  });
});
