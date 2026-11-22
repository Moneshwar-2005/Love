# LOVE Desktop Application Architecture (Phase 07)

## 1. Overview & Vision

The LOVE Desktop Application is the primary native interface for the LOVE sovereign personal AI assistant. It provides a unified, responsive, and visually modern operating interface for conversational intelligence, automated work tasks, human-in-the-loop approvals, persistent personal memory, and voice interaction.

LOVE is engineered to function as an integrated, single-identity personal assistant rather than a disconnected bundle of disparate chatbots or utilities. The desktop application connects directly to LOVE's authenticated FastAPI backend (`http://127.0.0.1:8000`) over secure HTTP and Server-Sent Events (SSE).

### Framework Decision & Rationale

- **Framework Choice:** React 19 + TypeScript 7 + Vite 8 + Tailwind CSS 3.4 + Electron 45.
- **Tauri 2 Compatibility Assessment:**
  - *Host Environment Status:* Rust compiler (`rustc`) and Cargo are not installed on the host system.
  - *Decision:* Electron was selected for native Windows packaging, window management, and native DPAPI encrypted credential storage (`safeStorage`).
  - *Portability Guarantee:* The entire frontend code (`desktop/src/`) is written in standard modular React and TypeScript with zero proprietary Electron coupling in UI components. All desktop-native functions are mediated through a clean `LoveDesktopAPI` interface (`storageAdapter.ts`, `windowControls`), allowing immediate drop-in portability to Tauri 2 whenever the Rust compiler toolchain is installed in a future environment.

---

## 2. Directory Structure

```
desktop/
├── electron/
│   ├── main.cjs                   # Electron main process (window creation, secure vault IPC, CSP)
│   └── preload.cjs                # ContextBridge exposing window.loveDesktop safely
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   └── AuthScreen.tsx     # Cyber/dark glass login and owner setup form
│   │   ├── chat/
│   │   │   ├── ChatWorkspace.tsx  # Central chat container with SSE streaming lifecycle
│   │   │   ├── Composer.tsx       # Auto-expanding multiline prompt composer & voice toggle
│   │   │   ├── MarkdownRenderer.tsx # Highlighting, code blocks with copy button, lists, formatting
│   │   │   ├── MessageItem.tsx    # User and assistant message bubbles with token/latency badges
│   │   │   └── MessageList.tsx    # Auto-scrolling conversation history and prompt starters
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx      # Top-level application shell with auth guards & modals
│   │   │   ├── Header.tsx         # Brand identity, assistant status pill, model routing badge
│   │   │   ├── Sidebar.tsx        # Navigation tabs, conversation list, settings, logout
│   │   │   └── StatusBadge.tsx    # Reusable assistant state indicator (idle, thinking, etc.)
│   │   ├── memory/
│   │   │   ├── MemoryWorkspace.tsx # Memory management, semantic vector search, category filters
│   │   │   └── SuggestionCard.tsx  # Discovered memory suggestion card with approve/reject actions
│   │   ├── settings/
│   │   │   └── SettingsModal.tsx  # Backend API URL config, connection diagnostics, session details
│   │   ├── status/
│   │   │   └── SystemStatusModal.tsx # Hardware profile (GTX 1650 4GB VRAM), provider status, models
│   │   ├── voice/
│   │   │   ├── AudioRecorder.tsx  # Web Audio API microphone capture with animated visualizer
│   │   │   └── VoiceWorkspace.tsx # Voice turn manager, TTS audio playback, wake-word toggle
│   │   └── work/
│   │       ├── ApprovalQueue.tsx  # Human-in-the-Loop pending action authorization queue
│   │       ├── TaskDetailModal.tsx # Step-by-step plan execution inspection, inputs/outputs
│   │       └── WorkWorkspace.tsx  # Work Intelligence dashboard, task filters, task launcher
│   ├── context/
│   │   ├── AppContext.tsx         # Global assistant state, current view, pending alerts
│   │   └── AuthContext.tsx        # User identity, authentication status, login/logout
│   ├── services/
│   │   ├── apiClient.ts           # Fetch client with auto JWT injection and 401 token refresh
│   │   ├── authService.ts         # User authentication, token lifecycle, and session store
│   │   ├── intelligenceService.ts # Chat CRUD and Server-Sent Events (SSE) stream parser
│   │   ├── memoryService.ts       # Canonical memories and consent suggestion APIs
│   │   ├── storageAdapter.ts      # Native DPAPI encrypted token store / session vault
│   │   ├── voiceService.ts        # STT, TTS, voice chat turn, and wake-word APIs
│   │   └── workService.ts         # Task creation, execution, tool discovery, and approvals
│   ├── test/
│   │   ├── apiClient.test.ts      # Tests for request headers, 401 auto-refresh, network failure
│   │   ├── authService.test.ts    # Tests for login, token storage, logout, session verification
│   │   ├── components.test.tsx    # Tests for StatusBadge, MessageItem, ApprovalQueue UI
│   │   ├── intelligenceService.test.ts # Tests for conversation CRUD and SSE stream decoding
│   │   ├── memoryService.test.ts  # Tests for memory listing, suggestions approve/reject
│   │   ├── setup.ts               # Test mocks for window.loveDesktop, Audio, scrollIntoView
│   │   ├── voiceService.test.ts   # Tests for voice turn upload and wake-word toggle
│   │   └── workService.test.ts    # Tests for task creation, listing, action approval
│   ├── types/
│   │   ├── auth.ts                # TypeScript interfaces for auth credentials and user models
│   │   ├── desktop.ts             # Global declarations for window.loveDesktop IPC APIs
│   │   ├── intelligence.ts        # Types for conversations, messages, SSE chunks, models
│   │   ├── memory.ts              # Types for memories, categories, suggestions, search
│   │   ├── voice.ts               # Types for voice sessions, turns, wake-word status
│   │   └── work.ts                # Types for tasks, actions, tools, risk levels, approvals
│   ├── App.tsx                    # Root application component with nested context providers
│   ├── index.css                  # Tailwind styles and custom dark theme scrollbars
│   ├── main.tsx                   # React DOM entry point
│   └── vite-env.d.ts              # Vite client types reference
├── index.html                     # HTML root template with strict Content Security Policy
├── package.json                   # Dependencies, build scripts, vitest test runner
├── postcss.config.js              # PostCSS configuration for Tailwind CSS
├── tailwind.config.js             # Theme color definitions, fonts, and glowing animations
├── tsconfig.json                  # TypeScript compiler options
└── vite.config.ts                 # Vite bundler and Vitest test runner configuration
```

