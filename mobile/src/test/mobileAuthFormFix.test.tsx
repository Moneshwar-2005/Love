import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileAuthProvider } from '../context/AuthContext';
import { MobileAuthScreen, formatAuthError } from '../components/auth/MobileAuthScreen';
import { mobileApiClient } from '../services/apiClient';
import { mobileAuthService } from '../services/authService';
import { mobileSecureStorage } from '../services/mobileSecureStorage';

describe('LOVE Mobile Phase 12.7C: Mode Switching, Normalization & Error Display', () => {
  beforeEach(async () => {
    vi.restoreAllMocks();
    await mobileSecureStorage.clearSecureStore();
    mobileApiClient.setAccessToken(null);
  });

  describe('1. Mode Switching & UI State', () => {
    it('defaults to Sign In mode on initial render', () => {
      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      // Verify Sign In is active
      expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument();
      expect(screen.getByPlaceholderText('username or email')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('user@example.com')).not.toBeInTheDocument();
    });

    it('switches to Create Account mode when segmented tab or footer link is tapped', async () => {
      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      // Tap Create Account in segmented selector
      const createTab = screen.getByRole('tab', { name: /Create Account Tab/i });
      fireEvent.click(createTab);

      // Email and username fields now visible
      expect(screen.getByPlaceholderText('user@example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('username')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();

      // Tap footer link to switch back to Sign In
      const signInLink = screen.getByText(/Already have an account\? Sign In/i);
      fireEvent.click(signInLink);

      // Sign In mode restored
      expect(screen.getByPlaceholderText('username or email')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('user@example.com')).not.toBeInTheDocument();
    });

    it('preserves user input across mode switches', () => {
      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      // Type username in Sign In
      fireEvent.change(screen.getByPlaceholderText('username or email'), {
        target: { value: 'loveowner' },
      });
      fireEvent.change(screen.getByPlaceholderText('••••••••'), {
        target: { value: 'SecretPassword123!' },
      });

      // Switch to Create Account via tab
      fireEvent.click(screen.getByRole('tab', { name: /Create Account Tab/i }));

      // Username and password transferred/preserved
      expect(screen.getByPlaceholderText('username')).toHaveValue('loveowner');
      expect(screen.getByPlaceholderText('••••••••')).toHaveValue('SecretPassword123!');

      // Switch back to Sign In
      fireEvent.click(screen.getByText(/Already have an account\? Sign In/i));

      expect(screen.getByPlaceholderText('username or email')).toHaveValue('loveowner');
      expect(screen.getByPlaceholderText('••••••••')).toHaveValue('SecretPassword123!');
    });
  });

  describe('2. Input Normalization', () => {
    it('trims leading and trailing whitespace from login identifier while preserving password', async () => {
      const loginSpy = vi.spyOn(mobileAuthService, 'login').mockResolvedValue({
        user: {
          id: 'usr-owner',
          username: 'loveowner',
          email: 'owner@love.ai',
          is_active: true,
          is_verified: true,
          is_owner: true,
          created_at: new Date().toISOString(),
        },
        access_token: 'tok-123',
        refresh_token: 'ref-456',
        token_type: 'Bearer',
        expires_in: 3600,
      });

      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      // Enter untrimmed username and password with preserved space
      fireEvent.change(screen.getByPlaceholderText('username or email'), {
        target: { value: '   loveowner   ' },
      });
      fireEvent.change(screen.getByPlaceholderText('••••••••'), {
        target: { value: ' Secret With Spaces ' },
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

      await waitFor(() => {
        expect(loginSpy).toHaveBeenCalledWith({
          email_or_username: 'loveowner', // Trimmed!
          password: ' Secret With Spaces ', // NOT trimmed! Preserved!
        });
      });
    });

    it('trims leading and trailing whitespace from registration username and email', async () => {
      const registerSpy = vi.spyOn(mobileAuthService, 'register').mockResolvedValue({
        id: 'usr-new',
        username: 'newuser',
        email: 'newuser@love.ai',
        is_active: true,
        is_verified: false,
        is_owner: false,
        created_at: new Date().toISOString(),
      });
      vi.spyOn(mobileAuthService, 'login').mockResolvedValue({} as any);

      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      // Switch to Register
      fireEvent.click(screen.getByRole('tab', { name: /Create Account Tab/i }));

      fireEvent.change(screen.getByPlaceholderText('user@example.com'), {
        target: { value: '   newuser@love.ai   ' },
      });
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: '   newuser   ' },
      });
      fireEvent.change(screen.getByPlaceholderText('••••••••'), {
        target: { value: ' ExactPass123! ' },
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /^Create Account$/i }));

      await waitFor(() => {
        expect(registerSpy).toHaveBeenCalledWith({
          email: 'newuser@love.ai', // Trimmed!
          username: 'newuser', // Trimmed!
          password: ' ExactPass123! ', // NOT trimmed!
        });
      });
    });

    it('rejects empty or whitespace-only values before sending request', async () => {
      const loginSpy = vi.spyOn(mobileAuthService, 'login');

      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      // Only whitespace
      fireEvent.change(screen.getByPlaceholderText('username or email'), {
        target: { value: '    ' },
      });
      fireEvent.change(screen.getByPlaceholderText('••••••••'), {
        target: { value: 'pass' },
      });

      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

      await waitFor(() => {
        expect(screen.getByText('Please complete the required fields.')).toBeInTheDocument();
      });

      expect(loginSpy).not.toHaveBeenCalled();
    });
  });

  describe('3. Validation Error Conversion & Display', () => {
    it('converts raw Pydantic validation errors to human-friendly message', () => {
      const rawPydanticError = {
        message: 'string_pattern_mismatch at body.username',
        status: 422,
      };
      expect(formatAuthError(rawPydanticError)).toBe('Please enter a valid username.');

      const emailError = {
        message: 'value_error at body.email',
        status: 422,
      };
      expect(formatAuthError(emailError)).toBe('Please enter a valid email address.');
    });

    it('converts network failures into clean server connection advice', () => {
      const netError = {
        message: 'Network failure connecting to LOVE backend: Failed to fetch',
        status: 0,
      };
      expect(formatAuthError(netError)).toBe('LOVE cannot connect to the server. Please try again.');
    });

    it('converts 401 unauthorized to clear invalid credentials message', () => {
      const authError = {
        status: 401,
        message: 'Invalid email/username or password.',
      };
      expect(formatAuthError(authError)).toBe('Invalid email/username or password.');
    });

    it('maintains form mounted and displays clean error banner upon login failure', async () => {
      vi.spyOn(mobileAuthService, 'login').mockRejectedValue({
        status: 401,
        message: 'Invalid email/username or password.',
      });

      render(
        <MobileAuthProvider>
          <MobileAuthScreen />
        </MobileAuthProvider>
      );

      fireEvent.change(screen.getByPlaceholderText('username or email'), {
        target: { value: 'wronguser' },
      });
      fireEvent.change(screen.getByPlaceholderText('••••••••'), {
        target: { value: 'wrongpass' },
      });

      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

      await waitFor(() => {
        expect(screen.getByText('Invalid email/username or password.')).toBeInTheDocument();
      });

      // Verify form is still mounted with user input preserved
      expect(screen.getByPlaceholderText('username or email')).toHaveValue('wronguser');
      expect(screen.getByPlaceholderText('••••••••')).toHaveValue('wrongpass');
    });
  });
});
