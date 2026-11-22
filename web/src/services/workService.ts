import { apiClient } from './apiClient';
import {
  PendingApproval,
  Task,
  TaskAction,
  ToolDefinition,
} from '../types/work';

export interface CreateTaskPayload {
  title: string;
  description: string;
  conversation_id?: string;
  auto_execute?: boolean;
}

export class WorkService {
  async listTools(): Promise<ToolDefinition[]> {
    return await apiClient.get<ToolDefinition[]>('/api/v1/work/tools');
  }

  async listTasks(statusFilter?: string): Promise<Task[]> {
    const url = statusFilter
      ? `/api/v1/work/tasks?status=${encodeURIComponent(statusFilter)}`
      : '/api/v1/work/tasks';
    return await apiClient.get<Task[]>(url);
  }

  async createTask(payload: CreateTaskPayload): Promise<Task> {
    return await apiClient.post<Task>('/api/v1/work/tasks', payload);
  }

  async getTask(taskId: string): Promise<Task> {
    return await apiClient.get<Task>(`/api/v1/work/tasks/${taskId}`);
  }

  async executeTask(taskId: string): Promise<Task> {
    return await apiClient.post<Task>(`/api/v1/work/tasks/${taskId}/execute`, {});
  }

  async cancelTask(taskId: string): Promise<Task> {
    return await apiClient.post<Task>(`/api/v1/work/tasks/${taskId}/cancel`, {});
  }

  async listPendingApprovals(): Promise<PendingApproval[]> {
    return await apiClient.get<PendingApproval[]>('/api/v1/work/approvals');
  }

  async resolveApproval(
    actionId: string,
    decision: 'approve' | 'reject',
    reason?: string
  ): Promise<TaskAction> {
    return await apiClient.post<TaskAction>(`/api/v1/work/approvals/${actionId}`, {
      decision,
      reason,
    });
  }
}

export const workService = new WorkService();