---

## 3. Subsystem Architecture & Integrations

### 3.1 Authentication & Encrypted Token Vault
- **No Plaintext `localStorage`:** Tokens are never persisted in plaintext browser `localStorage`.
- **Desktop Storage Adapter:** In Electron desktop mode, credentials are encrypted using Windows DPAPI via Electron's `safeStorage.encryptString()` and stored in `love_vault.dat` in the user's protected app data directory.
- **Automatic Token Refresh (401 Interceptor):** `apiClient.ts` intercepts HTTP 401 unauthorized responses, pauses queued requests, calls `/api/v1/auth/refresh` using the stored refresh token, updates the access token in the secure vault, and transparently replays the original request.

### 3.2 Universal Intelligence & SSE Streaming
- **Conversations & Message Threads:** Supports multi-conversation management with creation, deletion, and thread selection in the sidebar.
- **Server-Sent Events (SSE) Protocol:**
  - Streams tokens in real-time from `/api/v1/intelligence/chat/stream`.
  - Parsed by `intelligenceService.streamMessage()`: decodes `data: {"delta": "...", "is_done": false}` lines and accumulates text.
  - Automatically handles user cancellation via `AbortController`.
- **Markdown & Syntax Highlighting:** Custom lightweight `MarkdownRenderer` renders headers, lists, bold/italics, and fenced code blocks with language headers and copy-to-clipboard functionality.

### 3.3 Assistant Identity & State Indicators
The assistant state is continuously synchronized in the header via `StatusBadge.tsx`:
- `idle`: "Ready" (emerald indicator)
- `thinking`: "Thinking..." (cyan pulsing indicator)
- `responding`: "Generating" (indigo pulsing indicator)
- `listening`: "Listening" (amber pulsing indicator)
- `speaking`: "Speaking" (purple pulsing indicator)
- `awaiting_approval`: "Awaiting Approval" (rose warning indicator)
- `offline`: "Backend Offline" (slate indicator)

