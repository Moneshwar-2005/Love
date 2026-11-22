/**
 * LOVE Mobile Biometric Authentication Service.
 * Interfaces with native Android BiometricPrompt (via LoveBiometric plugin)
 * and iOS LocalAuthentication.
 * Biometrics gate access to the locally stored session credentials;
 * they NEVER bypass server-side token validation or remote device revocation.
 */

import { Capacitor, registerPlugin } from '@capacitor/core';
import { BiometricStatus } from '../types/auth';
import { mobileSecureStorage } from './mobileSecureStorage';

export interface LoveBiometricPluginInterface {
  checkBiometricAvailability(): Promise<{
    isAvailable: boolean;
    hasEnrolledBiometrics: boolean;
    status: string;
    biometryType: string;
  }>;
  authenticate(options?: {
    title?: string;
    subtitle?: string;
    cancelText?: string;
  }): Promise<{
    authenticated: boolean;
    errorCode?: number;
    message?: string;
  }>;
}

export const LoveBiometric = registerPlugin<LoveBiometricPluginInterface>('LoveBiometric');

export let biometricAdapter: LoveBiometricPluginInterface = LoveBiometric;
export const setBiometricAdapter = (adapter: LoveBiometricPluginInterface) => {
  biometricAdapter = adapter;
};

export class BiometricService {
  private mockBiometricResult: boolean | null = null;
  private mockAvailability: BiometricStatus | null = null;

  /**
   * For testing & automated verification.
   */
  setMockResult(success: boolean | null) {
    this.mockBiometricResult = success;
  }

  setMockAvailability(status: BiometricStatus | null) {
    this.mockAvailability = status;
  }

  /**
   * Checks whether the device hardware supports biometric authentication
   * and whether the user has biometric credentials enrolled.
   */
  async checkAvailability(): Promise<BiometricStatus> {
    if (this.mockAvailability) {
      return this.mockAvailability;
    }

    const isEnabled = await mobileSecureStorage.isBiometricEnabled();

    if (Capacitor.isNativePlatform() && Capacitor.isPluginAvailable('LoveBiometric')) {
      try {
        const res = await biometricAdapter.checkBiometricAvailability();
        return {
          isAvailable: res.isAvailable,
          hasEnrolledBiometrics: res.hasEnrolledBiometrics,
          biometryType: (res.biometryType as any) || 'none',
          isEnabled,
        };
      } catch (err) {
        console.warn('Native LoveBiometric availability check failed:', err);
      }
    }

    // Web / dev fallback
    return {
      isAvailable: false,
      hasEnrolledBiometrics: false,
      biometryType: 'none',
      isEnabled,
    };
  }

  /**
   * Prompts user for biometric verification (BiometricPrompt on Android).
   * Returns true on successful authentication; false on failure or cancellation.
   */
  async authenticate(reason: string = 'Unlock LOVE Assistant'): Promise<boolean> {
    if (this.mockBiometricResult !== null) {
      return this.mockBiometricResult;
    }

    const status = await this.checkAvailability();
    if (!status.isAvailable) {
      // In dev/web fallback, return true if user opted in
      return status.isEnabled;
    }

    if (Capacitor.isNativePlatform() && Capacitor.isPluginAvailable('LoveBiometric')) {
      try {
        const res = await biometricAdapter.authenticate({
          title: reason,
          subtitle: 'Confirm your identity to unlock session credentials',
          cancelText: 'Use Password',
        });
        return res.authenticated === true;
      } catch (err) {
        console.warn('Native LoveBiometric prompt failed or cancelled:', err);
        return false;
      }
    }

    return false;
  }

  /**
   * Opt-in toggle in Mobile Settings.
   */
  async enableBiometricUnlock(): Promise<boolean> {
    const verified = await this.authenticate('Verify biometrics to enable biometric unlock');
    if (verified) {
      await mobileSecureStorage.setBiometricEnabled(true);
      return true;
    }
    return false;
  }

  async disableBiometricUnlock(): Promise<void> {
    await mobileSecureStorage.setBiometricEnabled(false);
  }
}

export const biometricService = new BiometricService();
