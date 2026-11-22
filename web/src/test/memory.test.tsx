import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { MemoryWorkspace } from '../components/memory/MemoryWorkspace';
import { memoryService } from '../services/memoryService';
import { Memory, MemorySuggestion } from '../types/memory';

describe('Web Personal Memory & Consent Workflow', () => {
  const mockMemories: Memory[] = [
    {
      id: 'mem-1',
      user_id: 'usr-1',
      content: 'User prefers concise responses with bullet points',
      category: 'personal',
      tags: ['preferences', 'formatting'],
      confidence_score: 1.0,
      source_type: 'direct',
      is_archived: false,
      created_at: new Date().toISOString(),
    },
  ];

  const mockSuggestions: MemorySuggestion[] = [
    {
      id: 'sug-1',
      user_id: 'usr-1',
      content: 'User works with Pytest and Vite',
      category: 'project',
      tags: ['dev', 'stack'],
      confidence: 0.95,
      rationale: 'Inferred from user request about testing',
      status: 'pending',
      created_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders memory entries and pending explicit consent suggestions', async () => {
    vi.spyOn(memoryService, 'listMemories').mockResolvedValue(mockMemories);
    vi.spyOn(memoryService, 'listSuggestions').mockResolvedValue(mockSuggestions);

    render(
      <AuthProvider>
        <AppProvider>
          <MemoryWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Persistent Personal Memory')).toBeInTheDocument();
      expect(screen.getByText('User prefers concise responses with bullet points')).toBeInTheDocument();
      expect(screen.getByText(/Extracted Memory Suggestions Requiring Your Consent/i)).toBeInTheDocument();
      expect(screen.getByText(/"User works with Pytest and Vite"/i)).toBeInTheDocument();
    });
  });

  it('promotes suggestion to canonical memory upon explicit user approval', async () => {
    vi.spyOn(memoryService, 'listMemories').mockResolvedValue(mockMemories);
    vi.spyOn(memoryService, 'listSuggestions').mockResolvedValue(mockSuggestions);
    const approveSpy = vi.spyOn(memoryService, 'approveSuggestion').mockResolvedValue({
      id: 'mem-new',
      user_id: 'usr-1',
      content: 'User works with Pytest and Vite',
      category: 'project',
      tags: ['dev'],
      confidence_score: 0.95,
      source_type: 'suggestion_approved',
      is_archived: false,
      created_at: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <AppProvider>
          <MemoryWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Save Memory')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Save Memory'));

    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith('sug-1');
    });
  });

  it('discards suggestion when user rejects it', async () => {
    vi.spyOn(memoryService, 'listMemories').mockResolvedValue(mockMemories);
    vi.spyOn(memoryService, 'listSuggestions').mockResolvedValue(mockSuggestions);
    const rejectSpy = vi.spyOn(memoryService, 'rejectSuggestion').mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <AppProvider>
          <MemoryWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Reject')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Reject'));

    await waitFor(() => {
      expect(rejectSpy).toHaveBeenCalledWith('sug-1');
    });
  });
});