### 3.4 Work Intelligence & Human-in-the-Loop Approvals
- **Approval Queue:** High-priority visual queue rendered prominently when tool executions require user confirmation.
- **Risk Tiers:** Actions are classified into `low`, `medium`, `high`, and `critical` risk tiers.
- **Authorization Controls:** Provides one-click "Authorize & Run" (resumes task execution automatically) and "Reject" (aborts action without executing).
- **Execution Inspection:** `TaskDetailModal` provides an audited step-by-step timeline of input parameters, generated outputs, execution latency, and error states.

### 3.5 Persistent Personal Memory Management
- **Canonical Storage:** Displays permanent user memories with category tags (`preference`, `project`, `knowledge`, etc.) and creation dates.
- **Semantic Vector Search:** Integrates with `/api/v1/memory/search` to retrieve relevant memories by natural language query.
- **Consent Workflow:** Extracted suggestions are held in a pending consent queue until the user explicitly selects "Save Memory" (promoting to permanent vector-indexed storage) or "Reject".

### 3.6 Voice Engine & Speech Interface
- **Audio Capture:** `AudioRecorder` uses browser `MediaRecorder` API to record audio utterances and displays an active pulse animation.
- **End-to-End Turn:** Transmits audio blobs to `POST /api/v1/voice/chat`, receiving the transcribed user speech, assistant response, and synthesized TTS audio base64.
- **Audio Playback:** Automatically plays back the synthesized response using HTML5 `Audio`.
- **Wake Word Control:** Interactive toggle for "Hey LOVE" continuous monitoring with microphone permission status.

### 3.7 System Routing & Hardware Status
- **Hardware Profile:** Surfaces NVIDIA GeForce GTX 1650 4GB VRAM allocation, CUDA availability, and local-only mode enforcement.
- **Provider Discovery:** Real-time online/offline status and latency metrics for Ollama (local) and Gemini (cloud).

---

## 4. Security Architecture

1. **Content Security Policy (CSP):** Enforced in both `index.html` and Electron session headers:
   - Restricts connections strictly to `http://localhost:8000`, `http://127.0.0.1:8000`, `ws://localhost:8000`.
   - Disallows unauthorized remote script evaluation.
2. **Context Isolation & Sandboxing:** Electron BrowserWindow is configured with:
   - `nodeIntegration: false`
   - `contextIsolation: true`
   - `sandbox: true`
   - `webSecurity: true`
3. **Owner Authorization:** Desktop application honors role hierarchies; secondary registration requires Owner setup token when closed registration is enabled.
4. **Navigation & Window Controls:**
   - Popups blocked via `setWindowOpenHandler` ({ action: 'deny' }).
   - External navigation intercepted and blocked via `will-navigate`.
5. **Windows DPAPI Native Encryption:**
   - Secure token storage uses `safeStorage.encryptString()` / `safeStorage.decryptString()`.
   - Rejects unencrypted fallback if DPAPI is unavailable (zero plaintext leaks to disk).
   - Validated: 126-byte binary encrypted buffer on disk contains zero plaintext tokens.

---

## 5. Phase 07.5 Runtime Verification & Hardening

Phase 07.5 verified the desktop application in a live Windows environment against the running FastAPI backend and SQLite database:

| Component | Status | Verification Detail |
| :--- | :--- | :--- |
| **Electron Runtime** | `LIVE VERIFIED` | Launched via native `electron.exe`; confirmed `BrowserWindow` creation, preload bridge injection, and clean window lifecycle. |
| **Windows DPAPI Vault** | `LIVE VERIFIED` | Full lifecycle tested: write, raw disk inspection (zero plaintext), read/decrypt roundtrip, and secure deletion. |
| **Preload Isolation** | `LIVE VERIFIED` | `window.loveDesktop` exposed cleanly; renderer attempts to access `require`, `process`, or `fs` are confirmed blocked. |
| **Live Backend API** | `LIVE VERIFIED` | Full suite tested against `database/love.db` and `http://127.0.0.1:8000`: login, refresh, profile, SSE streaming, stream cancellation, memory CRUD/vector search, work task lifecycle, and voice status. |
| **Voice Honesty** | `LIVE VERIFIED` | Missing `hey_love.onnx` prevents wake-word activation and shows explicit warning; STT/TTS mock providers accurately labeled. |
| **Desktop Tests** | `LIVE VERIFIED` | 20/20 Vitest tests passed across 7 test suites. |
| **Backend Tests** | `LIVE VERIFIED` | 177/177 Pytest tests passed with 0 regressions. |
| **Windows Packaging** | `NOT CONFIGURED` | Standalone installer generation is not yet configured in `package.json` (`electron-builder` not installed). |

