# LOVE Web Security & Browser Threat Modeling Specification

## 1. Executive Summary

Browser-based web clients operate within an untrusted execution environment vulnerable to cross-site scripting (XSS), cross-site request forgery (CSRF), session hijacking, and man-in-the-middle interception.

Because LOVE handles sovereign personal memories, active task orchestration, and system-level actions, the web application implements defense-in-depth security principles matching enterprise standards without compromising local standalone performance.

---

## 2. Threat Modeling & Mitigation Matrix

| Threat | Risk Level | Target | Defense Mechanism Implemented |
| :--- | :--- | :--- | :--- |
| **XSS Token Exfiltration** | **CRITICAL** | Long-lived refresh tokens | **HttpOnly Cookies:** Refresh tokens are never stored in browser `localStorage`, `sessionStorage`, or JavaScript scope. They are stored in an `HttpOnly`, `SameSite=Lax` cookie unreadable by any client-side JavaScript. |
| **In-Memory Access Token Stealing** | **HIGH** | Active access token | **Short TTL & Ephemeral Memory:** Access tokens live solely in private class memory (`ApiClient`). Tokens expire after 60 minutes and are completely wiped on tab closure or logout. |
| **Cross-Site Request Forgery (CSRF)** | **HIGH** | Mutation endpoints (`POST`, `DELETE`) | **Dual Token Architecture + SameSite:** All data-altering requests require `Authorization: Bearer <token>` in the HTTP header (browsers never attach custom headers to cross-site form submissions). Refresh requests use `SameSite=Lax`. |
| **Unauthorized Action Execution** | **CRITICAL** | Task Actions & System Tools | **Human-in-the-Loop (HITL) Enforcement:** High-risk actions cannot execute automatically. The backend requires explicit approval records signed by an authenticated user session. |
| **Memory Extraction without Consent** | **MEDIUM** | Inferred Personal Knowledge | **Explicit Consent Queue:** Background memory suggestions remain in a `pending` state until the user actively clicks "Approve" in the web UI. |
| **Brute Force & Credential Stuffing** | **HIGH** | Login Endpoint | **Argon2id Hashing & Account Lockout:** Backend enforces Argon2id password hashing and locks accounts after repeated failed attempts. |
| **Microphone Snooping** | **MEDIUM** | User Audio | **Permission-Gated Push-to-Talk:** No passive background microphone listening. User must explicitly hold the record button; audio streams close immediately on release. |

---

## 3. Token Lifecycle & Authentication Architecture

### In-Memory vs. HttpOnly Cookie Separation
Unlike naive web applications that store JWT refresh tokens in `localStorage` (making them vulnerable to any third-party script injection or malicious browser extension), LOVE adopts a hardened hybrid model:

1. **Access Token (Short-Lived):**
   - Transmitted via standard JSON payload upon `/login` or `/refresh`.
   - Stored in a private JavaScript class property (`ApiClient.accessToken`).
   - Passed via `Authorization: Bearer <token>` header.
   - Cleared immediately on browser refresh, logout, or session expiry.
2. **Refresh Token (Long-Lived, Persistent):**
   - Transmitted via standard Set-Cookie response header:
     ```http
     Set-Cookie: love_refresh_token=<token>; HttpOnly; SameSite=Lax; Path=/api/v1/auth; Max-Age=2592000
     ```
   - Inaccessible to `document.cookie`, `eval()`, or any renderer script.
   - Handled transparently by the browser network stack when making requests to `/api/v1/auth/refresh` or `/api/v1/auth/logout`.

### Non-Blocking Refresh Interceptor
When an in-flight API request encounters an expired access token (`401 Unauthorized`):
1. `ApiClient` intercepts the 401 error before returning to the caller.
2. The failing request is queued into an internal subscriber array.
3. If no refresh is currently pending, `ApiClient` triggers a single `/refresh` request with `credentials: 'include'`.
4. The entire refresh operation is encapsulated in a `try...finally` block to guarantee `isRefreshing = false` is always reset, preventing client promise deadlocks under network failure.
5. Upon successful refresh:
   - The new access token is stored in memory.
   - All queued requests are replayed with the new token.
6. If the refresh request itself fails (e.g., revoked session or invalid cookie):
   - The backend explicitly attaches a `Set-Cookie: love_refresh_token=; Max-Age=0` header matching the exact `Path`, `Domain`, `SameSite`, and `Secure` attributes, actively clearing the dead cookie in the browser.
   - In-memory state is wiped.
   - `onUnauthorizedCallback` triggers an automatic redirect to `AuthScreen`.

