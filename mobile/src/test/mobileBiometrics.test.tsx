import { describe, it, expect, vi, beforeEach } from 'vitest';
import { biometricService } from '../services/biometricService';
import { mobileSecureStorage } from '../services/mobileSecureStorage';

describe('LOVE Mobile Biometric Authentication & Session Gating', () => {
  beforeEach(async () => {
    vi.restoreAllMocks();
    biometricService.setMockResult(null);
    biometricService.setMockAvailability(null);
    await mobileSecureStorage.clearSecureStore();
  });

  it('detects biometric availability and hardware enrollment', async () => {
    biometricService.setMockAvailability({
      isAvailable: true,
      hasEnrolledBiometrics: true,
      biometryType: 'fingerprint',
      isEnabled: false,
    });

    const status = await biometricService.checkAvailability();
    expect(status.isAvailable).toBe(true);
    expect(status.hasEnrolledBiometrics).toBe(true);
    expect(status.biometryType).toBe('fingerprint');
    expect(status.isEnabled).toBe(false);
  });

  it('authenticates user successfully on valid biometric verification', async () => {
    biometricService.setMockResult(true);

    const verified = await biometricService.authenticate('Unlock LOVE Assistant');
    expect(verified).toBe(true);
  });

  it('rejects authentication on cancelled or failed biometric scan', async () => {
    biometricService.setMockResult(false);

    const verified = await biometricService.authenticate('Unlock LOVE Assistant');
    expect(verified).toBe(false);
  });

  it('enables and disables biometric unlock preference with explicit biometric gating', async () => {
    // 1. Enabling with success
    biometricService.setMockResult(true);
    const enabled = await biometricService.enableBiometricUnlock();
    expect(enabled).toBe(true);

    let isStored = await mobileSecureStorage.isBiometricEnabled();
    expect(isStored).toBe(true);

    // 2. Disabling
    await biometricService.disableBiometricUnlock();
    isStored = await mobileSecureStorage.isBiometricEnabled();
    expect(isStored).toBe(false);
  });

  it('does not enable biometric unlock if user verification fails', async () => {
    biometricService.setMockResult(false);
    const enabled = await biometricService.enableBiometricUnlock();
    expect(enabled).toBe(false);

    const isStored = await mobileSecureStorage.isBiometricEnabled();
    expect(isStored).toBe(false);
  });
});
