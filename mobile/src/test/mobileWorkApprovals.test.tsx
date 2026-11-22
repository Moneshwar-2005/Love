import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileAuthProvider } from '../context/AuthContext';
import { MobileAppProvider } from '../context/AppContext';
import { MobileWorkWorkspace } from '../components/work/MobileWorkWorkspace';
import { mobileWorkService } from '../services/workService';
import { PendingApproval, Task } from '../types/work';

describe('LOVE Mobile Work Intelligence & HITL Approvals', () => {
  const mockTasks: Task[] = [
    {
      id: 'task-101',
      user_id: 'usr-1',
      title: 'Analyze Codebase Security',
      description: 'Audit mobile permissions and keystore configuration',
      status: 'completed',
      plan: [
        { step: 1, description: 'Scan AndroidManifest.xml', risk_level: 'low' },
        { step: 2, description: 'Verify Info.plist keys', risk_level: 'low' },
      ],
      actions: [],
      total_steps: 2,
      completed_steps: 2,
      created_at: new Date().toISOString(),
    },
  ];

  const mockApprovals: PendingApproval[] = [
    {
      task_id: 'task-102',
      task_title: 'Database Backup',
      action: {
        id: 'act-201',
        task_id: 'task-102',
        step_index: 1,
        title: 'Export SQLite Database to External Storage',
        tool_name: 'storage_export',
        risk_level: 'high',
        input: { target: '/sdcard/backups/love.db' },
        status: 'awaiting_approval',
        created_at: new Date().toISOString(),
      },
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders pending approval queue with risk badges and action details', async () => {
    vi.spyOn(mobileWorkService, 'listTasks').mockResolvedValue(mockTasks);
    vi.spyOn(mobileWorkService, 'listPendingApprovals').mockResolvedValue(mockApprovals);

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileWorkWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Export SQLite Database to External Storage')).toBeInTheDocument();
      expect(screen.getByText('high')).toBeInTheDocument();
      expect(screen.getByText(/storage_export/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Authorize/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reject/i })).toBeInTheDocument();
    });
  });

  it('authorizes pending action and notifies backend', async () => {
    vi.spyOn(mobileWorkService, 'listTasks').mockResolvedValue(mockTasks);
    vi.spyOn(mobileWorkService, 'listPendingApprovals').mockResolvedValue(mockApprovals);
    const resolveSpy = vi.spyOn(mobileWorkService, 'resolveApproval').mockResolvedValue({
      success: true,
      message: 'Authorized',
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileWorkWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Export SQLite Database to External Storage')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Authorize/i }));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith('act-201', true);
    });
  });

  it('rejects pending action when user clicks Reject', async () => {
    vi.spyOn(mobileWorkService, 'listTasks').mockResolvedValue(mockTasks);
    vi.spyOn(mobileWorkService, 'listPendingApprovals').mockResolvedValue(mockApprovals);
    const resolveSpy = vi.spyOn(mobileWorkService, 'resolveApproval').mockResolvedValue({
      success: true,
      message: 'Rejected',
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileWorkWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Export SQLite Database to External Storage')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Reject/i }));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith('act-201', false);
    });
  });

  it('creates an autonomous work task with title and description', async () => {
    const createSpy = vi.spyOn(mobileWorkService, 'createTask').mockResolvedValue({
      id: 'task-new',
      user_id: 'usr-1',
      title: 'Audit Mobile Storage',
      description: 'Check Keystore backing',
      status: 'pending',
      plan: [],
      actions: [],
      total_steps: 1,
      completed_steps: 0,
      created_at: new Date().toISOString(),
    });

    const task = await mobileWorkService.createTask({
      title: 'Audit Mobile Storage',
      description: 'Check Keystore backing',
      auto_execute: true,
    });

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Audit Mobile Storage',
      description: 'Check Keystore backing',
      auto_execute: true,
    });
    expect(task.id).toBe('task-new');
  });
});
