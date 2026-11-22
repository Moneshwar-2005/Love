# LOVE Mobile — iOS Setup & Build Guide

## 1. Environment & Operational Status Disclosure

> [!WARNING]
> **BUILD STATUS: IMPLEMENTED — NOT LIVE VERIFIED**  
> LOVE was developed and assembled on a Windows 11 host workstation. Apple Xcode, `xcodebuild`, iOS Simulators, and macOS SDK toolchains are physically unavailable on Windows.
>
> All iOS project manifests, bundle identifiers, permission dictionaries (`Info.plist`), CocoaPods specs, and web runtime bridges have been **fully generated and synchronized** in `mobile/ios/App/`. However, final compilation of the `.ipa` package and physical iOS device execution must be conducted on macOS and are therefore classified as **IMPLEMENTED — NOT LIVE VERIFIED**.

---

## 2. Directory Structure & Key Files

```
mobile/ios/
└── App/
    ├── App/
    │   ├── AppDelegate.swift              # Native application lifecycle & Capacitor bridge
    │   ├── Info.plist                     # iOS permissions & bundle metadata
    │   ├── Assets.xcassets                # AppIcon & Splash image sets
    │   └── capacitor.config.json          # Mirrored Capacitor configuration
    ├── App.xcodeproj                      # Xcode project workspace
    └── Podfile                            # CocoaPods dependency specification
```

---

## 3. Bundle Identifier & Permissions Configuration

- **Application Name**: `LOVE`
- **Bundle Identifier**: `ai.love.assistant`
- **Deployment Target**: iOS 14.0+

### Privacy Keys in `mobile/ios/App/App/Info.plist`

```xml
<!-- Microphone Permission for Push-to-Talk Speech Recognition -->
<key>NSMicrophoneUsageDescription</key>
<string>LOVE requires microphone access to enable push-to-talk voice conversations with your personal assistant.</string>

<!-- Biometric Face ID / Touch ID Permission -->
<key>NSFaceIDUsageDescription</key>
<string>LOVE uses Face ID to securely authenticate your session and unlock your local encrypted credentials.</string>
```

---

## 4. iOS Audio & Secure Storage Runtime Compatibility

Phase 12.5 hardened mobile runtime compatibility specifically for iOS WKWebView:

1. **Dynamic Audio Container Detection (`voiceService.ts`):**
   - iOS Safari / WKWebView does not support `audio/webm;codecs=opus` for `MediaRecorder`.
   - `voiceService.ts` queries `MediaRecorder.isTypeSupported('audio/webm')`. If unsupported, it seamlessly falls back to `audio/mp4` / `audio/aac`.
   - File uploads dynamically set the file extension (`.mp4` vs `.webm`) when sending `FormData` to `/api/v1/voice/transcribe`, ensuring compatibility with both backend Whisper and native iOS recording codecs.

2. **iOS Keychain Hardware Gating:**
   - On iOS native targets, `mobileSecureStorage.ts` dispatches refresh token storage to the iOS Keychain via native plugin bridge.
   - Access tokens remain exclusively in ephemeral JavaScript memory closure.

3. **Biometric Authentication:**
   - Uses iOS `LocalAuthentication` framework (`LAContext`), supporting Face ID and Touch ID with device passcode fallback.

---

## 5. Complete macOS Developer Handover & Build Steps

To compile, test, and package LOVE Mobile for iOS, follow these steps on a macOS workstation with Xcode 15+ installed:

### Step 1: Clone Repository & Install Node Dependencies
```bash
git clone <repository_url> love-mobile
cd love-mobile
npm install
npm --prefix mobile install
```

### Step 2: Build Web Assets & Synchronize iOS Project
```bash
npm --prefix mobile run build
cd mobile
npx cap sync ios
```

### Step 3: Install CocoaPods
```bash
cd ios/App
pod install
```

### Step 4: Open in Xcode
```bash
xcodebuild -workspace App.xcworkspace -scheme App -destination 'generic/platform=iOS' build
# OR open interactively in Xcode IDE:
open App.xcworkspace
```

### Step 5: Configure Code Signing & Provisioning
1. Select the `App` project in Xcode's project navigator.
2. Navigate to **Signing & Capabilities**.
3. Select your registered **Apple Developer Team**.
4. Confirm Bundle Identifier: `ai.love.assistant`.
5. Xcode will automatically generate the provisioning profile.

### Step 6: Run on iOS Simulator or Device
```bash
# Run on Simulator
npx cap run ios --target="iPhone 15 Pro"

# Run on connected physical iOS device
npx cap run ios --device
```

### Step 7: Archive & Export for App Store Connect / TestFlight
In Xcode:
1. Select **Product > Scheme > App**.
2. Select destination **Any iOS Device (arm64)**.
3. Select **Product > Archive**.
4. Once archiving succeeds in the Organizer window, click **Distribute App**.
5. Select **App Store Connect** for TestFlight beta testing or public distribution.
