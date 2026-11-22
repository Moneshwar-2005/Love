# LOVE — Phase 12.7B: Secure Local HTTPS Transport & Android WebView Hardening Audit

**Date:** 2026-11-21  
**Project:** LOVE Personal AI Assistant (`F:\LOVE`)  
**Target Device:** OPPO I2305 (vivo I2305, Android 16 / API 36, ADB Serial: `10BE910T3Y000PF`)  
**Backend Endpoint:** `https://192.168.0.176:8000` (FastAPI / Uvicorn with TLS 1.3, SQLite WAL `database/love.db`)  
**Package:** `ai.love.assistant`  
**Overall Status:** **VERIFIED**

---

## 1. Executive Summary

Phase 12.7B successfully transitioned all network communication between the physical Android application and the LOVE backend from insecure cleartext HTTP (`http://192.168.0.176:8000`) to strict, authenticated **HTTPS with TLS 1.3** (`https://192.168.0.176:8000`).

The implementation establishes a development Public Key Infrastructure (PKI) with a dedicated local Development Root Certificate Authority, generates cryptographically valid server certificates with exact Subject Alternative Name (SAN) IP/DNS bindings, configures Android Network Security Config scoped strictly to debug builds, and restores WebView security by removing insecure mixed-content allowances.

All tests validate certificate chains without bypasses (`curl -k`, `verify=False`, or trust-all managers were strictly avoided). Release packaging was audited directly to confirm that development certificates, debug overrides, and private keys are completely excluded from release builds.

---

## 2. Status Assessment Table

| Component / Requirement | Status | Verification Evidence |
| :--- | :---: | :--- |
| **Development CA & PKI Architecture** | **VERIFIED** | 2048-bit RSA Development CA (`love_dev_ca.crt`), pathlen=1, keyCertSign/cRLSign. |
| **Certificate SAN IP/DNS Validation** | **VERIFIED** | Server cert binds `192.168.0.176`, `127.0.0.1`, `10.0.2.2`, `localhost`, `love.local`. |
| **Private Key Isolation & Permissions** | **VERIFIED** | Private keys in `secrets/certs/` (gitignored), `icacls` restricted to user. |
| **Backend HTTPS & Uvicorn TLS** | **VERIFIED** | Uvicorn running on `https://0.0.0.0:8000` with TLS 1.3 `TLS_AES_256_GCM_SHA384`. |
| **Strict TLS Handshake (Windows Local)** | **VERIFIED** | Python `ssl` strict verification (CERT_REQUIRED, check_hostname=True) 200 OK. |
| **Strict TLS Handshake (Windows LAN)** | **VERIFIED** | `https://192.168.0.176:8000/health` verified with full certificate chain validation. |
| **Strict TLS Handshake (Physical Phone OS)** | **VERIFIED** | Android OS `curl` with `--cacert` returned `SSL certificate verify ok` over TLS 1.3. |
| **Android Debug CA Trust (`network_security_config`)** | **VERIFIED** | Debug build mounts `@raw/love_dev_ca` inside `<debug-overrides>`. |
| **Android WebView HTTPS Request** | **VERIFIED** | Physical phone WebView fetched `https://192.168.0.176:8000/health` successfully (200 OK). |
| **Capacitor Scheme & Origin Hardening** | **VERIFIED** | Hosted on `https://localhost/`, `androidScheme: "https"`, `cleartext: false`. |
| **WebView Mixed Content Hardening** | **VERIFIED** | `MIXED_CONTENT_ALWAYS_ALLOW` removed, set to `MIXED_CONTENT_NEVER_ALLOW`. |
| **CORS Preflight & Credential Handling** | **VERIFIED** | OPTIONS preflight returned 200 OK with `Access-Control-Allow-Origin: https://localhost`. |
| **Release APK Security Isolation** | **VERIFIED** | Direct ZIP audit of `app-release-unsigned.apk`: 0 dev certs, 0 keys, 0 raw resources. |
| **Release Cleartext Traffic Restriction** | **VERIFIED** | Release `network_security_config.xml` enforces `cleartextTrafficPermitted="false"`. |
| **Backend Regression Test Suite** | **VERIFIED** | 20 / 20 passed in 5.92s (including cookie refresh/logout). |
| **Mobile & Web Regression Test Suites** | **VERIFIED** | Mobile: 41/41 passed; Web: 33/33 passed; TypeScript build: 0 errors. |

---

## 3. Original Transport Vulnerabilities & Remediations

