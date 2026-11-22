import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { WorkWorkspace } from '../components/work/WorkWorkspace';
import { workService } from '../services/workService';
import { Task, PendingApproval } from '../types/work';

describe('Web Work Intelligence & Human-in-the-Loop Approvals', () => {
  const mockTasks: Task[] = [
    {
      id: 'task-1',
      user_id: 'usr-1',
      title: 'Analyze Repository',
      description: 'Run static analysis on backend codebase',
      status: 'completed',
      plan: [],
      actions: [],
      total_steps: 2,
      completed_steps: 2,
      created_at: new Date().toISOString(),
    },
  ];

  const mockApprovals: PendingApproval[] = [
    {
      task_id: 'task-2',
      task_title: 'Database Export',
      action: {
        id: 'act-101',
        task_id: 'task-2',
        step_index: 0,
        title: 'Export user records to CSV',
        tool_name: 'filesystem_write',
        risk_level: 'high',
        input: { path: 'exports/users.csv' },
        status: 'awaiting_approval',
        approval_state: 'pending',
        created_at: new Date().toISOString(),
      },
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders task list and pending approval queue', async () => {
    vi.spyOn(workService, 'listTasks').mockResolvedValue(mockTasks);
    vi.spyOn(workService, 'listPendingApprovals').mockResolvedValue(mockApprovals);

    render(
      <AuthProvider>
        <AppProvider>
          <WorkWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Universal Work Intelligence')).toBeInTheDocument();
      expect(screen.getByText('Analyze Repository')).toBeInTheDocument();
      expect(screen.getByText(/Human-in-the-Loop Authorizations Required/i)).toBeInTheDocument();
      expect(screen.getByText('filesystem_write')).toBeInTheDocument();
      expect(screen.getByText(/high risk/i)).toBeInTheDocument();
    });
  });

  it('authorizes pending action when user clicks Authorize & Run', async () => {
    vi.spyOn(workService, 'listTasks').mockResolvedValue([]);
    vi.spyOn(workService, 'listPendingApprovals').mockResolvedValue(mockApprovals);
    const resolveSpy = vi.spyOn(workService, 'resolveApproval').mockResolvedValue({
      id: 'act-101',
      task_id: 'task-2',
      step_index: 0,
      title: 'Export user records',
      tool_name: 'filesystem_write',
      risk_level: 'high',
      input: {},
      status: 'approved',
      approval_state: 'approved',
      created_at: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <AppProvider>
          <WorkWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Authorize & Run')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Authorize & Run'));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith('act-101', 'approve');
    });
  });

  it('rejects pending action when user clicks Reject', async () => {
    vi.spyOn(workService, 'listTasks').mockResolvedValue([]);
    vi.spyOn(workService, 'listPendingApprovals').mockResolvedValue(mockApprovals);
    const resolveSpy = vi.spyOn(workService, 'resolveApproval').mockResolvedValue({
      id: 'act-101',
      task_id: 'task-2',
      step_index: 0,
      title: 'Export user records',
      tool_name: 'filesystem_write',
      risk_level: 'high',
      input: {},
      status: 'rejected',
      approval_state: 'rejected',
      created_at: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <AppProvider>
          <WorkWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Reject')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Reject'));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith('act-101', 'reject');
    });
  });
});
