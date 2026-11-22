/**
 * LOVE Phase 12 — Mobile Application Screenshot Capture.
 * Uses Electron runtime (Chromium) configured for a 390x844 mobile viewport
 * to capture high-fidelity screenshots of all primary mobile views.
 */

const { app, BrowserWindow } = require('electron');
const http = require('http');
const path = require('path');
const fs = require('fs');

const distDir = path.join(__dirname, '../dist');
const screenshotsDir = path.join(__dirname, '../screenshots');

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

const logFile = path.join(screenshotsDir, 'capture.log');
fs.writeFileSync(logFile, `=== MOBILE CAPTURE [${new Date().toISOString()}] ===\n`);
function log(msg) {
  console.log(msg);
  try {
    fs.appendFileSync(logFile, msg + '\n');
  } catch (e) {}
}

let isAuthenticated = false;

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

const PORT = 4195;

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  log(`HTTP ${req.method} ${url}`);

  // API Mock Handler
  if (url.startsWith('/api/v1/')) {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
      res.writeHead(204);
      return res.end();
    }

    if (url === '/api/v1/auth/refresh') {
      if (isAuthenticated) {
        res.writeHead(200);
        return res.end(JSON.stringify({
          access_token: 'mock-mobile-access-token',
          refresh_token: 'mock-mobile-refresh-token',
          token_type: 'Bearer',
          expires_in: 3600,
        }));
      } else {
        res.writeHead(401);
        return res.end(JSON.stringify({ detail: 'Unauthenticated' }));
      }
    }

    if (url === '/api/v1/auth/login') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        access_token: 'mock-mobile-access-token',
        refresh_token: 'mock-mobile-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: 'usr-owner-01',
          username: 'owner',
          email: 'owner@love.ai',
          is_active: true,
          is_verified: true,
          is_owner: true,
          created_at: '2026-11-20T00:00:00Z',
        },
      }));
    }

    if (url === '/api/v1/auth/me') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        id: 'usr-owner-01',
        username: 'owner',
        email: 'owner@love.ai',
        is_active: true,
        is_verified: true,
        is_owner: true,
        created_at: '2026-11-20T00:00:00Z',
      }));
    }

    if (url === '/api/v1/intelligence/status') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        active_provider: 'Ollama',
        active_model: 'qwen2.5:7b',
        routing_preference: 'auto',
        local_only_mode: true,
        providers_available: 1,
        total_providers: 3,
      }));
    }

    if (url === '/api/v1/intelligence/conversations') {
      res.writeHead(200);
      return res.end(JSON.stringify([
        {
          id: 'c1',
          user_id: 'usr-owner-01',
          title: 'Native Mobile & Security Vault',
          is_archived: false,
          created_at: '2026-11-20T09:00:00Z',
        },
      ]));
    }

    if (url === '/api/v1/intelligence/conversations/c1') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        id: 'c1',
        user_id: 'usr-owner-01',
        title: 'Native Mobile & Security Vault',
        is_archived: false,
        created_at: '2026-11-20T09:00:00Z',
        messages: [
          {
            id: 'm1',
            conversation_id: 'c1',
            role: 'user',
            content: 'How does LOVE store credentials on mobile devices?',
            created_at: '2026-11-20T09:01:00Z',
          },
          {
            id: 'm2',
            conversation_id: 'c1',
            role: 'assistant',
            content: 'On mobile, LOVE holds short-lived access tokens exclusively in memory (`ApiClient`). Long-lived refresh tokens are stored exclusively in hardware-backed storage (Android Keystore / iOS Keychain). Biometric unlock protects access to the local vault.\n\n```typescript\n// Ephemeral in-memory access token\nprivate accessToken: string | null = null;\n// Native hardware-backed refresh token\nawait mobileSecureStorage.setSecureItem("refresh_token", token);\n```',
            provider: 'Ollama',
            model: 'qwen2.5:7b',
            created_at: '2026-11-20T09:01:05Z',
          },
        ],
      }));
    }

    if (url === '/api/v1/work/approvals') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        approvals: [
          {
            task_id: 'task-102',
            task_title: 'Sovereign Database Backup',
            action: {
              id: 'act-201',
              task_id: 'task-102',
              step_index: 1,
              title: 'Create Verified Encrypted SQLite Backup',
              tool_name: 'database_backup_create',
              risk_level: 'high',
              input: { destination: 'database/backups/love_atomic.db' },
              status: 'awaiting_approval',
              created_at: '2026-11-20T10:00:00Z',
            },
          },
        ],
        total: 1,
      }));
    }

    if (url === '/api/v1/work/tasks') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        tasks: [
          {
            id: 'task-101',
            user_id: 'usr-owner-01',
            title: 'Native Android & iOS Hardening',
            description: 'Verify Keystore security and biometric gating',
            status: 'completed',
            plan: [
              { step: 1, description: 'Verify Android Keystore vault', risk_level: 'low' },
              { step: 2, description: 'Test biometric authentication fallback', risk_level: 'medium' },
            ],
            actions: [],
            total_steps: 2,
            completed_steps: 2,
            created_at: '2026-11-20T08:00:00Z',
          },
        ],
        total: 1,
      }));
    }

    if (url === '/api/v1/memory/suggestions') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        suggestions: [
          {
            id: 'sug-1',
            user_id: 'usr-owner-01',
            category: 'preferences',
            key: 'mobile_ui_theme',
            value: 'Prefers futuristic dark mode with cyan accent lighting',
            importance: 5,
            reason: 'User consistently chooses dark mobile theme',
            status: 'pending',
            created_at: '2026-11-20T09:30:00Z',
          },
        ],
        total: 1,
      }));
    }

    if (url === '/api/v1/memory') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        memories: [
          {
            id: 'mem-1',
            user_id: 'usr-owner-01',
            category: 'core',
            key: 'assistant_identity',
            value: 'LOVE — Sovereign Personal AI Assistant',
            importance: 5,
            tags: ['identity', 'sovereign'],
            created_at: '2026-11-20T07:00:00Z',
          },
          {
            id: 'mem-2',
            user_id: 'usr-owner-01',
            category: 'preferences',
            key: 'primary_development_machine',
            value: 'Windows 11 Workstation with local Android SDK and NVIDIA GPU',
            importance: 4,
            tags: ['hardware', 'environment'],
            created_at: '2026-11-20T07:15:00Z',
          },
        ],
        total: 2,
      }));
    }

    if (url === '/api/v1/system/metrics') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        cpu_percent: 18.2,
        ram: { used_gb: 5.8, total_gb: 16.0, percent: 36.25 },
        gpu: { available: true, name: 'NVIDIA GeForce GTX 1650', vram_used_gb: 1.4, vram_total_gb: 4.0, vram_percent: 35.0, utilization_percent: 22 },
        uptime_seconds: 7200,
        timestamp: new Date().toISOString(),
      }));
    }

    if (url === '/api/v1/system/database/health') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        engine: 'sqlite',
        status: 'healthy',
        latency_ms: 0.6,
        journal_mode: 'wal',
        foreign_keys: true,
        integrity_check: 'ok',
        schema_revision: 'c0e81b379d42',
        database_size_bytes: 1048576,
        table_counts: { users: 1, conversations: 5, messages: 24, memories: 8, tasks: 4 },
      }));
    }

    if (url === '/api/v1/devices') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        devices: [
          {
            id: 'dev-01',
            device_identifier: 'mobile-android-9a8b7c6d',
            device_name: 'LOVE Mobile (Android)',
            device_type: 'android',
            client_version: '1.0.0',
            is_trusted: true,
            is_revoked: false,
            created_at: '2026-11-20T08:00:00Z',
          },
          {
            id: 'dev-02',
            device_identifier: 'desktop-win-4f3e2d1c',
            device_name: 'LOVE Desktop (Windows)',
            device_type: 'windows',
            client_version: '1.0.0',
            is_trusted: true,
            is_revoked: false,
            created_at: '2026-11-20T06:00:00Z',
          },
        ],
        total: 2,
      }));
    }

    if (url === '/api/v1/sync/status') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        sync_enabled: false,
        sync_mode: 'standalone',
        current_cursor: 48,
        total_events: 48,
        active_devices_count: 2,
        server_time: new Date().toISOString(),
      }));
    }

    if (url === '/api/v1/sync/settings') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        sync_enabled: false,
        sync_mode: 'standalone',
        auto_sync_interval_seconds: 60,
        sync_on_change: false,
      }));
    }

    if (url.startsWith('/api/v1/devices/notifications/')) {
      res.writeHead(200);
      return res.end(JSON.stringify({
        enabled: false,
        task_approvals: true,
        task_completions: true,
        security_alerts: true,
      }));
    }

    res.writeHead(200);
    return res.end(JSON.stringify({ success: true }));
  }

  // Static Assets
  let filePath = path.join(distDir, url === '/' ? 'index.html' : url);
  if (!fs.existsSync(filePath)) {
    filePath = path.join(distDir, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = mimeTypes[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      log(`404: ${filePath}`);
      res.writeHead(404);
      return res.end('File not found');
    }

    if (ext === '.html') {
      let html = data.toString('utf-8');
      let injected = `<script>window.__LOVE_API_BASE_URL__ = 'http://127.0.0.1:${PORT}';</script>`;
      if (isAuthenticated) {
        injected += `<script>sessionStorage.setItem('love_sec_vault_refresh_token', 'mock-mobile-refresh-token');</script>`;
      } else {
        injected += `<script>sessionStorage.clear();</script>`;
      }
      html = html.replace('<head>', `<head>${injected}`);
      res.writeHead(200, { 'Content-Type': 'text/html' });
      return res.end(html);
    }

    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  log(`Mobile test server listening on http://127.0.0.1:${PORT}`);
});

