import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WorkService } from '../services/workService';
import { apiClient } from '../services/apiClient';

describe('WorkService', () => {
  let work: WorkService;

  beforeEach(() => {
    work = new WorkService();
    vi.restoreAllMocks();
  });

  it('lists tasks with status filter', async () => {
    const mockTasks = [
      {
        id: 'tsk-1',
        user_id: 'u1',
        title: 'Task 1',
        description: 'Do work',
        status: 'completed',
        plan: [],
        actions: [],
        total_steps: 1,
        completed_steps: 1,
        created_at: '',
      },
    ];
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockTasks);

    const tasks = await work.listTasks('completed');
    expect(tasks).toEqual(mockTasks);
    expect(getSpy).toHaveBeenCalledWith(expect.stringContaining('status=completed'));
  });

  it('creates a task with auto_execute parameter', async () => {
    const mockTask = {
      id: 'tsk-2',
      user_id: 'u1',
      title: 'Calc',
      description: 'Calculate 18% of 45000',
      status: 'executing',
      plan: [],
      actions: [],
      total_steps: 1,
      completed_steps: 0,
      created_at: '',
    };
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockTask);

    const task = await work.createTask({
      description: 'Calculate 18% of 45000',
      auto_execute: true,
    });

    expect(task.id).toBe('tsk-2');
    expect(postSpy).toHaveBeenCalledWith(
      '/api/v1/work/tasks?auto_execute=true',
      expect.objectContaining({ description: 'Calculate 18% of 45000' })
    );
  });

  it('responds to pending approval action', async () => {
    const mockActionResponse = {
      id: 'act-99',
      task_id: 'tsk-1',
      step_index: 0,
      title: 'Write File',
      tool_name: 'workspace_write',
      risk_level: 'medium',
      input: { path: 'result.txt', content: 'test' },
      status: 'completed',
      approval_state: 'approved',
      created_at: '',
    };

    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockActionResponse);

    const res = await work.respondToApproval('act-99', true, true);
    expect(res.approval_state).toBe('approved');
    expect(postSpy).toHaveBeenCalledWith(
      '/api/v1/work/approvals/act-99?auto_resume=true',
      { approved: true }
    );
  });
});
