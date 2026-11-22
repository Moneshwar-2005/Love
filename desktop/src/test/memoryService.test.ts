import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryService } from '../services/memoryService';
import { apiClient } from '../services/apiClient';

describe('MemoryService', () => {
  let memory: MemoryService;

  beforeEach(() => {
    memory = new MemoryService();
    vi.restoreAllMocks();
  });

  it('lists memories and filters by category', async () => {
    const mockMemories = [
      {
        id: 'mem-1',
        user_id: 'u1',
        content: 'Prefers TypeScript',
        category: 'personal',
        tags: ['typescript'],
        confidence_score: 1.0,
        source_type: 'explicit',
        is_archived: false,
        created_at: '',
      },
    ];
    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockMemories);

    const list = await memory.listMemories({ category: 'personal' });
    expect(list).toEqual(mockMemories);
    expect(getSpy).toHaveBeenCalledWith(expect.stringContaining('category=personal'));
  });

  it('approves a memory suggestion', async () => {
    const mockApprovedMemory = {
      id: 'mem-2',
      user_id: 'u1',
      content: 'Likes dark mode',
      category: 'personal',
      tags: ['ui'],
      confidence_score: 0.95,
      source_type: 'suggestion_approved',
      is_archived: false,
      created_at: '',
    };
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockApprovedMemory);

    const res = await memory.approveSuggestion('sug-123');
    expect(res).toEqual(mockApprovedMemory);
    expect(postSpy).toHaveBeenCalledWith('/api/v1/memory/suggestions/sug-123/approve');
  });

  it('rejects a memory suggestion', async () => {
    const mockRejected = {
      id: 'sug-456',
      user_id: 'u1',
      content: 'Random noise',
      category: 'personal',
      tags: [],
      confidence: 0.5,
      status: 'rejected',
      created_at: '',
    };
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockRejected);

    const res = await memory.rejectSuggestion('sug-456');
    expect(res.status).toBe('rejected');
    expect(postSpy).toHaveBeenCalledWith('/api/v1/memory/suggestions/sug-456/reject');
  });
});
