/**
 * LOVE Mobile Work Service.
 * Manages background autonomous tasks and Human-in-the-Loop action approvals.
 */

import { CreateTaskPayload, PendingApproval, Task, TaskStatus } from '../types/work';
import { mobileApiClient } from './apiClient';

export class MobileWorkService {
  async listTasks(status?: TaskStatus, limit: number = 20, offset: number = 0): Promise<Task[]> {
    let url = `/api/v1/work/tasks?limit=${limit}&offset=${offset}`;
    if (status) {
      url += `&status=${status}`;
    }
    const resp = await mobileApiClient.get<{ tasks: Task[]; total: number }>(url);
    return resp.tasks || [];
  }

  async createTask(payload: CreateTaskPayload): Promise<Task> {
    return await mobileApiClient.post<Task>('/api/v1/work/tasks', payload);
  }

  async getTask(id: string): Promise<Task> {
    return await mobileApiClient.get<Task>(`/api/v1/work/tasks/${id}`);
  }

  async cancelTask(id: string): Promise<Task> {
    return await mobileApiClient.post<Task>(`/api/v1/work/tasks/${id}/cancel`);
  }

  async listPendingApprovals(): Promise<PendingApproval[]> {
    const resp = await mobileApiClient.get<{ approvals: PendingApproval[]; total: number }>(
      '/api/v1/work/approvals'
    );
    return resp.approvals || [];
  }

  async resolveApproval(
    actionId: string,
    approved: boolean,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    return await mobileApiClient.post<{ success: boolean; message: string }>(
      `/api/v1/work/approvals/${actionId}`,
      {
        approved,
        reason: reason || (approved ? 'Authorized from mobile client' : 'Rejected from mobile client'),
      }
    );
  }
}

export const mobileWorkService = new MobileWorkService();
