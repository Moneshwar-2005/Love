/**
 * LOVE Mobile Notification Service.
 * Manages push token registration, notification preferences, and privacy boundaries.
 * Remote push delivery requires FCM / APNs credentials and is classified as NOT CONFIGURED
 * when credentials are not supplied in backend environment settings.
 */

import { NotificationPreferences, PushTokenRegistration } from '../types/notification';
import { mobileApiClient } from './apiClient';
import { mobileSecureStorage } from './mobileSecureStorage';

const NOTIF_PREFS_KEY = 'love_notification_preferences';

export class MobileNotificationService {
  /**
   * Registers client device push token with the LOVE backend.
   * Associating the push token with the authorized device record.
   */
  async registerPushToken(token: string, platform: 'android' | 'ios'): Promise<boolean> {
    const deviceId = await mobileSecureStorage.getOrCreateDeviceId();
    const payload: PushTokenRegistration = {
      device_id: deviceId,
      token,
      platform,
    };

    try {
      await mobileApiClient.post('/api/v1/devices/notifications/register-token', payload);
      return true;
    } catch {
      // Backend route optional/graceful fallback
      return false;
    }
  }

  async getPreferences(): Promise<NotificationPreferences> {
    const raw = await mobileSecureStorage.getSecureItem(NOTIF_PREFS_KEY);
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        // Fall through
      }
    }

    return {
      enabled: false,
      task_approvals: true,
      task_completions: true,
      security_alerts: true,
    };
  }

  async savePreferences(prefs: NotificationPreferences): Promise<void> {
    await mobileSecureStorage.setSecureItem(NOTIF_PREFS_KEY, JSON.stringify(prefs));
    try {
      await mobileApiClient.put('/api/v1/devices/notifications/preferences', prefs);
    } catch {
      // Offline / local fallback
    }
  }

  /**
   * Request system push notification permission.
   */
  async requestPermission(): Promise<boolean> {
    if (typeof Notification !== 'undefined') {
      const result = await Notification.requestPermission();
      return result === 'granted';
    }
    return false;
  }
}

export const mobileNotificationService = new MobileNotificationService();
