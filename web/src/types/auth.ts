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
  device_type?: 'web' | 'windows' | 'macos' | 'linux' | 'android' | 'ios' | 'other';
  client_version?: string;
}
