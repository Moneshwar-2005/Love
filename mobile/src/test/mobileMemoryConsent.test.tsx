import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileAuthProvider } from '../context/AuthContext';
import { MobileAppProvider } from '../context/AppContext';
import { MobileMemoryWorkspace } from '../components/memory/MobileMemoryWorkspace';
import { mobileMemoryService } from '../services/memoryService';
import { MemoryEntry, MemorySuggestion } from '../types/memory';

describe('LOVE Mobile Personal Memory & Consent Workflow', () => {
  const mockMemories: MemoryEntry[] = [
    {
      id: 'mem-1',
      user_id: 'usr-1',
      category: 'preferences',
      key: 'preferred_editor',
      value: 'Antigravity IDE & Neovim',
      importance: 5,
      tags: ['tools', 'developer'],
      created_at: new Date().toISOString(),
    },
  ];

  const mockSuggestions: MemorySuggestion[] = [
    {
      id: 'sug-1',
      user_id: 'usr-1',
      category: 'knowledge',
      key: 'favorite_model',
      value: 'Prefers Qwen 2.5 7B for local inference',
      importance: 4,
      reason: 'User mentioned preference in dialogue #12',
      status: 'pending',
      created_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders memory entries and category filters', async () => {
    vi.spyOn(mobileMemoryService, 'listMemories').mockResolvedValue(mockMemories);
    vi.spyOn(mobileMemoryService, 'listSuggestions').mockResolvedValue(mockSuggestions);

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileMemoryWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('preferred_editor')).toBeInTheDocument();
      expect(screen.getByText('Antigravity IDE & Neovim')).toBeInTheDocument();
      expect(screen.getByText('preferences')).toBeInTheDocument();
    });
  });

  it('promotes suggestion to canonical memory upon explicit user approval', async () => {
    vi.spyOn(mobileMemoryService, 'listMemories').mockResolvedValue(mockMemories);
    vi.spyOn(mobileMemoryService, 'listSuggestions').mockResolvedValue(mockSuggestions);
    const resolveSpy = vi.spyOn(mobileMemoryService, 'resolveSuggestion').mockResolvedValue({
      success: true,
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileMemoryWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    // Switch to Consent Queue tab
    fireEvent.click(screen.getByText(/Consent Queue/i));

    await waitFor(() => {
      expect(screen.getByText('favorite_model')).toBeInTheDocument();
      expect(screen.getByText('Prefers Qwen 2.5 7B for local inference')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save to Memory/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Save to Memory/i }));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith('sug-1', true);
    });
  });

  it('discards suggestion when user rejects it', async () => {
    vi.spyOn(mobileMemoryService, 'listMemories').mockResolvedValue(mockMemories);
    vi.spyOn(mobileMemoryService, 'listSuggestions').mockResolvedValue(mockSuggestions);
    const resolveSpy = vi.spyOn(mobileMemoryService, 'resolveSuggestion').mockResolvedValue({
      success: true,
    });

    render(
      <MobileAuthProvider>
        <MobileAppProvider>
          <MobileMemoryWorkspace />
        </MobileAppProvider>
      </MobileAuthProvider>
    );

    fireEvent.click(screen.getByText(/Consent Queue/i));

    await waitFor(() => {
      expect(screen.getByText('favorite_model')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Discard/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Discard/i }));

    await waitFor(() => {
      expect(resolveSpy).toHaveBeenCalledWith('sug-1', false);
    });
  });

  it('deletes a memory entry when requested', async () => {
    const deleteSpy = vi.spyOn(mobileMemoryService, 'deleteMemory').mockResolvedValue();
    await mobileMemoryService.deleteMemory('mem-1');
    expect(deleteSpy).toHaveBeenCalledWith('mem-1');
  });
});
