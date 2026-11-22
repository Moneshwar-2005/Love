# LOVE Mobile — Release & Distribution Guide

## 1. Versioning Strategy

LOVE Mobile follows Semantic Versioning (`MAJOR.MINOR.PATCH`):
- Current Mobile Application Version: `1.0.0`
- Current Android `versionCode`: `1`
- Current iOS `CURRENT_PROJECT_VERSION`: `1`

The versions are maintained in sync across:
- `mobile/package.json` (`version: "1.0.0"`)
- `mobile/android/app/build.gradle` (`versionCode 1`, `versionName "1.0.0"`)
- `mobile/ios/App/App.xcodeproj/project.pbxproj` (`MARKETING_VERSION = 1.0.0`)

---

## 2. Android Release Packaging & Code Signing

### Step 1: Generate Release Keystore
Generate a dedicated 2048-bit RSA release signing key:
```bash
keytool -genkeypair -v -keystore love-release-key.jks -alias love-key-alias -keyalg RSA -keysize 2048 -validity 10000
```
Store `love-release-key.jks` securely in a protected vault. **Never commit keystore files or passwords to version control.**

### Step 2: Configure Gradle Signing
In `mobile/android/app/build.gradle`:
```groovy
android {
    ...
    signingConfigs {
        release {
            storeFile file(System.getenv("LOVE_KEYSTORE_PATH") ?: "love-release-key.jks")
            storePassword System.getenv("LOVE_KEYSTORE_PASSWORD")
            keyAlias System.getenv("LOVE_KEY_ALIAS")
            keyPassword System.getenv("LOVE_KEY_PASSWORD")
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### Step 3: Assemble Signed Android App Bundle (AAB) & APK
```powershell
$env:JAVA_HOME = "F:\Android\Android Studio\jbr"
cd F:\LOVE\mobile\android

# Build Google Play Android App Bundle (AAB)
.\gradlew.bat bundleRelease

# Build Standalone Signed APK
.\gradlew.bat assembleRelease
```
Outputs:
- **AAB**: `mobile/android/app/build/outputs/bundle/release/app-release.aab`
- **APK**: `mobile/android/app/build/outputs/apk/release/app-release.apk`

---

## 3. iOS Release Packaging & App Store Submission

### Step 1: Apple Developer Credentials
- Active Apple Developer Program enrollment.
- Apple Distribution Certificate imported into macOS Keychain.
- App Store Distribution Provisioning Profile for `ai.love.assistant`.

### Step 2: Archive & Export in Xcode
```bash
cd mobile/ios/App
xcodebuild -workspace App.xcworkspace \
  -scheme App \
  -configuration Release \
  -archivePath ./build/LOVE.xcarchive \
  archive
```

### Step 3: Export `.ipa` Package
```bash
xcodebuild -exportArchive \
  -archivePath ./build/LOVE.xcarchive \
  -exportOptionsPlist ExportOptions.plist \
  -exportPath ./build/export
```

### Step 4: Upload via Transporter or Xcode
Submit the generated `LOVE.ipa` to App Store Connect for TestFlight internal/external testing groups or App Store review.

---

## 4. Pre-Release Verification Checklist

Before tagging and publishing any mobile release build:

- [x] All 31 mobile Vitest test suites pass (`npm --prefix mobile run test`).
- [x] All 33 web Vitest tests pass without regressions (`npm --prefix web run test`).
- [x] All 33 desktop Vitest tests pass without regressions (`npm --prefix desktop run test`).
- [x] All 229 backend pytest tests pass against canonical SQLite database (`pytest tests -q`).
- [x] Zero plaintext tokens or credentials exist in `localStorage` or unencrypted preferences.
- [x] Android APK compiles and links successfully (`mobile/android/app/build/outputs/apk/debug/app-debug.apk`).
- [x] All 6 mobile screen states captured and verified in `mobile/screenshots/`.
- [x] Alembic migration head matches canonical database revision (`c0e81b379d42`).
- [x] Database journal mode verified as WAL (`PRAGMA journal_mode=wal`).
- [x] Push notification payloads verified free of conversational text or PII.
- [x] User informed of push-to-talk voice mode (no unauthorized always-on recording).
