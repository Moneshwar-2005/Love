/**
 * LOVE Mobile Auth Context.
 * Manages mobile user authentication, session restoration, native secure token lifecycle,
 * and biometric unlock flow.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { LoginPayload, RegisterPayload, User } from '../types/auth';
import { mobileApiClient } from '../services/apiClient';
import { mobileAuthService } from '../services/authService';
import { biometricService } from '../services/biometricService';
import { mobileSecureStorage } from '../services/mobileSecureStorage';

interface MobileAuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isBiometricSupported: boolean;
  isBiometricEnabled: boolean;
  login: (credentials: LoginPayload) => Promise<void>;
  register: (credentials: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  unlockWithBiometrics: () => Promise<boolean>;
  refreshUser: () => Promise<void>;
}

const MobileAuthContext = createContext<MobileAuthContextType | undefined>(undefined);

export const MobileAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isBiometricSupported, setIsBiometricSupported] = useState<boolean>(false);
  const [isBiometricEnabled, setIsBiometricEnabled] = useState<boolean>(false);

  const initAuth = async () => {
    setIsLoading(true);
    try {
      // 1. Check biometric hardware
      const bioStatus = await biometricService.checkAvailability();
      setIsBiometricSupported(bioStatus.isAvailable);
      setIsBiometricEnabled(bioStatus.isEnabled);

      // 2. Check if a stored refresh token exists in secure vault
      const storedToken = await mobileSecureStorage.getSecureItem('refresh_token');
      if (storedToken) {
        // If biometric unlock is enabled, we require explicit biometric verification
        if (bioStatus.isEnabled && bioStatus.isAvailable) {
          // Leave user unauthenticated until biometric unlock or login is triggered
          setUser(null);
        } else {
          // Attempt token refresh
          const refreshed = await mobileAuthService.refresh();
          if (refreshed) {
            const currentUser = await mobileAuthService.getMe();
            setUser(currentUser);
          } else {
            setUser(null);
          }
        }
      } else {
        setUser(null);
      }
    } catch (err) {
      console.warn('Mobile initial session restore check:', err);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    mobileApiClient.setOnUnauthorized(() => {
      setUser(null);
    });
    initAuth();
  }, []);

  const login = async (credentials: LoginPayload) => {
    const resp = await mobileAuthService.login(credentials);
    setUser(resp.user);
  };

  const register = async (credentials: RegisterPayload) => {
    await mobileAuthService.register(credentials);
    await login({
      email_or_username: credentials.email || credentials.username,
      password: credentials.password,
    });
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await mobileAuthService.logout();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const unlockWithBiometrics = async (): Promise<boolean> => {
    const verified = await biometricService.authenticate('Unlock LOVE Assistant');
    if (!verified) {
      return false;
    }

    try {
      const refreshed = await mobileAuthService.refresh();
      if (refreshed) {
        const currentUser = await mobileAuthService.getMe();
        setUser(currentUser);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const refreshUser = async () => {
    try {
      const currentUser = await mobileAuthService.getMe();
      setUser(currentUser);
    } catch {
      setUser(null);
    }
  };

  return (
    <MobileAuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        isBiometricSupported,
        isBiometricEnabled,
        login,
        register,
        logout,
        unlockWithBiometrics,
        refreshUser,
      }}
    >
      {children}
    </MobileAuthContext.Provider>
  );
};

export const useMobileAuth = (): MobileAuthContextType => {
  const context = useContext(MobileAuthContext);
  if (!context) {
    throw new Error('useMobileAuth must be used within a MobileAuthProvider');
  }
  return context;
};
