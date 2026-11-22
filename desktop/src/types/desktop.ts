export interface LoveDesktopAPI {
  platform: string;
  isElectron: boolean;
  safeStorage: {
    isAvailable: () => Promise<boolean>;
  };
  secureStore: {
    saveToken: (key: string, value: string) => Promise<boolean>;
    getToken: (key: string) => Promise<string | null>;
    removeToken: (key: string) => Promise<boolean>;
    clearTokens: () => Promise<boolean>;
  };
  windowControls: {
    minimize: () => Promise<void>;
    maximize: () => Promise<void>;
    close: () => Promise<void>;
  };
}

declare global {
  interface Window {
    loveDesktop?: LoveDesktopAPI;
  }
}
