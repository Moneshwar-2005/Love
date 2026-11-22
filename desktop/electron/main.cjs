const { app, BrowserWindow, ipcMain, safeStorage, session } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow = null;

// Determine secure token store file path in userData directory
function getSecureStoragePath() {
  const userDataDir = app.getPath('userData');
  return path.join(userDataDir, 'love_vault.dat');
}

// Read and decrypt secure storage using Windows DPAPI safeStorage
function readVault() {
  const vaultPath = getSecureStoragePath();
  if (!fs.existsSync(vaultPath)) {
    return {};
  }
  try {
    const rawData = fs.readFileSync(vaultPath);
    if (!safeStorage.isEncryptionAvailable()) {
      console.error('[SECURITY ALERT] DPAPI safeStorage is not available. Refusing unencrypted credential storage.');
      throw new Error('DPAPI secure storage unavailable on this host');
    }
    const decrypted = safeStorage.decryptString(rawData);
    return JSON.parse(decrypted);
  } catch (err) {
    console.error('Failed to read or decrypt secure vault:', err.message);
    return {};
  }
}

// Encrypt and write secure storage
function writeVault(vault) {
  const vaultPath = getSecureStoragePath();
  try {
    if (!safeStorage.isEncryptionAvailable()) {
      console.error('[SECURITY ALERT] safeStorage encryption is unavailable. Refusing unencrypted write.');
      throw new Error('DPAPI secure storage unavailable on this host');
    }
    const serialized = JSON.stringify(vault);
    const encrypted = safeStorage.encryptString(serialized);
    fs.writeFileSync(vaultPath, encrypted);
    return true;
  } catch (err) {
    console.error('Failed to encrypt or write vault:', err.message);
    return false;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 1024,
    minHeight: 700,
    frame: true,
    title: 'LOVE — Personal AI Assistant',
    backgroundColor: '#090a0f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  // Apply strict Content Security Policy (CSP) headers
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self' http://localhost:8000 http://127.0.0.1:8000; " +
          "script-src 'self' 'unsafe-inline'; " +
          "style-src 'self' 'unsafe-inline'; " +
          "img-src 'self' data: https:; " +
          "media-src 'self' blob: data: http://localhost:8000 http://127.0.0.1:8000; " +
          "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 ws://localhost:8000 ws://127.0.0.1:8000;"
        ],
      },
    });
  });

  // Security: Block unexpected external popups or window.open attempts
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    console.warn('[SECURITY] Blocked window.open to:', url);
    return { action: 'deny' };
  });

  // Security: Prevent navigation away from the local application
  mainWindow.webContents.on('will-navigate', (event, url) => {
    const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
    try {
      const parsedUrl = new URL(url);
      const allowedDevOrigins = ['http://localhost:5173', 'http://127.0.0.1:5173'];
      if (isDev && allowedDevOrigins.includes(parsedUrl.origin)) {
        return;
      }
      if (url.startsWith('file://')) {
        return;
      }
    } catch {
      // Invalid URL format
    }
    event.preventDefault();
    console.warn('[SECURITY] Blocked unexpected navigation to:', url);
  });

  if (process.env.ELECTRON_CAPTURE_SYNC === '1') {
    mainWindow.webContents.on('did-finish-load', async () => {
      console.log('[ELECTRON CAPTURE] Page did-finish-load');
      try {
        await new Promise((r) => setTimeout(r, 2500));
        await mainWindow.webContents.executeJavaScript(`
          (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const devBtn = buttons.find(b => b.innerText && b.innerText.includes('Device Settings'));
            if (devBtn) devBtn.click();
          })()
        `);
        await new Promise((r) => setTimeout(r, 800));
        await mainWindow.webContents.executeJavaScript(`
          (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const syncBtn = buttons.find(b => b.innerText && b.innerText.includes('Cross-Device Sync'));
            if (syncBtn) syncBtn.click();
          })()
        `);
        await new Promise((r) => setTimeout(r, 1200));
        const syncImg = await mainWindow.webContents.capturePage();
        fs.writeFileSync(path.join(__dirname, '../sync_screenshot.png'), syncImg.toPNG());
        console.log('[ELECTRON CAPTURE] Saved sync_screenshot.png');

        await mainWindow.webContents.executeJavaScript(`
          (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const closeBtn = buttons.find(b => b.innerText && b.innerText.trim() === 'Close');
            if (closeBtn) closeBtn.click();
          })()
        `);
        await new Promise((r) => setTimeout(r, 800));
        const dashImg = await mainWindow.webContents.capturePage();
        fs.writeFileSync(path.join(__dirname, '../dashboard_screenshot.png'), dashImg.toPNG());
        console.log('[ELECTRON CAPTURE] Saved dashboard_screenshot.png');
      } catch (err) {
        console.error('[ELECTRON CAPTURE ERROR]', err);
      } finally {
        app.quit();
      }
    });
  }

  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  if (isDev && process.env.ELECTRON_START_DEV === '1') {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    // Production / Direct load from dist/
    const distPath = path.join(__dirname, '../dist/index.html');
    mainWindow.loadFile(distPath);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers for Safe Storage & Token Vault with strict input validation
ipcMain.handle('secure-store:save', async (_event, payload) => {
  if (!payload || typeof payload !== 'object') {
    throw new Error('Invalid payload: expected object');
  }
  const { key, value } = payload;
  if (typeof key !== 'string' || !/^[a-zA-Z0-9_\-\.]+$/.test(key) || key.length > 128) {
    throw new Error('Invalid key: must be alphanumeric string under 128 chars');
  }
  if (typeof value !== 'string') {
    throw new Error('Invalid value: must be string');
  }
  const vault = readVault();
  vault[key] = value;
  return writeVault(vault);
});

ipcMain.handle('secure-store:get', async (_event, key) => {
  if (typeof key !== 'string' || !/^[a-zA-Z0-9_\-\.]+$/.test(key)) {
    throw new Error('Invalid key format');
  }
  const vault = readVault();
  return vault[key] || null;
});

ipcMain.handle('secure-store:remove', async (_event, key) => {
  if (typeof key !== 'string' || !/^[a-zA-Z0-9_\-\.]+$/.test(key)) {
    throw new Error('Invalid key format');
  }
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

// Window controls
ipcMain.handle('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});
ipcMain.handle('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});
ipcMain.handle('window:close', () => {
  if (mainWindow) mainWindow.close();
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
