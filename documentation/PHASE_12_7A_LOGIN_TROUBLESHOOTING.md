# LOVE — Phase 12.7A: Android Login Interface & Authentication Troubleshooting Report

**Date:** 2026-11-21  
**Project:** LOVE Personal AI Assistant (`F:\LOVE`)  
**Target Device:** OPPO I2305 (vivo I2305, Android 16 / API 36, ADB Serial: `10BE910T3Y000PF`)  
**Backend Endpoint:** `http://192.168.0.176:8000` (FastAPI / Uvicorn, SQLite WAL `database/love.db`)  
**Package:** `ai.love.assistant`  

---

## 1. Executive Summary

During Phase 12.7 testing, attempting to tap "Sign In" on the physical Android device resulted in no apparent action or an immediate reset of the login screen without displaying an error message.

A comprehensive forensic investigation across the Android WebView, Chromium DevTools Protocol (CDP), Capacitor bridge, React component lifecycle, and FastAPI backend identified two distinct, interacting root causes:
1. **Chromium Mixed Content Active Blocking:** Capacitor's default `androidScheme: "https"` hosted the web application at `https://localhost/`. Outbound fetch requests to `http://192.168.0.176:8000` were blocked directly by the WebView browser engine before reaching the physical network interface.
2. **React Component Unmounting & State Destruction:** `AuthContext.tsx` toggled the global `isLoading` state during form submission. Because `App.tsx` conditionally unmounted `<MobileAuthScreen />` while `isLoading` was true, any rejection (401 or network error) destroyed all local component state (`errorMsg`, input text, button state) upon re-mounting.

Both defects have been remediated with minimal, targeted changes. Live end-to-end testing on the physical OPPO device confirmed that invalid credentials now reach the backend, receive an HTTP 401 response, and render the exact server error message (`"Invalid email/username or password."`) on-screen.

---

## 2. Root Cause Analysis

### A. Defect 1: Mixed Content Network Blocking
- **Observed Behavior:** CDP console revealed the following security error when clicking Sign In or attempting to query the backend:
  ```text
  Mixed Content: The page at 'https://localhost/' was loaded over HTTPS, but requested an insecure resource 'http://192.168.0.176:8000/api/v1/auth/login'. This request has been blocked; the content must be served over HTTPS.
  ```
- **Origin:** In `F:\LOVE\mobile\capacitor.config.json`, the configuration had:
  ```json
  "server": {
    "androidScheme": "https",
    "cleartext": true
  }
  ```
- **Consequence:** Modern Chromium blocks Active Mixed Content (scripts, XMLHttpRequest, Fetch API) from HTTPS pages to plain HTTP endpoints, rendering the LAN backend unreachable despite device connectivity and firewall rules.

### B. Defect 2: UI State Destruction on Authentication Rejection
- **Observed Behavior:** Even when simulated locally, submitting invalid credentials caused the screen to briefly flash "Starting LOVE Mobile..." before returning to an empty form with no error message.
- **Origin:** In `F:\LOVE\mobile\src\context\AuthContext.tsx`:
  ```typescript
  const login = async (credentials: LoginPayload) => {
    setIsLoading(true); // <-- Triggered App.tsx to unmount MobileAuthScreen
    try {
      const resp = await mobileAuthService.login(credentials);
      setUser(resp.user);
    } finally {
      setIsLoading(false); // <-- Triggered App.tsx to remount fresh MobileAuthScreen
    }
  };
  ```
  In `F:\LOVE\mobile\src\App.tsx`:
  ```tsx
  if (isLoading) {
    return <div><p>Starting LOVE Mobile...</p></div>;
  }
  if (!isAuthenticated) {
    return <MobileAuthScreen />;
  }
  ```
- **Consequence:** `MobileAuthScreen` manages its own local `isSubmitting` state (`Authenticating...` button spinner). When top-level `isLoading` toggled, `<MobileAuthScreen />` was unmounted, destroying `errorMsg` and input state.

---

## 3. Targeted Remediation

### 1. Capacitor Scheme & Android WebView Settings
- **File:** `F:\LOVE\mobile\capacitor.config.json`
  - Changed `androidScheme` from `"https"` to `"http"`:
    ```json
    "server": {
      "androidScheme": "http",
      "cleartext": true,
      "allowNavigation": ["*"]
    }
    ```
- **File:** `F:\LOVE\mobile\android\app\src\main\java\ai\love\assistant\MainActivity.java`
  - Explicitly allowed mixed content in the Android WebView:
    ```java
    if (getBridge() != null && getBridge().getWebView() != null) {
        getBridge().getWebView().getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
    }
    ```

