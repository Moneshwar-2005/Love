import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { AuthScreen } from '../components/auth/AuthScreen';
import { authService } from '../services/authService';

const TestAuthConsumer: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  if (!isAuthenticated) return <div>Unauthenticated State</div>;
  return (
    <div>
      <div>Authenticated as {user?.username}</div>
      <button onClick={() => logout()}>Log Out</button>
    </div>
  );
};

describe('Web Authentication Flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('restores existing session on startup using HttpOnly cookie', async () => {
    vi.spyOn(authService, 'refresh').mockResolvedValue({
      access_token: 'valid-restored-token',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    vi.spyOn(authService, 'getMe').mockResolvedValue({
      id: 'usr-1',
      username: 'owner',
      email: 'owner@love.ai',
      is_active: true,
      is_verified: true,
      is_owner: true,
      created_at: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Authenticated as owner')).toBeInTheDocument();
    });
  });

  it('renders login screen when unauthenticated and handles login', async () => {
    vi.spyOn(authService, 'refresh').mockResolvedValue(null);
    const loginSpy = vi.spyOn(authService, 'login').mockResolvedValue({
      access_token: 'new-access-token',
      token_type: 'Bearer',
      expires_in: 3600,
      user: {
        id: 'usr-1',
        username: 'testowner',
        email: 'test@love.ai',
        is_active: true,
        is_verified: true,
        is_owner: true,
        created_at: new Date().toISOString(),
      },
    });

    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('owner or owner@example.com')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('owner or owner@example.com'), {
      target: { value: 'testowner' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'ValidPass123!' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          email_or_username: 'testowner',
          password: 'ValidPass123!',
        })
      );
    });
  });

  it('displays authentication error on invalid credentials', async () => {
    vi.spyOn(authService, 'refresh').mockResolvedValue(null);
    vi.spyOn(authService, 'login').mockRejectedValue(new Error('Invalid email/username or password'));

    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('owner or owner@example.com')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('owner or owner@example.com'), {
      target: { value: 'baduser' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'WrongPass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByText(/Invalid email\/username or password/i)).toBeInTheDocument();
    });
  });

  it('performs logout and clears authenticated state', async () => {
    vi.spyOn(authService, 'refresh').mockResolvedValue({
      access_token: 'valid-token',
      token_type: 'Bearer',
      expires_in: 3600,
    });
    vi.spyOn(authService, 'getMe').mockResolvedValue({
      id: 'usr-1',
      username: 'logoutuser',
      email: 'logout@love.ai',
      is_active: true,
      is_verified: true,
      is_owner: true,
      created_at: new Date().toISOString(),
    });
    const logoutSpy = vi.spyOn(authService, 'logout').mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Authenticated as logoutuser')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Log Out'));

    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalled();
      expect(screen.getByText('Unauthenticated State')).toBeInTheDocument();
    });
  });
});
