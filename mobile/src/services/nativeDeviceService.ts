/**
 * LOVE Mobile Native Device Integration Service.
 * Manages native status bar, Android hardware back button, keyboard behavior, and safe areas.
 */

import { App } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';
import { Keyboard } from '@capacitor/keyboard';
import { StatusBar, Style } from '@capacitor/status-bar';

export class MobileNativeDeviceService {
  private backButtonListeners: Array<() => boolean> = [];

  async initializeNativeFeatures(): Promise<void> {
    if (!Capacitor.isNativePlatform()) {
      return;
    }

    try {
      // 1. Configure Dark Status Bar
      await StatusBar.setStyle({ style: Style.Dark });
      await StatusBar.setBackgroundColor({ color: '#090a0f' });
      await StatusBar.setOverlaysWebView({ overlay: false });
    } catch (err) {
      console.warn('StatusBar initialization:', err);
    }

    try {
      // 2. Android Hardware Back Button Handling
      App.addListener('backButton', ({ canGoBack }) => {
        // Execute registered top-most back button handler
        for (let i = this.backButtonListeners.length - 1; i >= 0; i--) {
          const handled = this.backButtonListeners[i]();
          if (handled) return;
        }

        if (canGoBack) {
          window.history.back();
        } else {
          App.exitApp();
        }
      });
    } catch (err) {
      console.warn('App backButton listener:', err);
    }

    try {
      // 3. Configure Native Keyboard
      await Keyboard.setAccessoryBarVisible({ isVisible: true });
      await Keyboard.setStyle({ style: 'DARK' as any });
    } catch {
      // Ignored
    }
  }

  /**
   * Registers a back-button handler (e.g. for closing drawers or modals).
   * Returning true indicates the event was consumed and back-navigation is halted.
   */
  registerBackHandler(handler: () => boolean): () => void {
    this.backButtonListeners.push(handler);
    return () => {
      this.backButtonListeners = this.backButtonListeners.filter((h) => h !== handler);
    };
  }
}

export const mobileNativeDeviceService = new MobileNativeDeviceService();
