import { apiClient } from './apiClient';
import {
  PendingApproval,
  Task,
  TaskAction,
  TaskStatus,
  ToolDefinition,
} from '../types/work';

export interface TaskCreatePayload {
  description: string;
  title?: string;
  conversation_id?: string;
  auto_execute?: boolean;
}

export class WorkService {
  async listTools(category?: string): Promise<ToolDefinition[]> {
    const qs = category ? `?category=${encodeURIComponent(category)}` : '';
    return await apiClient.get<ToolDefinition[]>(`/api/v1/work/tools${qs}`);
  }

  async listTasks(status?: TaskStatus, limit: number = 30, offset: number = 0): Promise<Task[]> {
    const queryParts: string[] = [`limit=${limit}`, `offset=${offset}`];
    if (status) queryParts.push(`status=${encodeURIComponent(status)}`);
    return await apiClient.get<Task[]>(`/api/v1/work/tasks?${queryParts.join('&')}`);
  }

  async getTask(id: string): Promise<Task> {
    return await apiClient.get<Task>(`/api/v1/work/tasks/${id}`);
  }

  async createTask(payload: TaskCreatePayload): Promise<Task> {
    const autoExec = payload.auto_execute !== undefined ? payload.auto_execute : true;
    return await apiClient.post<Task>(
      `/api/v1/work/tasks?auto_execute=${autoExec}`,
      {
        description: payload.description,
        title: payload.title,
        conversation_id: payload.conversation_id,
      }
    );
  }

  async executeTask(id: string): Promise<Task> {
    return await apiClient.post<Task>(`/api/v1/work/tasks/${id}/execute`);
  }

  async cancelTask(id: string): Promise<Task> {
    return await apiClient.post<Task>(`/api/v1/work/tasks/${id}/cancel`);
  }

  async listPendingApprovals(): Promise<PendingApproval[]> {
    return await apiClient.get<PendingApproval[]>('/api/v1/work/approvals');
  }

  async respondToApproval(
    actionId: string,
    approved: boolean,
    autoResume: boolean = true
  ): Promise<TaskAction> {
    return await apiClient.post<TaskAction>(
      `/api/v1/work/approvals/${actionId}?auto_resume=${autoResume}`,
      { approved }
    );
  }
}

export const workService = new WorkService();
