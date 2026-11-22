const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('loveDesktop', {
  platform: process.platform,
  isElectron: true,
  safeStorage: {
    isAvailable: () => ipcRenderer.invoke('secure-store:is-available'),
  },
  secureStore: {
    saveToken: (key, value) => ipcRenderer.invoke('secure-store:save', { key, value }),
    getToken: (key) => ipcRenderer.invoke('secure-store:get', key),
    removeToken: (key) => ipcRenderer.invoke('secure-store:remove', key),
    clearTokens: () => ipcRenderer.invoke('secure-store:clear'),
  },
  windowControls: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
  },
});
