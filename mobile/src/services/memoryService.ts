/**
 * LOVE Mobile Personal Memory Service.
 * Provides episodic knowledge retrieval and explicit user consent for inferred memories.
 */

import { MemoryCategory, MemoryEntry, MemorySuggestion } from '../types/memory';
import { mobileApiClient } from './apiClient';

export class MobileMemoryService {
  async listMemories(
    category?: MemoryCategory,
    search?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<MemoryEntry[]> {
    let url = `/api/v1/memory?limit=${limit}&offset=${offset}`;
    if (category) url += `&category=${category}`;
    if (search && search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;

    const resp = await mobileApiClient.get<{ memories: MemoryEntry[]; total: number }>(url);
    return resp.memories || [];
  }

  async getMemory(id: string): Promise<MemoryEntry> {
    return await mobileApiClient.get<MemoryEntry>(`/api/v1/memory/${id}`);
  }

  async deleteMemory(id: string): Promise<void> {
    await mobileApiClient.delete(`/api/v1/memory/${id}`);
  }

  async listSuggestions(status: 'pending' | 'accepted' | 'rejected' = 'pending'): Promise<MemorySuggestion[]> {
    const resp = await mobileApiClient.get<{ suggestions: MemorySuggestion[]; total: number }>(
      `/api/v1/memory/suggestions?status=${status}`
    );
    return resp.suggestions || [];
  }

  async resolveSuggestion(
    suggestionId: string,
    approved: boolean
  ): Promise<{ success: boolean; memory?: MemoryEntry }> {
    return await mobileApiClient.post<{ success: boolean; memory?: MemoryEntry }>(
      `/api/v1/memory/suggestions/${suggestionId}/resolve`,
      {
        action: approved ? 'approve' : 'reject',
      }
    );
  }
}

export const mobileMemoryService = new MobileMemoryService();
