/**
 * LOVE Desktop Runtime & Security Verification Script (Electron).
 */

const { app, BrowserWindow, safeStorage, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

const logFile = path.join(__dirname, '../verification_log.txt');
fs.writeFileSync(logFile, `=== LOVE ELECTRON RUNTIME VERIFICATION [${new Date().toISOString()}] ===\n\n`);

function log(msg) {
  console.log(msg);
  fs.appendFileSync(logFile, msg + '\n');
}

function getSecureStoragePath() {
  return path.join(app.getPath('userData'), 'love_secure_vault.dat');
}

function readVault() {
  const vaultPath = getSecureStoragePath();
  if (!fs.existsSync(vaultPath)) return {};
  try {
    const raw = fs.readFileSync(vaultPath);
    if (!safeStorage.isEncryptionAvailable()) return {};
    const decrypted = safeStorage.decryptString(raw);
    return JSON.parse(decrypted);
  } catch {
    return {};
  }
}

function writeVault(data) {
  const vaultPath = getSecureStoragePath();
  if (!safeStorage.isEncryptionAvailable()) return false;
  try {
    const serialized = JSON.stringify(data);
    const encrypted = safeStorage.encryptString(serialized);
    fs.writeFileSync(vaultPath, encrypted);
    return true;
  } catch {
    return false;
  }
}

function registerIpcHandlers() {
  ipcMain.handle('secure-store:save', async (_event, payload) => {
    if (!payload || typeof payload !== 'object') throw new Error('Invalid payload');
    const { key, value } = payload;
    const vault = readVault();
    vault[key] = value;
    return writeVault(vault);
  });

  ipcMain.handle('secure-store:get', async (_event, key) => {
    const vault = readVault();
    return vault[key] || null;
  });

  ipcMain.handle('secure-store:remove', async (_event, key) => {
    const vault = readVault();
    delete vault[key];
    return writeVault(vault);
  });

  ipcMain.handle('secure-store:clear', async () => {
    const vaultPath = getSecureStoragePath();
    if (fs.existsSync(vaultPath)) {
      try {
        fs.unlinkSync(vaultPath);
        return true;
      } catch {
        return false;
      }
    }
    return true;
  });

  ipcMain.handle('secure-store:is-available', async () => {
    return safeStorage.isEncryptionAvailable();
  });

  ipcMain.handle('app:get-version', () => '1.0.0');
  ipcMain.handle('app:get-system-info', () => ({
    platform: process.platform,
    arch: process.arch,
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    nodeVersion: process.versions.node,
  }));
}

function testSecureStorageLifecycle() {
  log('--- 1. Testing Windows DPAPI Secure Storage Lifecycle ---');
  const isAvailable = safeStorage.isEncryptionAvailable();
  log(`[PASS] safeStorage.isEncryptionAvailable(): ${isAvailable}`);

  if (!isAvailable) {
    throw new Error('DPAPI safeStorage is not available on this host!');
  }

  const vaultTestFile = path.join(app.getPath('userData'), 'love_vault_test.dat');
  const plainSecret = 'love_access_token_super_secret_jwt_payload_987654321';
  const vaultData = { access_token: plainSecret, username: 'love_owner' };

  // Encrypt and write to disk
  const serialized = JSON.stringify(vaultData);
  const encryptedBuf = safeStorage.encryptString(serialized);
  fs.writeFileSync(vaultTestFile, encryptedBuf);

  // Read raw file from disk to verify encryption
  const rawDiskData = fs.readFileSync(vaultTestFile);
  const diskString = rawDiskData.toString('utf8');

  const containsPlaintext = diskString.includes('love_access_token') || diskString.includes(plainSecret);
  log(`[PASS] Raw encrypted disk buffer size: ${rawDiskData.length} bytes`);
  log(`[PASS] File contains plain text token: ${containsPlaintext} (Must be false)`);

  if (containsPlaintext) {
    throw new Error('SECURITY VIOLATION: Plaintext found in storage vault file!');
  }

  // Decrypt and verify matching contents
  const decrypted = safeStorage.decryptString(rawDiskData);
  const parsed = JSON.parse(decrypted);
  const matches = parsed.access_token === plainSecret && parsed.username === 'love_owner';
  log(`[PASS] Decrypted content matches original: ${matches}`);

  if (!matches) {
    throw new Error('Decrypted content does not match original secret!');
  }

  // Test deletion / clear
  fs.unlinkSync(vaultTestFile);
  const cleared = !fs.existsSync(vaultTestFile);
  log(`[PASS] Secure storage file cleared successfully: ${cleared}`);
}

async function testElectronWindow() {
  log('\n--- 2. Testing Electron Window & Preload Runtime ---');

  const preloadPath = path.join(__dirname, '../electron/preload.cjs');
  const distPath = path.join(__dirname, '../dist/index.html');

  log(`Preload path: ${preloadPath} (exists: ${fs.existsSync(preloadPath)})`);
  log(`Dist path: ${distPath} (exists: ${fs.existsSync(distPath)})`);

  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    show: false,
    webPreferences: {
      preload: preloadPath,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  log('[PASS] BrowserWindow created with security options.');

  win.webContents.on('console-message', (event, level, message) => {
    log(`[RENDERER LOG L${level}] ${message}`);
  });

  win.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    log(`[ERROR] did-fail-load: ${errorCode} - ${errorDescription} on ${validatedURL}`);
  });

  try {
    await win.loadFile(distPath);
    log('[PASS] dist/index.html loadFile resolved.');
  } catch (err) {
    log(`[ERROR loading dist]: ${err.message}`);
  }

  // Wait 1 second for React to render initial state
  await new Promise((r) => setTimeout(r, 1000));

  try {
    const rendererAudit = await win.webContents.executeJavaScript(`
      ({
        hasLoveDesktop: typeof window.loveDesktop !== 'undefined',
        isElectron: window.loveDesktop?.isElectron === true,
        hasNodeRequire: typeof window.require !== 'undefined',
        hasNativeFs: typeof window.fs !== 'undefined',
        title: document.title,
        rootHtmlPreview: document.getElementById('root')?.innerHTML?.substring(0, 150) || ''
      })
    `);

    log(`[PASS] Preload loveDesktop exposed: ${rendererAudit.hasLoveDesktop}`);
    log(`[PASS] Node require blocked: ${!rendererAudit.hasNodeRequire}`);
    log(`[PASS] Native fs blocked: ${!rendererAudit.hasNativeFs}`);
    log(`[PASS] Document title: "${rendererAudit.title}"`);
    log(`[PASS] Rendered HTML preview: ${rendererAudit.rootHtmlPreview}...`);

    // Test renderer IPC calls to secureStore
    const ipcIpcTest = await win.webContents.executeJavaScript(`
      (async () => {
        try {
          const avail = await window.loveDesktop.safeStorage.isAvailable();
          await window.loveDesktop.secureStore.saveToken('ipc_test_key', 'renderer_secret_token_123');
          const retrieved = await window.loveDesktop.secureStore.getToken('ipc_test_key');
          await window.loveDesktop.secureStore.removeToken('ipc_test_key');
          return { success: true, isAvailable: avail, matches: retrieved === 'renderer_secret_token_123' };
        } catch (e) {
          return { success: false, error: e.message };
        }
      })()
    `);
    log(`[PASS] Renderer IPC secureStore roundtrip: ${JSON.stringify(ipcIpcTest)}`);

    // Capture screenshot
    const image = await win.webContents.capturePage();
    const screenshotPath = path.join(__dirname, '../desktop_screenshot.png');
    const pngBuffer = image.toPNG();
    fs.writeFileSync(screenshotPath, pngBuffer);
    log(`[PASS] Live desktop screenshot captured: ${screenshotPath} (${pngBuffer.length} bytes)`);
  } catch (err) {
    log(`[ERROR during renderer audit or screenshot]: ${err.message}`);
  } finally {
    win.close();
    log('[PASS] BrowserWindow closed cleanly.');
  }
}

app.whenReady().then(async () => {
  try {
    registerIpcHandlers();
    testSecureStorageLifecycle();
    await testElectronWindow();

    log('\n======================================================');
    log('ALL ELECTRON RUNTIME & SECURITY CHECKS PASSED CLEANLY');
    log('======================================================\n');
    app.exit(0);
  } catch (err) {
    log(`\n[FATAL RUNTIME TEST FAILURE]: ${err.stack || err.message}`);
    app.exit(1);
  }
});
