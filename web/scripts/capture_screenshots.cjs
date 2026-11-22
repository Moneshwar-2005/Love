/**
 * LOVE Phase 11 — Comprehensive Web Application Screenshot Capture.
 * Uses Electron runtime (Chromium) to render web/dist and capture full-fidelity screenshots.
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

const logFile = path.join(screenshotsDir, 'capture_log.txt');
fs.writeFileSync(logFile, `=== CAPTURE LOG [${new Date().toISOString()}] ===\n`);
function log(msg) {
  console.log(msg);
  fs.appendFileSync(logFile, msg + '\n');
}

log('Starting script. App defined: ' + (typeof app !== 'undefined' && app !== null));
log('Current PID: ' + process.pid);

let isAuthenticated = false;

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];

  // API Mock Handler for Live Web Application Rendering
  if (url.startsWith('/api/v1/')) {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Credentials', 'true');

    if (url === '/api/v1/auth/refresh') {
      if (isAuthenticated) {
        res.writeHead(200);
        return res.end(JSON.stringify({
          access_token: 'mock-web-token-xyz',
          token_type: 'Bearer',
          expires_in: 3600,
        }));
      } else {
        res.writeHead(401);
        return res.end(JSON.stringify({ detail: 'Unauthenticated' }));
      }
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
          title: 'Project Architecture & SQLite WAL',
          is_archived: false,
          created_at: '2026-11-20T09:00:00Z',
        },
        {
          id: 'c2',
          user_id: 'usr-owner-01',
          title: 'FastAPI Backend & React Web Client',
          is_archived: false,
          created_at: '2026-11-20T08:30:00Z',
        },
      ]));
    }

    if (url === '/api/v1/intelligence/conversations/c1') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        id: 'c1',
        user_id: 'usr-owner-01',
        title: 'Project Architecture & SQLite WAL',
        is_archived: false,
        created_at: '2026-11-20T09:00:00Z',
        messages: [
          {
            id: 'm1',
            conversation_id: 'c1',
            role: 'user',
            content: 'How does LOVE maintain data integrity and avoid lock contention during parallel access?',
            created_at: '2026-11-20T09:01:00Z',
          },
          {
            id: 'm2',
            conversation_id: 'c1',
            role: 'assistant',
            content: '### LOVE Relational Database & Concurrency Architecture\n\nLOVE utilizes **hardened SQLite** with **Write-Ahead Logging (WAL)** mode for robust concurrent access.\n\n```python\n# SQLite connection PRAGMA configuration\nPRAGMA journal_mode = WAL;\nPRAGMA busy_timeout = 10000;\nPRAGMA foreign_keys = ON;\nPRAGMA synchronous = NORMAL;\nPRAGMA cache_size = -64000; # 64MB cache\n```\n\nKey architectural pillars:\n- **Concurrent Multi-Reader Support:** Reads never block writes, and writes never block reads under WAL mode.\n- **Atomic Hot Backups:** Verified SQLite Online Backup API (`sqlite3.Connection.backup`) with SHA-256 integrity metadata.\n- **Linear Migrations:** Schema managed via linear Alembic migrations up to head `c0e81b379d42`.',
            provider: 'ollama',
            model: 'qwen2.5:7b',
            latency_ms: 112,
            tokens_completion: 96,
            created_at: '2026-11-20T09:01:03Z',
          },
        ],
      }));
    }

    if (url === '/api/v1/work/approvals') {
      res.writeHead(200);
      return res.end(JSON.stringify([
        {
          task_id: 't1',
          task_title: 'Automated Database Backup',
          action: {
            id: 'act-01',
            task_id: 't1',
            step_index: 0,
            title: 'Create atomic verified database snapshot',
            tool_name: 'sqlite_online_backup',
            risk_level: 'high',
            input: { target_path: 'database/backups/love_backup_now.db' },
            status: 'awaiting_approval',
            approval_state: 'pending',
            created_at: '2026-11-20T09:00:00Z',
          },
        },
      ]));
    }

    if (url === '/api/v1/work/tasks') {
      res.writeHead(200);
      return res.end(JSON.stringify([
        {
          id: 't1',
          user_id: 'usr-owner-01',
          title: 'Automated Database Backup',
          description: 'Take verified hot snapshot of SQLite database using Online Backup API',
          status: 'awaiting_approval',
          plan: [],
          actions: [],
          total_steps: 1,
          completed_steps: 0,
          created_at: '2026-11-20T09:00:00Z',
        },
        {
          id: 't2',
          user_id: 'usr-owner-01',
          title: 'Codebase Static Inspection',
          description: 'Inspect FastAPI routers and SQLAlchemy ORM models',
          status: 'completed',
          plan: [],
          actions: [],
          result_summary: 'All 14 domain models verified with composite indexes.',
          total_steps: 2,
          completed_steps: 2,
          created_at: '2026-11-20T08:00:00Z',
        },
      ]));
    }

    if (url === '/api/v1/memory') {
      res.writeHead(200);
      return res.end(JSON.stringify([
        {
          id: 'mem1',
          user_id: 'usr-owner-01',
          content: 'User prefers concise, clean markdown responses with syntax-highlighted code blocks.',
          category: 'personal',
          tags: ['preference', 'formatting'],
          confidence_score: 1.0,
          source_type: 'direct',
          is_archived: false,
          created_at: '2026-11-20T09:00:00Z',
        },
        {
          id: 'mem2',
          user_id: 'usr-owner-01',
          content: 'Core technology stack consists of FastAPI, SQLAlchemy Async, SQLite WAL, and React 19.',
          category: 'project',
          tags: ['architecture', 'stack'],
          confidence_score: 1.0,
          source_type: 'direct',
          is_archived: false,
          created_at: '2026-11-20T08:00:00Z',
        },
      ]));
    }

    if (url === '/api/v1/memory/suggestions') {
      res.writeHead(200);
      return res.end(JSON.stringify([
        {
          id: 'sug1',
          user_id: 'usr-owner-01',
          content: 'User is developing a universal web client for LOVE using Vite and Tailwind CSS.',
          category: 'project',
          tags: ['web', 'frontend'],
          confidence: 0.96,
          rationale: 'Inferred from active Phase 11 engineering session',
          status: 'pending',
          created_at: '2026-11-20T09:00:00Z',
        },
      ]));
    }

    if (url === '/api/v1/memory/stats') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        total_memories: 14,
        active_memories: 14,
        archived_memories: 0,
        categories_breakdown: { personal: 6, project: 8 },
        vector_store_type: 'local_json',
        vector_index_size: 14,
        embedding_provider: 'deterministic',
        embedding_dimension: 128,
        cloud_embeddings_permitted: false,
      }));
    }

    if (url === '/api/v1/system/metrics') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        cpu_percent: 18.5,
        ram: { used_gb: 4.8, total_gb: 16.0, percent: 30.0 },
        gpu: {
          available: true,
          name: 'NVIDIA GeForce GTX 1650',
          vram_used_gb: 1.1,
          vram_total_gb: 4.0,
          vram_percent: 27.5,
          utilization_percent: 12.0,
        },
        local_model: {
          is_running: true,
          service_name: 'ollama',
          latency_ms: 14.2,
          error: null,
        },
        uptime_seconds: 7200,
        timestamp: '2026-11-20T09:00:00Z',
      }));
    }

    if (url === '/api/v1/system/database') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        engine: 'sqlite',
        status: 'healthy',
        latency_ms: 0.5,
        journal_mode: 'wal',
        foreign_keys: true,
        integrity_check: 'ok',
        schema_revision: 'c0e81b379d42',
        database_size_bytes: 524288,
        table_counts: { users: 1, devices: 1, conversations: 6, messages: 32, memories: 14, tasks: 4, sync_events: 42 },
        last_backup: {
          filename: 'love_backup_20261120_095038.db',
          created_at: '2026-11-20T09:50:38Z',
          size_bytes: 524288,
          is_valid: true,
          total_backups: 2,
        },
      }));
    }

    if (url === '/api/v1/sync/status') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        sync_enabled: false,
        sync_mode: 'standalone',
        current_cursor: 42,
        total_events: 42,
        active_devices_count: 1,
        server_time: '2026-11-20T09:00:00Z',
      }));
    }

    if (url === '/api/v1/sync/settings') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        sync_enabled: false,
        sync_mode: 'standalone',
        auto_sync_interval_seconds: 30,
        conflict_resolution: 'server_wins',
        updated_at: '2026-11-20T09:00:00Z',
      }));
    }

    if (url === '/api/v1/devices') {
      res.writeHead(200);
      return res.end(JSON.stringify([
        {
          id: 'dev-1',
          user_id: 'usr-owner-01',
          device_identifier: 'web-session-client-01',
          device_name: 'LOVE Web Client (Chrome)',
          device_type: 'web',
          is_trusted: true,
          is_revoked: false,
          created_at: '2026-11-20T09:00:00Z',
        },
      ]));
    }

    if (url === '/api/v1/system/activity') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        items: [
          {
            id: 'act-1',
            event_type: 'conversation_created',
            title: 'Project Architecture & SQLite WAL',
            description: 'Started chat turn with Qwen 2.5 7B',
            category: 'intelligence',
            timestamp: '2026-11-20T09:00:00Z',
            metadata: {},
          },
          {
            id: 'act-2',
            event_type: 'action_awaiting_approval',
            title: 'Automated Database Backup',
            description: 'Tool action requires Human-in-the-Loop authorization',
            category: 'work',
            timestamp: '2026-11-20T08:50:00Z',
            metadata: {},
          },
          {
            id: 'act-3',
            event_type: 'memory_saved',
            title: 'Personal Memory Saved',
            description: 'Saved formatting preference memory',
            category: 'memory',
            timestamp: '2026-11-20T08:40:00Z',
            metadata: {},
          },
        ],
        total: 3,
      }));
    }

    if (url === '/api/v1/voice/status') {
      res.writeHead(200);
      return res.end(JSON.stringify({
        is_enabled: true,
        local_only_mode: true,
        stt: { active_provider: 'whisper', name: 'Whisper Local', is_local: true, is_configured: true, is_available: true },
        tts: { active_provider: 'piper', name: 'Piper Neural TTS', is_local: true, is_configured: true, is_available: true },
        wake_word: { active: false, model_name: 'hey_love', threshold: 0.5, model_available: false, mic_permission_granted: false, message: 'Acoustic model not installed' },
        personality: { profile_id: 'default', name: 'LOVE Core', preferred_accent: 'British RP', style_description: 'Calm, articulate, efficient' },
      }));
    }

    res.writeHead(200);
    return res.end(JSON.stringify({ status: 'ok' }));
  }

  // Static Assets
  let reqPath = url;
  if (reqPath === '/' || reqPath === '/index.html') {
    let html = fs.readFileSync(path.join(distDir, 'index.html'), 'utf-8');
    html = html.replace('<head>', `<head><script>window.__LOVE_API_BASE_URL__ = 'http://127.0.0.1:${PORT}';</script>`);
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(html);
  }

  const filePath = path.join(distDir, reqPath);
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
    fs.createReadStream(filePath).pipe(res);
  } else {
    let html = fs.readFileSync(path.join(distDir, 'index.html'), 'utf-8');
    html = html.replace('<head>', `<head><script>window.__LOVE_API_BASE_URL__ = 'http://127.0.0.1:${PORT}';</script>`);
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(html);
  }
});

const PORT = 4188;

server.on('error', (err) => {
  log('Server error: ' + err.message);
});

server.listen(PORT, () => {
  log(`Web application test server listening on http://127.0.0.1:${PORT}`);
});

log('Registering app.whenReady handler...');
app.whenReady().then(async () => {
  log('app.whenReady resolved!');
  try {
    const win = new BrowserWindow({
      width: 1280,
      height: 800,
      show: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
      },
    });

    win.webContents.on('console-message', (_e, level, message) => {
      log(`[Renderer] ${message}`);
    });

      // 1. Capture Unauthenticated Auth Screen
      isAuthenticated = false;
      await win.loadURL(`http://127.0.0.1:${PORT}`);
      await new Promise((r) => setTimeout(r, 1200));

      const authImg = await win.capturePage();
      fs.writeFileSync(path.join(screenshotsDir, '01_web_auth_screen.png'), authImg.toPNG());
      log('Captured: 01_web_auth_screen.png');

      // 2. Enable Authentication and Capture Assistant Chat
      isAuthenticated = true;
      await win.loadURL(`http://127.0.0.1:${PORT}`);
      await new Promise((r) => setTimeout(r, 1500));

      const chatImg = await win.capturePage();
      fs.writeFileSync(path.join(screenshotsDir, '02_web_chat_workspace.png'), chatImg.toPNG());
      log('Captured: 02_web_chat_workspace.png');

      // 3. Navigate to Dashboard View
      await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const dashBtn = buttons.find(b => b.textContent && b.textContent.includes('Dashboard'));
          if (dashBtn) dashBtn.click();
        })()
      `);
      await new Promise((r) => setTimeout(r, 1200));

      const dashImg = await win.capturePage();
      fs.writeFileSync(path.join(screenshotsDir, '03_web_command_dashboard.png'), dashImg.toPNG());
      log('Captured: 03_web_command_dashboard.png');

      // 4. Navigate to Work Intelligence View
      await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const workBtn = buttons.find(b => b.textContent && b.textContent.includes('Work Intelligence'));
          if (workBtn) workBtn.click();
        })()
      `);
      await new Promise((r) => setTimeout(r, 1200));

      const workImg = await win.capturePage();
      fs.writeFileSync(path.join(screenshotsDir, '04_web_work_approvals.png'), workImg.toPNG());
      log('Captured: 04_web_work_approvals.png');

      // 5. Navigate to Personal Memory View
      await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const memBtn = buttons.find(b => b.textContent && b.textContent.includes('Personal Memory'));
          if (memBtn) memBtn.click();
        })()
      `);
      await new Promise((r) => setTimeout(r, 1200));

      const memImg = await win.capturePage();
      fs.writeFileSync(path.join(screenshotsDir, '05_web_personal_memory.png'), memImg.toPNG());
      log('Captured: 05_web_personal_memory.png');

      // 6. Responsive Mobile View (Viewport 375x812)
      win.setSize(375, 812);
      await win.webContents.executeJavaScript(`
        (() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const chatBtn = buttons.find(b => b.textContent && b.textContent.includes('Assistant Chat'));
          if (chatBtn) chatBtn.click();
        })()
      `);
      await new Promise((r) => setTimeout(r, 1200));

      const mobileImg = await win.capturePage();
      fs.writeFileSync(path.join(screenshotsDir, '06_web_mobile_chat.png'), mobileImg.toPNG());
      log('Captured: 06_web_mobile_chat.png');

      win.close();
      log('All screenshots successfully generated in web/screenshots/');
    } catch (err) {
      log('Error during screenshot capture: ' + String(err));
    } finally {
      server.close();
      app.quit();
    }
});