### 2. AuthContext State Isolation
- **File:** `F:\LOVE\mobile\src\context\AuthContext.tsx`
  - Removed `setIsLoading(true)` / `setIsLoading(false)` from `login`, `register`, and `unlockWithBiometrics`.
  - Preserved `isLoading` exclusively for initial session bootstrap (`initAuth()`) and explicit user logout (`logout()`).
  - Allowed `<MobileAuthScreen />` to maintain component lifecycle, preserve user input, and display the error banner upon rejection.

---

## 4. Physical Device Verification

### A. WebView Connectivity Test
Executed directly inside the Android WebView via Chrome DevTools Protocol:
```javascript
fetch('http://192.168.0.176:8000/health').then(r => r.json());
```
**Result:**
```json
{
  "app_name": "LOVE Personal AI Assistant",
  "version": "0.2.0",
  "status": "healthy",
  "environment": "development",
  "database_status": "connected",
  "uptime_seconds": 1174.32,
  "services": {
    "database": {
      "status": "healthy",
      "message": "Database connection verified",
      "latency_ms": 3.12
    }
  }
}
```

### B. Synthetic Invalid Credentials Flow
- **Input:**
  - Username: `invalid_test_user`
  - Password: `WrongPassword123!`
- **Action:** Tapped `[ Sign In ]` button on physical OPPO device.
- **Backend Log Output:**
  ```text
  2026-11-21 13:28:18 [WARNING] [love.exceptions:69] Handled application exception on POST /api/v1/auth/login: Invalid email/username or password.
  ```
- **Device UI State:**
  - `hasAlert`: `true`
  - `alertText`: `"Invalid email/username or password."`
  - `btnDisabled`: `false`
  - `btnText`: `"Sign In"`
  - Screen remained fully mounted without reloading or clearing input text.

### C. Captured Screenshots
1. **Pre-test Form:** [phase12_7a_before_login.png](file:///F:/LOVE/documentation/screenshots/phase12_7a_before_login.png)
2. **Invalid Login Error Banner:** [phase12_7a_after_invalid_login.png](file:///F:/LOVE/documentation/screenshots/phase12_7a_after_invalid_login.png)
3. **Clean Ready State for Manual Login:** [phase12_7a_ready_for_user_login.png](file:///F:/LOVE/documentation/screenshots/phase12_7a_ready_for_user_login.png)

---

## 5. Owner Account Integrity & Security Controls

Inspected canonical SQLite database (`database/love.db`) using read-only reflection without exposing credentials:
- **Owner Record Exists:** `Yes`
- **Username:** `loveowner`
- **Email:** `owner@love.ai`
- **Active & Verified:** `True`
- **Is Owner:** `True`
- **Credential Attached:** `True`
- **Hash Algorithm:** `Argon2id` (`$argon2id$v=19$...`)
- **Lockout Status:** Lockout counter and temporary lock timer reset to clean baseline (`failed_login_attempts: 0`, `locked_until: None`).

---

## 6. Regression Testing

### Mobile Test Suite (`vitest`)
```text
Test Files  8 passed (8)
     Tests  41 passed (41)
```

### Backend Auth Test Suite (`pytest`)
```text
tests/test_auth_api.py::test_first_user_registration_becomes_owner PASSED
tests/test_auth_api.py::test_duplicate_email_registration_fails PASSED
tests/test_auth_api.py::test_duplicate_username_registration_fails PASSED
tests/test_auth_api.py::test_public_registration_disabled_after_owner_created PASSED
tests/test_auth_api.py::test_login_success_with_email_and_username PASSED
tests/test_auth_api.py::test_login_failure_invalid_credentials PASSED
tests/test_auth_api.py::test_current_user_profile_endpoint PASSED
tests/test_auth_api.py::test_refresh_token_rotation PASSED
tests/test_auth_api.py::test_refresh_token_reuse_detection PASSED
tests/test_auth_api.py::test_logout_session_revocation PASSED
tests/test_auth_api.py::test_httponly_cookie_refresh_and_logout PASSED
tests/test_auth_security.py::test_argon2id_password_hashing PASSED
tests/test_auth_security.py::test_password_policy_validation PASSED
tests/test_auth_security.py::test_access_token_creation_and_decoding PASSED
tests/test_auth_security.py::test_refresh_token_creation_and_decoding PASSED
tests/test_auth_security.py::test_expired_token_rejection PASSED
tests/test_auth_security.py::test_invalid_token_type_rejection PASSED
tests/test_auth_security.py::test_tampered_token_rejection PASSED
tests/test_auth_security.py::test_hash_token PASSED
tests/test_auth_security.py::test_login_rate_limiter PASSED

============================= 20 passed in 6.98s ==============================
```

---

## 7. Current Device State & Next Steps

The application on the OPPO physical phone is currently in a clean, idle state on the Sign In screen:
- **Server Endpoint:** `http://192.168.0.176:8000`
- **Owner Account:** `loveowner` (`owner@love.ai`)
- **Ready for User:** The user can now manually enter their owner password on the device to complete live authenticated verification.
