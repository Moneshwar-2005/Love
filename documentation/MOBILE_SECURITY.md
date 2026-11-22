# LOVE Mobile — Security Architecture & Threat Matrix

## 1. Mobile Threat Matrix

| Threat | Attack Vector | Mobile Mitigation Strategy | Severity |
|---|---|---|---|
| **Stolen Device Token Extraction** | Physical device theft with file inspection / adb backup | Access token held strictly in ephemeral JavaScript memory. Refresh token encrypted inside hardware-backed Android Keystore (`LoveKeystorePlugin` AES-256-GCM) / iOS Keychain. | Critical |
| **Plaintext Storage Leaks** | Web storage inspection or backup extraction | Explicit prohibition and unit-test validation that `localStorage` contains zero tokens or secrets. Standard `SharedPreferences` replaced with Keystore AES-GCM vault. | High |
| **ADB / Cloud Backup Data Theft** | Malicious ADB backup or cloud serialization | `android:allowBackup="false"` enforced in `AndroidManifest.xml`. | High |
| **Token Hijacking via XSS** | Injected malicious script in WebView | No dynamic `eval()` or unescaped HTML injection. Safe markdown renderer whitelists protocols (`http:`, `https:`, `mailto:`). Access token is non-enumerable in module closure. | High |
| **Biometric Bypass** | Attacker disables device biometric prompt | Native `androidx.biometric.BiometricPrompt` (`LoveBiometricPlugin`) mandatory before the local vault yields the refresh token. Invalidating or failing prompt prevents token retrieval. | High |
| **Unauthorized Background Listening** | Malicious trigger or battery drain from wake word | Always-on microphone listening is deliberately **not implemented** on mobile. Audio recording only occurs on active user push-to-talk touch. | Medium |
| **Push Notification Surveillance** | Interception of push notification APNs/FCM payloads | Push notification payloads contain zero message content, memory data, or PII. Notifications contain generic task IDs only. | Medium |
| **Rogue Client Impersonation** | Attacker attempts to forge client type | Device registration binds cryptographically random installation UUID (`crypto.randomUUID()`) to the authorized user account. | Medium |

---

## 2. Storage Comparison: Desktop vs Web vs Mobile

| Security Attribute | Desktop (Electron) | Web (Browser) | Mobile (Capacitor) |
|---|---|---|---|
| **Access Token** | In-Memory closure | In-Memory closure | In-Memory closure (`MobileApiClient`) |
| **Refresh Token** | OS Keychain (`keytar` / DPAPI) | `HttpOnly`, `Secure`, `SameSite=Lax` Cookie | Hardware-backed Keystore (`LoveKeystorePlugin` AES-256-GCM) / Keychain |
| **JavaScript Token Access** | Protected behind Preload IPC | Completely blocked (HttpOnly cookie) | Refresh token blocked behind native bridge; access token in closure |
| **Hardware Biometric Gating** | Optional Windows Hello / Touch ID | WebAuthn Platform Authenticator | Native BiometricPrompt (`LoveBiometricPlugin`) / Face ID |
| **Backup Leakage Defense** | Protected by OS user account permissions | None (browser-managed) | `android:allowBackup="false"` in manifest |
| **Offline Data Exposure** | Local SQLite files protected by OS user account | None (zero local database persistence) | None (zero local database persistence) |

---

## 3. Biometric Authentication Architecture

LOVE Mobile integrates with platform biometric hardware:

1. **Android**: Native `LoveBiometricPlugin.java` integrating `androidx.biometric.BiometricPrompt` and `BiometricManager`, supporting Class 3 (Strong) biometrics (Fingerprint and secure 3D Face Unlock) with device credential (PIN/pattern) fallback.
2. **iOS**: `LocalAuthentication` framework (`LAContext.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics)`).

### Gating Invariant
Biometrics on LOVE Mobile act as a **local gatekeeper to the hardware vault**:
- Passing biometric authentication authorizes `MobileSecureStorage` to read the encrypted `refresh_token`.
- The retrieved token is then transmitted to `/api/v1/auth/refresh`.
- If the token was revoked remotely on the backend, the backend responds with `401 Unauthorized` and the session terminates immediately, regardless of local biometric success.

---

## 4. Hardware-Backed Android Keystore Architecture (`LoveKeystorePlugin.java`)

To prevent plaintext token storage in `/data/data/ai.love.assistant/shared_prefs/CapacitorStorage.xml`:
- **Cryptographic Engine:** AES-256 in Galois/Counter Mode (`AES/GCM/NoPadding`) with a 12-byte cryptographically secure random IV and 128-bit authentication tag.
- **Master Key Security:** Master key (`love_mobile_master_key`) is stored in and managed by `AndroidKeyStore`. The master key never leaves hardware-isolated storage (TEE / StrongBox).
- **Integrity Validation:** GCM mode verifies ciphertext integrity; any manual tampering with stored XML files causes an `AEADBadTagException`, preventing ciphertext malleability.

---

## 5. Push Notification Privacy Principles

Push notification architecture complies with privacy-first standards:
1. **Device-Scoped Registration**: The mobile device registers an APNs / FCM push token via `POST /api/v1/devices/notifications/register`.
2. **Preference Controls**: Users independently toggle notifications for:
   - Task Approvals (`task_approvals`)
   - Task Completions (`task_completions`)
   - Security Alerts (`security_alerts`)
3. **Zero Content in Payloads**: Push notification payloads contain:
   ```json
   {
     "title": "LOVE — Action Requires Authorization",
     "body": "A background task requires your approval.",
     "data": { "task_id": "task-102", "action_id": "act-201" }
   }
   ```
   No conversation text, user memory, database records, or sensitive strings are ever included in notification payloads.

---

## 6. Remote Session Revocation

Users can inspect all active authorized devices from **Mobile Settings > Authorized Devices**:
- Each entry displays the device name, platform (`android`, `ios`, `windows`, `web`), registration date, and active session status.
- Tapping **Revoke Session** sends `DELETE /api/v1/devices/{device_id}`, which terminates all refresh-token sessions associated with that device on the backend SQLite database.

---

## 7. Phase 12.5 Audit & Verification Status

- **Android Keystore AES-256-GCM Plugin:** Implemented, compiled into APK DEX, and verified with 10 dedicated security tests.
- **BiometricPrompt Hardware Gating:** Integrated via `androidx.biometric:biometric:1.1.0` and verified.
- **Application Backup Leakage:** `android:allowBackup="false"` verified via `aapt.exe dump xmltree`.
- **Voice API Compatibility:** Form parameter corrected to `'file'` matching FastAPI backend.
- **Regression Suite:** 41 mobile tests passing; 336 monorepo tests passing.
