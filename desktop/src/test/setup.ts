import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock window.loveDesktop
window.loveDesktop = {
  platform: 'win32',
  isElectron: true,
  safeStorage: {
    isAvailable: vi.fn().mockResolvedValue(true),
  },
  secureStore: {
    saveToken: vi.fn().mockResolvedValue(true),
    getToken: vi.fn().mockResolvedValue(null),
    removeToken: vi.fn().mockResolvedValue(true),
    clearTokens: vi.fn().mockResolvedValue(true),
  },
  windowControls: {
    minimize: vi.fn().mockResolvedValue(undefined),
    maximize: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
  },
};

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// Mock Audio
global.Audio = vi.fn().mockImplementation(() => ({
  play: vi.fn().mockResolvedValue(undefined),
  pause: vi.fn(),
  onended: null,
  onerror: null,
})) as any;
