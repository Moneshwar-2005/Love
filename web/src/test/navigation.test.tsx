import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider, useApp } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { AppLayout } from '../components/layout/AppLayout';
import { SettingsModal } from '../components/settings/SettingsModal';
import { authService } from '../services/authService';
import { apiClient } from '../services/apiClient';

const MockViewSwitcher: React.FC = () => {
  const { currentView } = useApp();
  return <div data-testid="active-view-container">{currentView}</div>;
};

describe('Web Navigation & Responsive Layout', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders layout and switches navigation views', async () => {
    vi.spyOn(authService, 'refresh').mockResolvedValue({
      access_token: 'valid',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    vi.spyOn(authService, 'getMe').mockResolvedValue({
      id: 'usr-1',
      username: 'navowner',
      email: 'nav@love.ai',
      is_active: true,
      is_verified: true,
      is_owner: true,
      created_at: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <AppProvider>
          <AppLayout onOpenSystemStatus={vi.fn()} onOpenSettings={vi.fn()}>
            <MockViewSwitcher />
          </AppLayout>
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('LOVE')).toBeInTheDocument();
      expect(screen.getByText('Work Intelligence')).toBeInTheDocument();
      expect(screen.getByText('Personal Memory')).toBeInTheDocument();
    });

    // Switch to Work Intelligence
    fireEvent.click(screen.getByText('Work Intelligence'));
    expect(screen.getByTestId('active-view-container')).toHaveTextContent('work');

    // Switch to Personal Memory
    fireEvent.click(screen.getByText('Personal Memory'));
    expect(screen.getByTestId('active-view-container')).toHaveTextContent('memory');

    // Switch to Dashboard
    fireEvent.click(screen.getByText('Dashboard'));
    expect(screen.getByTestId('active-view-container')).toHaveTextContent('dashboard');
  });

  it('updates API base URL via Settings modal', async () => {
    const setBaseUrlSpy = vi.spyOn(apiClient, 'setBaseUrl');
    const closeSpy = vi.fn();

    render(
      <AuthProvider>
        <AppProvider>
          <SettingsModal onClose={closeSpy} />
        </AppProvider>
      </AuthProvider>
    );

    expect(screen.getByText('Preferences & System Settings')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('http://127.0.0.1:8000');
    fireEvent.change(input, { target: { value: 'http://192.168.1.100:8000' } });

    fireEvent.click(screen.getByText('Apply Settings'));

    expect(setBaseUrlSpy).toHaveBeenCalledWith('http://192.168.1.100:8000');
    expect(closeSpy).toHaveBeenCalled();
  });
});
