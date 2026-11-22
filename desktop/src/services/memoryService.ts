import { apiClient } from './apiClient';
import {
  Memory,
  MemoryCategory,
  MemoryStats,
  MemorySuggestion,
} from '../types/memory';

export interface MemoryCreatePayload {
  content: string;
  category?: MemoryCategory;
  tags?: string[];
  key?: string;
}

export interface MemoryUpdatePayload {
  content?: string;
  category?: MemoryCategory;
  tags?: string[];
  is_archived?: boolean;
}

export interface MemorySearchParams {
  query: string;
  limit?: number;
  category?: MemoryCategory;
}

export class MemoryService {
  async listMemories(params?: {
    category?: MemoryCategory;
    tag?: string;
    is_archived?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<Memory[]> {
    const queryParts: string[] = [];
    if (params?.category) queryParts.push(`category=${encodeURIComponent(params.category)}`);
    if (params?.tag) queryParts.push(`tag=${encodeURIComponent(params.tag)}`);
    if (params?.is_archived !== undefined) queryParts.push(`is_archived=${params.is_archived}`);
    if (params?.limit) queryParts.push(`limit=${params.limit}`);
    if (params?.offset) queryParts.push(`offset=${params.offset}`);

    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return await apiClient.get<Memory[]>(`/api/v1/memory${qs}`);
  }

  async searchMemories(params: MemorySearchParams): Promise<Memory[]> {
    const raw = await apiClient.post<any[]>('/api/v1/memory/search', {
      query: params.query,
      category: params.category,
      top_k: params.limit || 10,
    });
    return Array.isArray(raw)
      ? raw.map((item) => (item && item.memory ? item.memory : item))
      : [];
  }

  async createMemory(payload: MemoryCreatePayload): Promise<Memory> {
    return await apiClient.post<Memory>('/api/v1/memory', {
      content: payload.content,
      category: payload.category || 'personal',
      tags: payload.tags || [],
      key: payload.key,
    });
  }

  async getStats(): Promise<MemoryStats> {
    return await apiClient.get<MemoryStats>('/api/v1/memory/stats');
  }

  async getMemory(id: string): Promise<Memory> {
    return await apiClient.get<Memory>(`/api/v1/memory/${id}`);
  }

  async updateMemory(id: string, payload: MemoryUpdatePayload): Promise<Memory> {
    return await apiClient.put<Memory>(`/api/v1/memory/${id}`, payload);
  }

  async deleteMemory(id: string): Promise<{ status: string; id: string }> {
    return await apiClient.delete<{ status: string; id: string }>(`/api/v1/memory/${id}`);
  }

  async listSuggestions(status?: 'pending' | 'approved' | 'rejected', limit: number = 50): Promise<MemorySuggestion[]> {
    const qs = status ? `?status_filter=${status}&limit=${limit}` : `?limit=${limit}`;
    return await apiClient.get<MemorySuggestion[]>(`/api/v1/memory/suggestions${qs}`);
  }

  async approveSuggestion(id: string): Promise<Memory> {
    return await apiClient.post<Memory>(`/api/v1/memory/suggestions/${id}/approve`);
  }

  async rejectSuggestion(id: string): Promise<MemorySuggestion> {
    return await apiClient.post<MemorySuggestion>(`/api/v1/memory/suggestions/${id}/reject`);
  }

  async deleteSuggestion(id: string): Promise<{ status: string; id: string }> {
    return await apiClient.delete<{ status: string; id: string }>(`/api/v1/memory/suggestions/${id}`);
  }
}

export const memoryService = new MemoryService();
