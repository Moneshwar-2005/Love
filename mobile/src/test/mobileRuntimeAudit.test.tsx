/**
 * LOVE Phase 12.5 — Mobile Runtime, Keystore & Device Security Audit Test Suite.
 * Validates native Keystore encryption plugin binding, BiometricPrompt integration,
 * audio container compatibility, network resilience, and token leakage protections.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mobileSecureStorage, setKeystoreAdapter } from '../services/mobileSecureStorage';
import { biometricService, setBiometricAdapter } from '../services/biometricService';
import { mobileVoiceService } from '../services/voiceService';
import { mobileApiClient } from '../services/apiClient';
import { mobileNotificationService } from '../services/notificationService';
import { Capacitor } from '@capacitor/core';

describe('LOVE Phase 12.5: Native Mobile Runtime & Security Verification', () => {
  beforeEach(async () => {
    vi.restoreAllMocks();
    await mobileSecureStorage.clearSecureStore();
  });

  describe('1. Android Keystore Hardware-Backed Storage Plugin Integration', () => {
    it('dispatches to LoveKeystore plugin when running on native platform', async () => {
      vi.spyOn(Capacitor, 'isNativePlatform').mockReturnValue(true);
      vi.spyOn(Capacitor, 'isPluginAvailable').mockReturnValue(true);

      const setSpy = vi.fn().mockResolvedValue({ success: true });
      const getSpy = vi.fn().mockResolvedValue({ value: 'encrypted-token-xyz' });
      setKeystoreAdapter({
        setSecureItem: setSpy,
        getSecureItem: getSpy,
        removeSecureItem: vi.fn().mockResolvedValue({ success: true }),
        clearSecureStore: vi.fn().mockResolvedValue({ success: true }),
        isHardwareBacked: vi.fn().mockResolvedValue({ isHardwareBacked: true, provider: 'AndroidKeyStore' }),
      });

      await mobileSecureStorage.setSecureItem('refresh_token', 'my-secret-refresh-token');
      expect(setSpy).toHaveBeenCalledWith({
        key: 'love_sec_vault_refresh_token',
        value: 'my-secret-refresh-token',
      });

      const retrieved = await mobileSecureStorage.getSecureItem('refresh_token');
      expect(getSpy).toHaveBeenCalledWith({
        key: 'love_sec_vault_refresh_token',
      });
      expect(retrieved).toBe('encrypted-token-xyz');
    });

    it('queries hardware-backed status via LoveKeystore', async () => {
      vi.spyOn(Capacitor, 'isNativePlatform').mockReturnValue(true);
      vi.spyOn(Capacitor, 'isPluginAvailable').mockReturnValue(true);

      const hwSpy = vi.fn().mockResolvedValue({
        isHardwareBacked: true,
        provider: 'AndroidKeyStore',
      });
      setKeystoreAdapter({
        setSecureItem: vi.fn(),
        getSecureItem: vi.fn(),
        removeSecureItem: vi.fn(),
        clearSecureStore: vi.fn(),
        isHardwareBacked: hwSpy,
      });

      const isHw = await mobileSecureStorage.isHardwareBacked();
      expect(hwSpy).toHaveBeenCalled();
      expect(isHw).toBe(true);
    });

    it('falls back gracefully to in-memory store in non-native / test environments without crashing', async () => {
      vi.spyOn(Capacitor, 'isNativePlatform').mockReturnValue(false);

      await mobileSecureStorage.setSecureItem('test_key', 'test_val');
      const val = await mobileSecureStorage.getSecureItem('test_key');
      expect(val).toBe('test_val');

      await mobileSecureStorage.removeSecureItem('test_key');
      const removed = await mobileSecureStorage.getSecureItem('test_key');
      expect(removed).toBeNull();
    });
  });

  describe('2. Native BiometricPrompt & BiometricManager Hardware Binding', () => {
    it('queries LoveBiometric plugin for hardware availability and enrolled biometrics', async () => {
      vi.spyOn(Capacitor, 'isNativePlatform').mockReturnValue(true);
      vi.spyOn(Capacitor, 'isPluginAvailable').mockReturnValue(true);
      biometricService.setMockAvailability(null);

      const checkSpy = vi.fn().mockResolvedValue({
        isAvailable: true,
        hasEnrolledBiometrics: true,
        status: 'BIOMETRIC_SUCCESS',
        biometryType: 'fingerprint',
      });
      setBiometricAdapter({
        checkBiometricAvailability: checkSpy,
        authenticate: vi.fn(),
      });

      const status = await biometricService.checkAvailability();
      expect(checkSpy).toHaveBeenCalled();
      expect(status.isAvailable).toBe(true);
      expect(status.hasEnrolledBiometrics).toBe(true);
      expect(status.biometryType).toBe('fingerprint');
    });

    it('invokes native BiometricPrompt and returns true upon successful biometric scan', async () => {
      vi.spyOn(Capacitor, 'isNativePlatform').mockReturnValue(true);
      vi.spyOn(Capacitor, 'isPluginAvailable').mockReturnValue(true);
      biometricService.setMockResult(null);

      const authSpy = vi.fn().mockResolvedValue({
        authenticated: true,
      });
      setBiometricAdapter({
        checkBiometricAvailability: vi.fn().mockResolvedValue({
          isAvailable: true,
          hasEnrolledBiometrics: true,
          status: 'BIOMETRIC_SUCCESS',
          biometryType: 'fingerprint',
        }),
        authenticate: authSpy,
      });

      const success = await biometricService.authenticate('Unlock LOVE');
      expect(authSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Unlock LOVE',
          cancelText: 'Use Password',
        })
      );
      expect(success).toBe(true);
    });

    it('returns false when user cancels BiometricPrompt or prompt times out', async () => {
      vi.spyOn(Capacitor, 'isNativePlatform').mockReturnValue(true);
      vi.spyOn(Capacitor, 'isPluginAvailable').mockReturnValue(true);
      biometricService.setMockResult(null);

      const authSpy = vi.fn().mockResolvedValue({
        authenticated: false,
        errorCode: 10, // ERROR_USER_CANCELED
        message: 'User cancelled biometric prompt',
      });
      setBiometricAdapter({
        checkBiometricAvailability: vi.fn().mockResolvedValue({
          isAvailable: true,
          hasEnrolledBiometrics: true,
          status: 'BIOMETRIC_SUCCESS',
          biometryType: 'fingerprint',
        }),
        authenticate: authSpy,
      });

      const success = await biometricService.authenticate('Unlock LOVE');
      expect(success).toBe(false);
    });
  });

  describe('3. Mobile Audio & Backend Transcription Schema Compliance', () => {
    it('uses correct "file" parameter name when uploading audio to /api/v1/voice/transcribe', async () => {
      const mockPost = vi.spyOn(mobileApiClient, 'post').mockResolvedValue({
        text: 'Hello LOVE Assistant',
        language: 'en',
        confidence: 0.98,
        duration_seconds: 2.5,
      });

      const fakeAudioBlob = new Blob(['fake-audio-bytes'], { type: 'audio/webm' });
      const result = await mobileVoiceService.transcribeAudio(fakeAudioBlob);

      expect(mockPost).toHaveBeenCalledTimes(1);
      const [url, formData] = mockPost.mock.calls[0];
      expect(url).toBe('/api/v1/voice/transcribe');
      expect(formData).toBeInstanceOf(FormData);

      // Verify FormData has 'file' field (not 'audio')
      const uploadedFile = (formData as FormData).get('file');
      expect(uploadedFile).not.toBeNull();
      expect(result.text).toBe('Hello LOVE Assistant');
    });
  });

  describe('4. Token Security & Leakage Prevention', () => {
    it('strictly maintains access tokens in-memory without leaking to localStorage or sessionStorage', async () => {
      mobileApiClient.setAccessToken('super-secret-access-token-12345');

      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('token')).toBeNull();
      expect(sessionStorage.getItem('access_token')).toBeNull();
      expect(mobileApiClient.getAccessToken()).toBe('super-secret-access-token-12345');

      mobileApiClient.setAccessToken(null);
      expect(mobileApiClient.getAccessToken()).toBeNull();
    });

    it('clears stored refresh credentials completely upon logout', async () => {
      await mobileSecureStorage.setSecureItem('refresh_token', 'valid-refresh-token-999');
      expect(await mobileSecureStorage.getSecureItem('refresh_token')).toBe('valid-refresh-token-999');

      await mobileSecureStorage.removeSecureItem('refresh_token');
      expect(await mobileSecureStorage.getSecureItem('refresh_token')).toBeNull();
    });
  });

  describe('5. Push Notification Privacy & Payload Safeguards', () => {
    it('registers push tokens with device_id and platform without transmitting personal conversation content', async () => {
      const postSpy = vi.spyOn(mobileApiClient, 'post').mockResolvedValue({ success: true });

      const registered = await mobileNotificationService.registerPushToken('device-fcm-token-abc', 'android');
      expect(registered).toBe(true);

      const [url, payload] = postSpy.mock.calls[0];
      expect(url).toBe('/api/v1/devices/notifications/register-token');
      expect(payload).toHaveProperty('device_id');
      expect(payload).toHaveProperty('token', 'device-fcm-token-abc');
      expect(payload).toHaveProperty('platform', 'android');

      // Verify payload contains NO user messages, memories, or PII
      expect(payload).not.toHaveProperty('messages');
      expect(payload).not.toHaveProperty('conversations');
      expect(payload).not.toHaveProperty('memory');
    });
  });
});
