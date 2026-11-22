export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  role?: string;
  is_active: boolean;
  is_verified?: boolean;
  is_owner: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface TokenRefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  username_or_email: string;
  password: string;
  device_name?: string;
  device_type?: string;
}

export interface RegisterCredentials {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  setup_token?: string;
}