### RFC 6265bis Cookie Attribute Matching on Deletion
Under RFC 6265bis, browsers will ignore a cookie deletion request unless the `Path`, `Domain`, and `Secure` flags match those provided when the cookie was set. LOVE's `/logout` and failed `/refresh` responses strictly echo matching parameters:
- `Path`: `/api/v1/auth` (configurable via `COOKIE_PATH`)
- `SameSite`: `lax` (configurable via `COOKIE_SAMESITE`)
- `Secure`: `True` in production, `False` in dev/test (configurable via `COOKIE_SECURE`)
- `HttpOnly`: `True`

---

## 4. Input Sanitization & Content Security

### XSS Prevention in Markdown & Code Rendering
LOVE displays rich AI responses containing markdown tables, lists, and formatted code blocks.
- **Renderer Implementation:** Handled via `MarkdownRenderer.tsx`.
- **Parsing Strategy:** Uses a token-based AST parser that generates typed React JSX elements (`React.createElement` / virtual DOM nodes).
- **Prohibited Patterns:** No use of `dangerouslySetInnerHTML`, `innerHTML`, or unsafe regex replacements that output raw HTML strings.
- **Code Block Safety:** Code snippets are rendered inside `<pre><code>` elements where all special characters (`<`, `>`, `&`, `"`) are automatically HTML-escaped by React.
- **URI Scheme Whitelisting:** Markdown links (`[label](url)`) are strictly validated against a permitted scheme whitelist (`http:`, `https:`, `mailto:`, relative `/`, `#`). Dangerous URI schemes—such as `javascript:`, `data:`, or `vbscript:`—are neutralized and rendered as inert warning text (`[label (unsafe-link-blocked)]`).
- **Tab Hijacking Defense:** All external links are rendered with `target="_blank"` and `rel="noopener noreferrer"`.

### Safe Copy-to-Clipboard
Message and code copying uses the standard `navigator.clipboard.writeText()` API with graceful fallback to `document.execCommand('copy')` wrapped in a localized scope.

---

## 5. Network & Cross-Origin Resource Sharing (CORS) & CSRF Defense

### Strict Origin Whitelisting
The FastAPI backend (`backend/app/config/settings.py`) implements environment-segregated CORS origins:
- **Development/Testing:** `DEV_CORS_ORIGINS` automatically permits localhost ports (`5174`, `5173`, `3000`, `8080`) and `tauri://localhost`.
- **Production:** Requires explicit, validated domains via `CORS_ORIGINS`. Wildcards (`*`) with credentials are completely forbidden, and localhost origins are prohibited unless `ALLOW_LOCALHOST_IN_PRODUCTION=True` is explicitly specified.

### Cookie-Authenticated Request CSRF Defense
Because all standard data endpoints require `Authorization: Bearer <token>`, cross-origin forms and scripts cannot perform CSRF against conversation, task, or memory endpoints.
For cookie-authenticated endpoints (`/api/v1/auth/refresh` and `/api/v1/auth/logout`), the backend performs strict `Origin` and `Referer` validation against the active CORS whitelist (`validate_cookie_request_origin`). Any cross-site submission from an unauthorized origin is immediately rejected with HTTP `403 Forbidden`. Requests passing tokens directly in request bodies (Desktop and CLI) bypass this check.

---

## 6. Hardware & Device Identity Management

When a user logs in from a web browser, the client submits a persistent client device identifier generated on first launch:
```json
{
  "device_identifier": "web-client-[UUID]",
  "device_name": "LOVE Web Client (Browser)",
  "device_type": "web"
}
```
This device is registered in the SQLite `devices` table, enabling the owner to:
- Inspect active browser sessions from the Command Dashboard or Settings Modal.
- Revoke compromised browser sessions remotely from the Desktop or Web interface.
- Audit synchronization events associated specifically with the web client.

---

## 7. SSE Stream Cancellation Security & State Integrity

When streaming assistant responses via Server-Sent Events (`fetchStream()` in `intelligenceService.ts`):
1. **Explicit Cancellation Lifecycle:** If the user clicks "Stop Generating", an `AbortController` signal is triggered, immediately aborting the underlying HTTP stream.
2. **Distinct Completion Boundary:** Truncated responses trigger a dedicated `onCancel(accumulated)` callback rather than `onDone()`. This ensures incomplete responses are visually flagged (`*[Generation stopped by user]*`), preventing partial output from being falsely logged as a complete turn.
3. **Information Disclosure Prevention:** Stream parsing error logs redact raw chunk content and log chunk byte lengths instead, preventing sensitive payload leakage in browser console traces.