| Vulnerability in Phase 12.7A | Risk & Behavior | Remediation in Phase 12.7B |
| :--- | :--- | :--- |
| `androidScheme: "http"` | WebView origin was cleartext HTTP (`http://localhost/`), susceptible to tampering. | Reverted to `"https"` (`https://localhost/`). Outbound calls are HTTPS-to-HTTPS. |
| `usesCleartextTraffic="true"` | Permitted unencrypted HTTP requests globally across the application. | Removed from `AndroidManifest.xml`. Configured `cleartextTrafficPermitted="false"`. |
| `MIXED_CONTENT_ALWAYS_ALLOW` | Allowed arbitrary insecure HTTP subresources within HTTPS contexts. | Changed to `WebSettings.MIXED_CONTENT_NEVER_ALLOW` in `MainActivity.java`. |
| Cleartext LAN backend (`http://192.168.0.176:8000`) | User credentials and session tokens transmitted in plaintext across local WiFi. | Uvicorn bound to TLS 1.3 using local development PKI with SAN IP encoding. |
| Missing Network Security Config | Android OS defaulted to platform trust store with no debug scoping. | Added `network_security_config.xml` with `<debug-overrides>` for development. |

---

## 4. Development PKI & Certificate Architecture

### A. Root Certificate Authority (`love_dev_ca.crt`)
- **Key Type:** RSA 2048-bit
- **Distinguished Name:** `CN=LOVE Development Root CA, O=LOVE Personal AI Assistant, OU=Development Security`
- **Extensions:**
  - `BasicConstraints(ca=True, path_length=1)` [Critical]
  - `KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True)` [Critical]
  - `SubjectKeyIdentifier`
- **Storage:** `F:\LOVE\secrets\certs\love_dev_ca.key` (Permissions restricted via Windows ACLs; excluded by `.gitignore`).
- **Android Deployment:** Public certificate placed in `mobile/android/app/src/debug/res/raw/love_dev_ca.crt`.

### B. Server TLS Certificate (`love_dev_server.crt`)
- **Key Type:** RSA 2048-bit
- **Distinguished Name:** `CN=192.168.0.176, O=LOVE Personal AI Assistant, OU=Development Server`
- **Extensions:**
  - `BasicConstraints(ca=False)` [Critical]
  - `KeyUsage(digital_signature=True, key_encipherment=True)` [Critical]
  - `ExtendedKeyUsage([serverAuth])` [Critical]
  - `SubjectAlternativeName` [RFC 5280]:
    - `iPAddress: 192.168.0.176` (Target physical phone LAN host)
    - `iPAddress: 127.0.0.1` (Local loopback)
    - `iPAddress: 10.0.2.2` (Android emulator host loopback)
    - `dNSName: localhost`
    - `dNSName: love.local`
- **Server Bundle:** `F:\LOVE\secrets\certs\love_dev_bundle.crt` (Concatenated server cert + CA cert).

---

## 5. Android Network Security & Scope Isolation

### A. Production Configuration (`src/main/res/xml/network_security_config.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
```
- Only pre-installed system Certificate Authorities are trusted.
- Cleartext HTTP traffic is blocked at the Android operating system level.
- No debug trust anchors or user-installed CAs are trusted.

### B. Development Configuration (`src/debug/res/xml/network_security_config.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    <!-- Debug overrides: active ONLY when android:debuggable="true" -->
    <debug-overrides>
        <trust-anchors>
            <certificates src="system" />
            <certificates src="@raw/love_dev_ca" />
        </trust-anchors>
    </debug-overrides>
