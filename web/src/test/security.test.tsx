import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from '../components/chat/MarkdownRenderer';
import { ApiClient } from '../services/apiClient';
import { IntelligenceService } from '../services/intelligenceService';
import { authService } from '../services/authService';

describe('Phase 11.5 Web Security & XSS Sanitization Tests', () => {
  describe('MarkdownRenderer XSS Protection', () => {
    it('renders legitimate https markdown links with rel="noopener noreferrer"', () => {
      render(<MarkdownRenderer content="Read the [LOVE Docs](https://docs.love.ai) for details." />);
      const link = screen.getByRole('link', { name: 'LOVE Docs' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://docs.love.ai');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('blocks and neutralizes javascript: URLs in markdown links', () => {
      const { container } = render(
        <MarkdownRenderer content="Click [Malicious Exploit](javascript:alert(document.cookie)) to continue." />
      );
      // Ensure no <a> tag with javascript: was created
      const link = container.querySelector('a[href^="javascript:"]');
      expect(link).toBeNull();
      // Verify safe blocked placeholder text
      expect(screen.getByText(/unsafe-link-blocked/i)).toBeInTheDocument();
    });

    it('blocks data: and vbscript: URLs in markdown links', () => {
      const { container } = render(
        <MarkdownRenderer content="Test [Data Link](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==) and [VB Link](vbscript:msgbox(1))." />
      );
      expect(container.querySelector('a[href^="data:"]')).toBeNull();
      expect(container.querySelector('a[href^="vbscript:"]')).toBeNull();
    });

    it('renders raw script tags as inert text nodes without execution', () => {
      const { container } = render(
        <MarkdownRenderer content="Here is some code: <script>window.pwned=true;</script>" />
      );
      expect(container.querySelector('script')).toBeNull();
      expect(screen.getByText(/<script>window\.pwned=true;<\/script>/)).toBeInTheDocument();
    });

    it('renders image tags with event handlers as inert text without executing handlers', () => {
      const { container } = render(
        <MarkdownRenderer content="Malicious image: <img src='invalid' onerror='alert(1)' />" />
      );
      expect(container.querySelector('img')).toBeNull();
      expect(screen.getByText(/<img src='invalid' onerror='alert\(1\)' \/>/)).toBeInTheDocument();
    });
  });

  describe('ApiClient 401 Queue & Concurrency Lifecycle', () => {
    let client: ApiClient;

    beforeEach(() => {
      client = new ApiClient('http://127.0.0.1:8000');
      vi.restoreAllMocks();
    });

    it('coalesces multiple simultaneous 401 requests into exactly one refresh call', async () => {
      let refreshCallCount = 0;
      let requestAttemptCount = 0;

      // Mock fetch
      vi.spyOn(global, 'fetch').mockImplementation(async (url: any) => {
        const urlStr = String(url);
        if (urlStr.includes('/api/v1/auth/refresh')) {
          refreshCallCount++;
          return new Response(
            JSON.stringify({
              access_token: 'new-valid-refreshed-token',
              token_type: 'Bearer',
              expires_in: 3600,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } }
          );
        }

        requestAttemptCount++;
        // First turn: token expired, return 401
        if (requestAttemptCount <= 3) {
          return new Response(JSON.stringify({ detail: 'Token expired' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        // Subsequent retries with new token succeed
        return new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      });

      // Fire 3 simultaneous requests with expired token
      client.setAccessToken('expired-token-123');
      const [res1, res2, res3] = await Promise.all([
        client.get('/api/v1/work/tasks'),
        client.get('/api/v1/memory'),
        client.get('/api/v1/system/metrics'),
      ]);

      // Exactly ONE refresh request should have fired
      expect(refreshCallCount).toBe(1);
      expect(res1).toEqual({ success: true });
      expect(res2).toEqual({ success: true });
      expect(res3).toEqual({ success: true });
      expect(client.getAccessToken()).toBe('new-valid-refreshed-token');
    });

    it('rejects all queued requests and invokes onUnauthorized when refresh fails', async () => {
      const onUnauthorized = vi.fn();
      client.setOnUnauthorized(onUnauthorized);

      vi.spyOn(global, 'fetch').mockImplementation(async (url: any) => {
        const urlStr = String(url);
        if (urlStr.includes('/api/v1/auth/refresh')) {
          return new Response(JSON.stringify({ detail: 'Token revoked' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ detail: 'Token expired' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      });

      client.setAccessToken('expired-token');

      const results = await Promise.allSettled([
        client.get('/api/v1/work/tasks'),
        client.get('/api/v1/memory'),
      ]);

      expect(results[0].status).toBe('rejected');
      expect(results[1].status).toBe('rejected');
      expect(onUnauthorized).toHaveBeenCalled();
      expect(client.getAccessToken()).toBeNull();
    });
  });

  describe('IntelligenceService Stream Cancellation Security', () => {
    it('does not invoke onDone when stream is aborted by user', async () => {
      const intService = new IntelligenceService();
      const controller = new AbortController();

      const onChunk = vi.fn((chunk) => {
        if (chunk.delta === 'Hello') {
          controller.abort();
        }
      });
      const onDone = vi.fn();
      const onCancel = vi.fn();

      // Mock streaming body with two chunks
      const stream = new ReadableStream({
        start(ctrl) {
          ctrl.enqueue(new TextEncoder().encode('data: {"delta": "Hello", "is_done": false}\n\n'));
          ctrl.enqueue(new TextEncoder().encode('data: {"delta": " World", "is_done": true}\n\n'));
          ctrl.close();
        },
      });

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
      );

      await intService.streamMessage(
        { message: 'Hello' },
        { onChunk, onDone, onCancel },
        controller.signal
      );

      expect(onChunk).toHaveBeenCalled();
      expect(onDone).not.toHaveBeenCalled();
      expect(onCancel).toHaveBeenCalled();
    });
  });

  describe('Browser Device Identity Security', () => {
    beforeEach(() => {
      localStorage.clear();
      vi.restoreAllMocks();
    });

    it('generates a clean UUID device identifier prefixed with web- without leaking hardware data', async () => {
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: 'mock-token',
            refresh_token: 'mock-refresh',
            token_type: 'Bearer',
            expires_in: 3600,
            user: { id: 'u1', username: 'owner', email: 'owner@love.ai', is_owner: true, is_active: true, is_verified: true, created_at: '' },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      );

      await authService.login({ email_or_username: 'owner', password: 'pass' });

      const storedDeviceId = localStorage.getItem('love_web_device_id');
      expect(storedDeviceId).toBeDefined();
      expect(storedDeviceId).toMatch(/^web-[0-9a-fA-F-]+$/);
      // Ensure no private hardware identifiers leaked
      expect(storedDeviceId).not.toContain('MAC');
      expect(storedDeviceId).not.toContain('IP');
    });
  });
});
