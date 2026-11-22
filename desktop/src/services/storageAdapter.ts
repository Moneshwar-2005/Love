/**
 * Secure Storage Adapter for LOVE Desktop.
 *
 * In Electron desktop mode: uses the native OS-level DPAPI encrypted storage via IPC.
 * In browser/test mode: uses an in-memory session vault (never plain-text localStorage).
 */

class SecureStorageAdapter {
  private inMemoryVault: Map<string, string> = new Map();

  async setItem(key: string, value: string): Promise<boolean> {
    if (typeof window !== 'undefined' && window.loveDesktop?.secureStore) {
      try {
        return await window.loveDesktop.secureStore.saveToken(key, value);
      } catch (err) {
        console.warn('Native secureStore failed, falling back to memory vault:', err);
      }
    }
    this.inMemoryVault.set(key, value);
    return true;
  }

  async getItem(key: string): Promise<string | null> {
    if (typeof window !== 'undefined' && window.loveDesktop?.secureStore) {
      try {
        return await window.loveDesktop.secureStore.getToken(key);
      } catch (err) {
        console.warn('Native secureStore failed, falling back to memory vault:', err);
      }
    }
    return this.inMemoryVault.get(key) || null;
  }

  async removeItem(key: string): Promise<boolean> {
    if (typeof window !== 'undefined' && window.loveDesktop?.secureStore) {
      try {
        return await window.loveDesktop.secureStore.removeToken(key);
      } catch (err) {
        console.warn('Native secureStore failed, falling back to memory vault:', err);
      }
    }
    this.inMemoryVault.delete(key);
    return true;
  }

  async clear(): Promise<boolean> {
    if (typeof window !== 'undefined' && window.loveDesktop?.secureStore) {
      try {
        return await window.loveDesktop.secureStore.clearTokens();
      } catch (err) {
        console.warn('Native secureStore failed, falling back to memory vault:', err);
      }
    }
    this.inMemoryVault.clear();
    return true;
  }
}

export const secureStorage = new SecureStorageAdapter();
