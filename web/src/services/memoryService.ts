import { apiClient } from './apiClient';
import {
  Memory,
  MemoryCategory,
  MemoryStats,
  MemorySuggestion,
} from '../types/memory';

export interface CreateMemoryPayload {
  content: string;
  category?: MemoryCategory;
  tags?: string[];
  key?: string;
}

export class MemoryService {
  async listMemories(params?: {
    category?: MemoryCategory;
    is_archived?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<Memory[]> {
    const query = new URLSearchParams();
    if (params?.category) query.append('category', params.category);
    if (params?.is_archived !== undefined) query.append('is_archived', String(params.is_archived));
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const queryString = query.toString();
    const url = queryString ? `/api/v1/memory?${queryString}` : '/api/v1/memory';
    return await apiClient.get<Memory[]>(url);
  }

  async createMemory(payload: CreateMemoryPayload): Promise<Memory> {
    return await apiClient.post<Memory>('/api/v1/memory', payload);
  }

  async updateMemory(
    id: string,
    payload: { content?: string; category?: MemoryCategory; tags?: string[]; is_archived?: boolean }
  ): Promise<Memory> {
    return await apiClient.put<Memory>(`/api/v1/memory/${id}`, payload);
  }

  async deleteMemory(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/memory/${id}`);
  }

  async searchMemories(query: string, limit: number = 10): Promise<Memory[]> {
    return await apiClient.post<Memory[]>('/api/v1/memory/search', {
      query,
      limit,
    });
  }

  async getStats(): Promise<MemoryStats> {
    return await apiClient.get<MemoryStats>('/api/v1/memory/stats');
  }

  async listSuggestions(status: string = 'pending'): Promise<MemorySuggestion[]> {
    return await apiClient.get<MemorySuggestion[]>(`/api/v1/memory/suggestions?status=${status}`);
  }

  async approveSuggestion(id: string): Promise<Memory> {
    return await apiClient.post<Memory>(`/api/v1/memory/suggestions/${id}/approve`, {});
  }

  async rejectSuggestion(id: string): Promise<void> {
    await apiClient.post(`/api/v1/memory/suggestions/${id}/reject`, {});
  }
}

export const memoryService = new MemoryService();
