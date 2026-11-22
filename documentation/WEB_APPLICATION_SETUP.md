# LOVE Web Application Setup & Deployment Guide

## 1. Prerequisites

Before running the LOVE Web Application, ensure your environment meets the following baseline requirements:

- **Node.js:** v20.x or higher (Tested and verified on Node.js v24.22.3).
- **npm:** v10.x or higher.
- **Python Backend:** LOVE FastAPI backend running on Python 3.11 with SQLite WAL mode.
- **Modern Web Browser:** Chrome, Chromium, Edge, Safari, or Firefox (supporting ES2022 and Web Audio API).

---

## 2. Quick Start (Development Mode)

### Step 1: Install Dependencies
From the repository root:
```bash
# Navigate to web directory
cd F:\LOVE\web

# Install dependencies (React 19, TypeScript, Vite, Tailwind CSS, Lucide)
npm install
```

### Step 2: Start Backend Server
Ensure the LOVE FastAPI backend is running on `http://127.0.0.1:8000`:
```bash
# From repository root
F:\LOVE\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Step 3: Launch Web Development Server
```bash
# From web/ directory
npm run dev
```
The application will start on **`http://localhost:5174`** with Hot Module Replacement (HMR).

---

## 3. Production Build & Preview

To compile the application for production deployment:

```bash
# Run TypeScript typecheck and Vite build
npm run build
```

This compiles optimized static assets into `web/dist/`:
- `dist/index.html`: Optimized HTML entry point (~1.16 kB).
- `dist/assets/index-[hash].css`: Compiled Tailwind CSS (~32.68 kB / 6.42 kB gzip).
- `dist/assets/index-[hash].js`: Minified TypeScript bundle (~351.16 kB / 97.76 kB gzip).

To preview the production build locally:
```bash
npm run preview
```

---

## 4. Configuration & Environment Variables

### Frontend Environment Configuration (Vite)
The web client is pre-configured with robust sensible defaults. Custom environments can be configured using standard Vite environment files (`.env`, `.env.local`, `.env.production`):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Target URL for the LOVE FastAPI backend |

### Backend Security & Authentication Configuration (`.env`)
The backend provides granular environment variables to configure cookie and CORS security:

| Variable | Default (Dev) | Production Default | Description |
| :--- | :--- | :--- | :--- |
| `COOKIE_SECURE` | `False` | `True` | Enforce HTTPS-only cookie transmission |
| `COOKIE_SAMESITE` | `lax` | `lax` | SameSite cookie policy (`lax`, `strict`, `none`) |
| `COOKIE_DOMAIN` | `None` | `None` (host-only) | Optional domain scope for cookies |
| `COOKIE_PATH` | `/api/v1/auth` | `/api/v1/auth` | Cookie path constraint |
| `CORS_ORIGINS` | `[]` (uses `DEV_CORS_ORIGINS`) | Required list | Explicitly permitted origins for CORS requests |
| `ALLOW_LOCALHOST_IN_PRODUCTION` | `False` | `False` | Strict override required if localhost is permitted in production CORS |

### Runtime Base URL Override
The client also supports dynamic runtime configuration without recompilation:
```javascript
// In browser console or injected bootstrap script:
window.__LOVE_API_BASE_URL__ = 'http://192.168.1.50:8000';
// Or via the ApiClient instance:
window.apiClient.setBaseUrl('http://192.168.1.50:8000');
```
Users can also adjust the backend URL directly via the UI in **Settings Modal -> Device & Backend Settings**.

---

## 5. Reverse Proxy Configuration (Vite & Nginx)

### Vite Development Proxy
In `web/vite.config.ts`, reverse proxying is configured to route `/api` requests seamlessly:
```typescript
server: {
  port: 5174,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false,
    },
  },
}
```

### Production Nginx Reverse Proxy Example
When hosting LOVE behind Nginx on a home server or private network:
```nginx
server {
    listen 80;
    server_name love.local;

    # Static SPA Files
    location / {
        root /var/www/love/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API & SSE Streaming Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for Server-Sent Events (SSE)
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

---

## 6. Running Tests & Verifications

The web application includes a 33-test Vitest test suite covering all services, authentication, chat streaming, approvals, memory, metrics, navigation, and Phase 11.5 security defenses (XSS neutralization, refresh deadlocks, stream cancellation):

```bash
# Run tests once
npm test

# Run tests in watch mode
npm run test:watch

# Capture automated UI screenshots across all 6 views
npm run capture
```

Output screenshots are saved in `web/screenshots/`:
- `01_web_auth_screen.png`: Unauthenticated Login / Registration Screen
- `02_web_chat_workspace.png`: Assistant Chat Workspace with Syntax-highlighted Markdown
- `03_web_command_dashboard.png`: Command Dashboard with CPU/RAM/GPU & SQLite Health
- `04_web_work_approvals.png`: Work Intelligence with Human-in-the-Loop Risk Badges
- `05_web_personal_memory.png`: Personal Episodic Memory & Suggestion Consent Queue
- `06_web_mobile_chat.png`: Responsive Mobile Viewport (375x812)
