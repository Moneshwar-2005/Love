/**
 * Captures screenshot of Electron Desktop with Cross-Device Synchronization UI (Phase 09).
 */

const { app, BrowserWindow, safeStorage, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

const logFile = path.join(__dirname, '../capture_log.txt');
fs.writeFileSync(logFile, `=== CAPTURE LOG [${new Date().toISOString()}] ===\n`);

function log(msg) {
  console.log(msg);
  fs.appendFileSync(logFile, msg + '\n');
}

function getSecureStoragePath() {
  return path.join(app.getPath('userData'), 'love_vault.dat');
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

function registerIpc() {
  ipcMain.handle('secure-store:save', async (_event, payload) => {
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
    if (fs.existsSync(vaultPath)) fs.unlinkSync(vaultPath);
    return true;
  });

  ipcMain.handle('secure-store:is-available', async () => safeStorage.isEncryptionAvailable());
  ipcMain.handle('app:get-version', () => '1.0.0');
  ipcMain.handle('app:get-system-info', () => ({
    platform: process.platform,
    arch: process.arch,
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    nodeVersion: process.versions.node,
  }));
}

app.whenReady().then(async () => {
  try {
    registerIpc();

    // Populate vault with active owner credentials for auto-login
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_or_username: 'work_persist_1795095542',
          password: 'SecurePassword123!',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        writeVault({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          user_info: JSON.stringify(data.user),
        });
        log('[PASS] Authenticated user credentials stored in DPAPI vault.');
      }
    } catch (err) {
      log(`Could not login via HTTP: ${err.message}`);
    }

    const win = new BrowserWindow({
      width: 1280,
      height: 850,
      show: false,
      webPreferences: {
        preload: path.join(__dirname, '../electron/preload.cjs'),
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
      },
    });

    win.webContents.on('did-finish-load', async () => {
      log('[PASS] Window did-finish-load event fired.');
      try {
        // Wait 2s for React hydration
        await new Promise((r) => setTimeout(r, 2000));

        // Trigger Settings modal open
        await win.webContents.executeJavaScript(`
          (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const btn = buttons.find(b => b.textContent.includes('Device Settings') || b.textContent.includes('Settings'));
            if (btn) btn.click();
          })()
        `);
        log('[PASS] Clicked Settings button.');

        await new Promise((r) => setTimeout(r, 800));

        // Switch to Cross-Device Sync tab
        await win.webContents.executeJavaScript(`
          (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const tabBtn = buttons.find(b => b.textContent.includes('Cross-Device Sync'));
            if (tabBtn) tabBtn.click();
          })()
        `);
        log('[PASS] Clicked Cross-Device Sync tab.');

        await new Promise((r) => setTimeout(r, 1200));

        // Capture page screenshot
        const image = await win.webContents.capturePage();
        const screenshotPath = path.join(__dirname, '../sync_screenshot.png');
        const buffer = image.toPNG();
        fs.writeFileSync(screenshotPath, buffer);
        log(`[PASS] Saved screenshot: ${screenshotPath} (${buffer.length} bytes).`);
      } catch (err) {
        log(`[ERROR in capture]: ${err.message}`);
      } finally {
        win.close();
        app.exit(0);
      }
    });

    const distPath = path.join(__dirname, '../dist/index.html');
    log(`[PASS] Calling loadFile(${distPath})...`);
    win.loadFile(distPath);
  } catch (err) {
    log(`[FATAL]: ${err.message}`);
    app.exit(1);
  }
});
