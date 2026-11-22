export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_owner: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse extends AuthTokens {
  user: User;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  setup_token?: string;
}

export interface LoginPayload {
  email_or_username: string;
  password: string;
  device_identifier?: string;
  device_name?: string;
  device_type?: 'android' | 'ios' | 'web' | 'windows' | 'macos' | 'linux' | 'other';
  client_version?: string;
}

export interface BiometricStatus {
  isAvailable: boolean;
  hasEnrolledBiometrics: boolean;
  biometryType: 'fingerprint' | 'face' | 'iris' | 'none';
  isEnabled: boolean;
}

export interface DeviceInfo {
  id: string;
  device_identifier: string;
  device_name: string;
  device_type: string;
  client_version?: string | null;
  is_trusted: boolean;
  is_revoked: boolean;
  revoked_at?: string | null;
  last_seen_at?: string | null;
  created_at: string;
}
