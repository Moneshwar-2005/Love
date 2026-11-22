# LOVE Mobile — Android Setup & Build Guide

## 1. Prerequisites & Environment

LOVE Mobile's Android target requires the following verified host components:

- **Operating System**: Windows 11 / Linux / macOS
- **Node.js**: v20+ (Verified with v26.4.0) & npm 11.17.0
- **Android SDK**: API Platform 34 (Android 14) / API Platform 35 (Android 15)
  - Canonical location: `F:\Android\SDK`
  - Build-tools: `34.0.0`, `35.0.0`
- **Java Development Kit**: JDK 21+ or OpenJDK 25 (Verified with JetBrains JBR OpenJDK 25.0.2 at `F:\Android\Android Studio\jbr`)
- **Gradle**: Gradle 9.3.1 Wrapper (resolves Groovy AST class file version 69 compatibility with Java 25)
- **Android Gradle Plugin (AGP)**: `8.8.0`
- **Jetpack Biometrics**: `androidx.biometric:biometric:1.1.0`

---

## 2. Directory Structure & Key Files

```
mobile/android/
├── app/
│   ├── build.gradle                       # Android app module with androidx.biometric dependency
│   ├── proguard-rules.pro                 # R8 / ProGuard rules for release shrinking
│   └── src/main/
│       ├── AndroidManifest.xml            # Hardware permissions & allowBackup="false"
│       ├── java/ai/love/assistant/
│       │   ├── MainActivity.java          # Native entry point registering custom plugins
│       │   ├── LoveKeystorePlugin.java    # AndroidKeyStore AES-256-GCM vault plugin
│       │   └── LoveBiometricPlugin.java   # Jetpack BiometricPrompt native plugin
│       └── res/                           # App icons, splash screens, themes, layouts
├── build.gradle                           # Root Gradle project configuration (AGP 8.8.0)
├── gradle/wrapper/
│   ├── gradle-wrapper.jar
│   └── gradle-wrapper.properties          # Gradle 9.3.1 distribution URL
├── gradlew.bat                            # Windows Gradle wrapper execution script
├── local.properties                       # Android SDK root pointer (sdk.dir)
└── variables.gradle                       # minSdkVersion=26, compileSdkVersion=34, targetSdkVersion=34
```

---

## 3. Permissions & Security Configuration

The Android manifest (`mobile/android/app/src/main/AndroidManifest.xml`) requests the following minimal necessary permissions:

```xml
<!-- Hardware Microphone & Audio for Push-to-Talk -->
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />

<!-- Network Communication with LOVE Host Backend -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<!-- Hardware Biometric Authentication -->
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.USE_FINGERPRINT" />

<!-- Human-in-the-Loop Task Approval Notifications -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

### Application Security Attributes
```xml
<application
    android:allowBackup="false"
    android:icon="@mipmap/ic_launcher"
    android:label="@string/app_name"
    android:roundIcon="@mipmap/ic_launcher_round"
    android:supportsRtl="true"
    android:theme="@style/AppTheme"
    android:usesCleartextTraffic="true">
```
- **`android:allowBackup="false"`**: Strictly prevents ADB backup commands (`adb backup`) and automated cloud backup services from extracting private internal storage.
- **`android:usesCleartextTraffic="true"`**: Permitted in development to connect to local development backends (e.g., `http://10.0.2.2:8000` or LAN IPs) without self-signed TLS certificates.

---

## 4. Emulator vs Physical Device Networking

| Environment | Server Base URL | Configuration Note |
|---|---|---|
| **Android Emulator** | `http://10.0.2.2:8000` | Android QEMU maps `10.0.2.2` directly to the host machine loopback `127.0.0.1`. LOVE defaults to this address automatically on Android. |
| **Physical Device (WiFi)** | `http://192.168.x.x:8000` | Enter the host machine's LAN IP address in the Mobile Auth Screen or Settings drawer. |
| **Reverse Proxy (HTTPS)** | `https://love.yourdomain.com` | Enter public HTTPS endpoint with TLS certificate. |

---

## 5. Build & Assembly Instructions

### Step 1: Compile Web Production Bundle
```bash
cmd /c "npm --prefix mobile run build"
```
This runs TypeScript checking (`tsc`) and Vite bundling, creating optimized assets in `mobile/dist/`.

### Step 2: Synchronize Capacitor Native Assets
```bash
cd mobile
npx cap sync android
```
This copies web assets into `mobile/android/app/src/main/assets/public/` and updates plugin bindings.

### Step 3: Assemble Debug APK
Set JDK environment variable and invoke the Gradle wrapper:
```powershell
$env:JAVA_HOME = "F:\Android\Android Studio\jbr"
cd F:\LOVE\mobile\android
.\gradlew.bat assembleDebug
```

### Build Output Verification (Phase 12.5 Hardened APK)
- **Debug APK Location:** `mobile/android/app/build/outputs/apk/debug/app-debug.apk`
- **File Size:** 6,617,636 bytes (~6.31 MiB)
- **SHA-256 Checksum:** `8ECE99C2E04297C2E7ADF26750489EBF89C83B4BF64F90C5467345D326E03ECE`
- **Package Details:** `ai.love.assistant` (versionCode=1, versionName="1.0")
- **SDK Targets:** `minSdkVersion=26`, `compileSdkVersion=34`, `targetSdkVersion=34`
- **Signature Scheme:** APK Signature Scheme v2: `true` (RSA 2048-bit debug certificate)
- **Native Custom Plugins In Bytecode:** `LoveKeystorePlugin.class`, `LoveBiometricPlugin.class`

---

## 6. Running on Device or Emulator

### Launch via Android Debug Bridge (ADB)
```bash
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n ai.love.assistant/ai.love.assistant.MainActivity
```

### Inspecting Device Logs
```bash
adb logcat -s "Capacitor" "LOVE" "Chromium"
```

### Host Runtime & Tooling Disclosure
- **ADB Status:** `adb devices` reports no currently attached physical devices on USB/WiFi.
- **Emulator Images:** Directory `F:\Android\SDK\system-images` is not present on disk; no local emulator AVDs configured.
- **Operational Status:** Fully compiled, assembled, and statically verified binary; runtime OS execution classified as **COMPILED & STATICALLY VERIFIED (NOT LIVE VERIFIED ON RUNNING OS KERNEL)**.
