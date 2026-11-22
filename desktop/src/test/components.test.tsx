import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { StatusBadge } from '../components/layout/StatusBadge';
import { MessageItem } from '../components/chat/MessageItem';
import { ApprovalQueue } from '../components/work/ApprovalQueue';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { PendingApproval } from '../types/work';

describe('UI Components', () => {
  it('renders StatusBadge with correct text and indicator for different assistant states', () => {
    const { rerender } = render(<StatusBadge state="idle" />);
    expect(screen.getByText('Ready')).toBeInTheDocument();

    rerender(<StatusBadge state="thinking" />);
    expect(screen.getByText('Thinking...')).toBeInTheDocument();

    rerender(<StatusBadge state="responding" />);
    expect(screen.getByText('Generating')).toBeInTheDocument();

    rerender(<StatusBadge state="speaking" />);
    expect(screen.getByText('Speaking')).toBeInTheDocument();

    rerender(<StatusBadge state="listening" />);
    expect(screen.getByText('Listening')).toBeInTheDocument();

    rerender(<StatusBadge state="awaiting_approval" />);
    expect(screen.getByText('Awaiting Approval')).toBeInTheDocument();

    rerender(<StatusBadge state="offline" />);
    expect(screen.getByText('Backend Offline')).toBeInTheDocument();
  });

  it('renders MessageItem with markdown formatting, code block and assistant metadata', () => {
    const mockMessage = {
      id: 'm1',
      conversation_id: 'c1',
      role: 'assistant' as const,
      content: 'Here is the code:\n```typescript\nconst greeting: string = "Hello LOVE";\n```',
      provider: 'ollama',
      model: 'llama3.2',
      total_tokens: 45,
      latency_ms: 320,
      status: 'completed',
      created_at: new Date().toISOString(),
    };

    render(<MessageItem message={mockMessage} />);

    expect(screen.getByText('LOVE')).toBeInTheDocument();
    expect(screen.getByText('ollama / llama3.2')).toBeInTheDocument();
    expect(screen.getByText('320ms')).toBeInTheDocument();
    expect(screen.getByText('45 tokens')).toBeInTheDocument();
    expect(screen.getByText(/const greeting: string/)).toBeInTheDocument();
  });

  it('renders ApprovalQueue with pending actions and risk warnings', async () => {
    const mockApprovals: PendingApproval[] = [
      {
        task_id: 'task-10',
        task_title: 'Project Setup Task',
        action: {
          id: 'action-22',
          task_id: 'task-10',
          step_index: 0,
          title: 'Write Configuration File',
          tool_name: 'workspace_write',
          risk_level: 'high',
          input: { file_path: 'config.json', content: '{}' },
          status: 'pending',
          approval_state: 'pending',
          created_at: new Date().toISOString(),
        },
      },
    ];

    await act(async () => {
      render(
        <AuthProvider>
          <AppProvider>
            <ApprovalQueue approvals={mockApprovals} onRefresh={vi.fn()} />
          </AppProvider>
        </AuthProvider>
      );
    });

    expect(screen.getByText(/Human-in-the-Loop Authorizations Required/)).toBeInTheDocument();
    expect(screen.getByText('Project Setup Task')).toBeInTheDocument();
    expect(screen.getByText('workspace_write')).toBeInTheDocument();
    expect(screen.getByText('high risk')).toBeInTheDocument();
    expect(screen.getByText('Authorize & Run')).toBeInTheDocument();
    expect(screen.getByText('Reject')).toBeInTheDocument();
  });
});
