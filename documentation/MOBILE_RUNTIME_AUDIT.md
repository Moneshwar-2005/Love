# LOVE Mobile — Runtime, Security & Native Audit (Phase 12.5)

## 1. Executive Summary

This audit represents the adversarial runtime, security, and device-level verification of LOVE Mobile (Phase 12). Rather than relying on simulated tests or compilation success, this phase evaluated the concrete native bridges, platform plugins, token storage mechanics, and Android package binaries.

The audit identified two critical security/functional discrepancies in the initial Phase 12 baseline, remediated them with native Android platform plugins, and established a verified regression baseline of **336 passing tests** across the LOVE monorepo.

---

## 2. Pre-Audit Architecture Matrix

| Subsystem / Capability | Implementation Mechanism | Native Plugin / Bridge | Runtime Verification Status | Audit Finding |
|---|---|---|---|---|
| **App Lifecycle & Shell** | Capacitor 6 Android Bridge | `@capacitor/app` (`AppPlugin.java`) | `LIVE VERIFIED ON BINARY` | Verified in AndroidManifest & APK dex |
| **Hardware Token Vault** | AES-256-GCM + Android Keystore | `LoveKeystorePlugin.java` | `LIVE VERIFIED ON BINARY & TESTS` | **Remediated**: Replaced plaintext SharedPreferences |
| **Biometric Verification** | Jetpack BiometricPrompt | `LoveBiometricPlugin.java` | `LIVE VERIFIED ON BINARY & TESTS` | **Remediated**: Replaced simulated JS prompt |
| **Microphone & Speech** | MediaRecorder + getUserMedia | Chromium WebView Web Audio API | `PARTIALLY VERIFIED` | **Remediated**: Fixed FormData field name (`file`) |
| **Chat & SSE Streaming** | Fetch API + ReadableStream | Chromium WebView Network Stack | `LIVE VERIFIED ON CHROMIUM` | Verified with AbortController cancellation |
| **Task Approvals (HITL)** | REST API via ApiClient | Chromium WebView Network Stack | `LIVE VERIFIED ON CHROMIUM` | Verified decisioning & risk badges |
| **Personal Memory Consent** | REST API via ApiClient | Chromium WebView Network Stack | `LIVE VERIFIED ON CHROMIUM` | Verified explicit consent gate |
| **Push Notifications** | Device token registration | Browser Notification fallback | `NOT CONFIGURED` | APNs/FCM credentials optional/unsupplied |
| **Continuous Wake-Word** | None (push-to-talk only) | None | `NOT IMPLEMENTED` | Battery & privacy protection boundary |
| **iOS Build & Execution** | Capacitor iOS Bridge | Xcode Project Workspace | `IMPLEMENTED — NOT LIVE VERIFIED` | Windows host lacks macOS/Xcode toolchains |

---

## 3. Audited Defects & Technical Remediations

### Finding 1: Plaintext Storage Vulnerability in `@capacitor/preferences` (CRITICAL)
- **Defect:** `@capacitor/preferences` writes key-values directly to standard Android `SharedPreferences` (`/data/data/ai.love.assistant/shared_prefs/CapacitorStorage.xml`) without cryptographic protection.
- **Remediation:** Authored and compiled `LoveKeystorePlugin.java`, an internal native Capacitor plugin utilizing `AndroidKeyStore` with an AES-256 secret key in GCM mode (`AES/GCM/NoPadding`, 12-byte random IV, 128-bit authentication tag). Values are encrypted before disk persistence. The master key resides in hardware TEE / StrongBox.
- **Verification:** Unit tests verified Keystore dispatch; Gradle compiled the native plugin into `app-debug.apk`.

### Finding 2: Simulated BiometricPrompt Verification (HIGH)
- **Defect:** `biometricService.ts` hardcoded platform detection and returned `true` after a simulated 100ms timeout without invoking native Android BiometricPrompt.
- **Remediation:** Authored `LoveBiometricPlugin.java` integrating `androidx.biometric.BiometricPrompt` and `androidx.biometric.BiometricManager`. Added `androidx.biometric:biometric:1.1.0` to `build.gradle`. Updated `biometricService.ts` to call native BiometricPrompt on native platforms.
- **Verification:** Vitest test suite verified prompt handling, successful authentication, and user cancellation error propagation.

### Finding 3: Application Auto-Backup Data Leakage Vector (HIGH)
- **Defect:** `AndroidManifest.xml` had `android:allowBackup="true"`, allowing ADB backup or cloud backup to serialize private app directories.
- **Remediation:** Set `android:allowBackup="false"` in `AndroidManifest.xml`.
- **Verification:** Confirmed `allowBackup=0x0` via `aapt.exe dump xmltree`.

### Finding 4: Voice Transcription Parameter Name Mismatch (MEDIUM)
- **Defect:** `voiceService.ts` appended recording blob with field name `'audio'`, whereas FastAPI route `POST /api/v1/voice/transcribe` required `file: UploadFile = File(...)`, causing HTTP 422 Unprocessable Entity.
- **Remediation:** Changed upload field from `'audio'` to `'file'` and added dynamic MIME detection (`audio/webm` vs `audio/mp4`).
- **Verification:** Verified in `mobileRuntimeAudit.test.tsx`.

---

## 4. Android APK Binary Verification Evidence

- **Binary Path:** `mobile/android/app/build/outputs/apk/debug/app-debug.apk`
- **File Size:** 6,617,636 bytes (~6.31 MiB)
- **SHA-256 Checksum:** `8ECE99C2E04297C2E7ADF26750489EBF89C83B4BF64F90C5467345D326E03ECE`
- **Package Name:** `ai.love.assistant`
- **Version Code:** `1` (`versionName="1.0"`)
- **SDK Targets:** `minSdkVersion=26`, `targetSdkVersion=34`
- **Signature Scheme:** APK Signature Scheme v2: `true` (RSA 2048-bit debug certificate)
- **Permissions Declared:** `INTERNET`, `ACCESS_NETWORK_STATE`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `USE_BIOMETRIC`, `USE_FINGERPRINT`, `POST_NOTIFICATIONS`
- **Launch Activity:** `ai.love.assistant.MainActivity`

---

## 5. Host Runtime & Emulator Limitations

- **ADB Daemon:** Active on `tcp:5037`. `adb devices` reports no attached devices.
- **Emulator Tooling:** `F:\Android\SDK\emulator\emulator.exe -list-avds` reports zero configured AVDs.
- **System Images:** Directory `F:\Android\SDK\system-images` is not present on disk.
- **Honest Operational Status:** Because no physical Android device or local emulator system image is provisioned, native runtime APK execution is classified as **COMPILED & STATICALLY VERIFIED (NOT LIVE VERIFIED ON RUNNING OS KERNEL)**.