</network-security-config>
```
- `<debug-overrides>` is exclusively activated by Android OS when `android:debuggable="true"`.
- Android WebView verifies `love_dev_server.crt` against `@raw/love_dev_ca` without requiring the user to install root certificates into Android OS user credential storage.
- Full SAN matching and expiration checks remain enforced.

---

## 6. Strict TLS Verification Evidence

### A. Windows Host Socket Inspection
```text
Live TLS Version: TLSv1.3
Live Cipher Suite: ('TLS_AES_256_GCM_SHA384', 'TLSv1.3', 256)
Peer Certificate Subject: ((('commonName', '192.168.0.176'),), (('organizationName', 'LOVE Personal AI Assistant'),), (('organizationalUnitName', 'Development Server'),))
Peer Certificate SAN: (('IP Address', '192.168.0.176'), ('IP Address', '127.0.0.1'), ('IP Address', '10.0.2.2'), ('DNS', 'localhost'), ('DNS', 'love.local'))
```

### B. Physical Android OS Handshake (`curl /system/bin/curl`)
```text
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* Server certificate:
*  subject: CN=192.168.0.176; O=LOVE Personal AI Assistant; OU=Development Server
*  subjectAltName: host "192.168.0.176" matched cert's IP address!
*  issuer: CN=LOVE Development Root CA; O=LOVE Personal AI Assistant; OU=Development Security
*  SSL certificate verify ok.
* Connected to 192.168.0.176 (192.168.0.176) port 8000
< HTTP/1.1 200 OK
{"app_name":"LOVE Personal AI Assistant","version":"0.2.0","status":"healthy","environment":"development","database_status":"connected"}
```

### C. Physical Android WebView In-App Request (`CDP fetch`)
```json
{
  "app_name": "LOVE Personal AI Assistant",
  "version": "0.2.0",
  "status": "healthy",
  "environment": "development",
  "database_status": "connected",
  "services": {
    "database": {
      "status": "healthy",
      "message": "Database connection verified",
      "latency_ms": 1.28
    }
  }
}
```

### D. CORS Preflight Handshake (OPTIONS)
```http
HTTP/1.1 200 OK
date: Sat, 21 Nov 2026 09:38:00 GMT
server: uvicorn
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, QUERY
access-control-allow-credentials: true
access-control-allow-origin: https://localhost
access-control-allow-headers: Content-Type
```

---

## 7. Release APK Security Audit

Direct binary inspection of `mobile/android/app/build/outputs/apk/release/app-release-unsigned.apk` (493 entries):
- **Development Private Keys (`*.key`):** `0 found` (PASSED)
- **Development Certificates (`*.crt`, `*.pem`, `love_dev`):** `0 found` (PASSED)
- **Debug Raw Resources (`res/raw/`):** `0 found` (PASSED)
- **Web Assets (`assets/public/`):** 10 files audited, zero embedded secrets (PASSED)
- **Explanation of Previous Command Exit Code 1:**
  A broad substring search for `'raw'` matched non-security Android Jetpack library metadata (`META-INF/androidx.drawerlayout_drawerlayout.version` and `vectordrawable`). Scoping the audit specifically to security keys and raw resources confirmed zero development artifacts were bundled.

---

## 8. Backend Test Failure Root Cause & Resolution

- **Symptom:** `tests/test_auth_api.py::test_httponly_cookie_refresh_and_logout` failed with `400 Bad Request`.
- **Root Cause:**
  In `backend/app/config/settings.py`, `effective_cookie_secure` returned `True` whenever `SSL_KEYFILE` and `SSL_CERTFILE` were set in `.env`.
  When cookies have the `Secure` flag, HTTP test clients (such as Starlette's `TestClient` connecting over `http://testserver`) refuse to send the cookie back on subsequent unencrypted requests. As a result, `client.post("/api/v1/auth/refresh", json={})` lacked the refresh cookie and returned 400.
- **Resolution:**
  Updated `effective_cookie_secure` in `settings.py` to always return `False` when `APP_ENV == "testing"`:
  ```python
  @property
  def effective_cookie_secure(self) -> bool:
      if self.COOKIE_SECURE is not None:
          return self.COOKIE_SECURE
      if self.APP_ENV == "testing":
          return False
      return self.APP_ENV == "production" or bool(self.SSL_KEYFILE and self.SSL_CERTFILE)
  ```
- **Test Result:** 20/20 tests passed.

---

## 9. Final Regression Suite Results

| Test Suite | Framework | Total Tests | Passed | Failed | Execution Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Backend Authentication API** | `pytest` | 11 | 11 | 0 | 3.42s |
| **Backend Security & Token Cryptography** | `pytest` | 9 | 9 | 0 | 2.50s |
| **Mobile Security & Biometrics** | `vitest` | 41 | 41 | 0 | 4.90s |
| **Web Client Workspaces & Auth** | `vitest` | 33 | 33 | 0 | 6.77s |
| **Mobile TypeScript & Asset Build** | `tsc + vite` | 2,170 modules | 2,170 | 0 | 1.38s |
| **Android Debug APK Compilation** | `gradlew assembleDebug` | 255 tasks | 255 | 0 | 26s |
| **Android Release APK Compilation** | `gradlew assembleRelease` | 345 tasks | 345 | 0 | 2m 16s |

---

## 10. Captured Artifacts & Screenshots

- **HTTPS Ready Login Screen:** [phase12_7b_https_login_ready.png](file:///F:/LOVE/documentation/screenshots/phase12_7b_https_login_ready.png)
- **HTTPS Invalid Login Rejection:** [phase12_7b_invalid_login_https.png](file:///F:/LOVE/documentation/screenshots/phase12_7b_invalid_login_https.png)
- **Authenticated Workspace over HTTPS:** [phase12_7b_authenticated_workspace_https.png](file:///F:/LOVE/documentation/screenshots/phase12_7b_authenticated_workspace_https.png)
- **Release Audit Script:** [audit_release_apk.py](file:///F:/LOVE/scripts/audit_release_apk.py)
- **Certificate Generator:** [generate_dev_certs.py](file:///F:/LOVE/scripts/generate_dev_certs.py)

---

## 11. Remaining Limitations & Production Notes

1. **Local Development Scope:** The development CA (`love_dev_ca.crt`) is intended solely for local development and LAN device testing. In production, a publicly signed certificate (e.g. Let's Encrypt / DigiCert) must be installed on the reverse proxy or server.
2. **IP Changes:** If the host machine's LAN IP changes from `192.168.0.176`, re-running `python scripts/generate_dev_certs.py` will regenerate the SAN certificate for the new LAN IP.