app.whenReady().then(async () => {
  log('Electron ready. Creating mobile BrowserWindow (390x844)...');
  const win = new BrowserWindow({
    width: 390,
    height: 844,
    resizable: false,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.webContents.on('did-finish-load', () => {
    log('EVENT: did-finish-load');
  });

  win.webContents.on('did-fail-load', (e, code, desc, validatedUrl) => {
    log(`EVENT: did-fail-load: ${code} ${desc} for ${validatedUrl}`);
  });

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  try {
    // 1. Capture Unauthenticated Mobile Auth Screen
    log('Loading unauthenticated auth page...');
    isAuthenticated = false;
    await win.loadURL(`http://127.0.0.1:${PORT}`);
    log('win.loadURL resolved. Sleeping 1500ms...');
    await sleep(1500);
    let img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotsDir, '01_mobile_auth_screen.png'), img.toPNG());
    log('Captured: 01_mobile_auth_screen.png');

    // 2. Enable authentication and capture Chat Workspace
    log('Loading authenticated session...');
    isAuthenticated = true;
    await win.loadURL(`http://127.0.0.1:${PORT}`);
    log('Auth win.loadURL resolved. Sleeping 2000ms...');
    await sleep(2000);

    img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotsDir, '02_mobile_chat_screen.png'), img.toPNG());
    log('Captured: 02_mobile_chat_screen.png');

    // 3. Navigate to Work Intelligence
    log('Navigating to Work tab...');
    await win.webContents.executeJavaScript(`
      (() => {
        const btn = document.querySelector('button[data-tab="work"]');
        if (btn) btn.click();
      })();
    `);
    await sleep(1200);
    img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotsDir, '03_mobile_work_screen.png'), img.toPNG());
    log('Captured: 03_mobile_work_screen.png');

    // 4. Navigate to Memory
    log('Navigating to Memory tab...');
    await win.webContents.executeJavaScript(`
      (() => {
        const btn = document.querySelector('button[data-tab="memory"]');
        if (btn) btn.click();
      })();
    `);
    await sleep(1200);
    img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotsDir, '04_mobile_memory_screen.png'), img.toPNG());
    log('Captured: 04_mobile_memory_screen.png');

    // 5. Navigate to Telemetry Dashboard
    log('Navigating to Telemetry tab...');
    await win.webContents.executeJavaScript(`
      (() => {
        const btn = document.querySelector('button[data-tab="dashboard"]');
        if (btn) btn.click();
      })();
    `);
    await sleep(1200);
    img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotsDir, '05_mobile_telemetry_screen.png'), img.toPNG());
    log('Captured: 05_mobile_telemetry_screen.png');

    // 6. Navigate to Settings
    log('Navigating to Settings tab...');
    await win.webContents.executeJavaScript(`
      (() => {
        const btn = document.querySelector('button[data-tab="settings"]');
        if (btn) btn.click();
      })();
    `);
    await sleep(1200);
    img = await win.webContents.capturePage();
    fs.writeFileSync(path.join(screenshotsDir, '06_mobile_settings_screen.png'), img.toPNG());
    log('Captured: 06_mobile_settings_screen.png');

    log('All mobile screenshots generated successfully in mobile/screenshots/');
  } catch (err) {
    log('Screenshot capture encountered an error: ' + String(err));
  } finally {
    server.close();
    win.destroy();
    app.quit();
  }
});
