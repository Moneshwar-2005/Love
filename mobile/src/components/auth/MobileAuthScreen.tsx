import React, { useState, useEffect } from 'react';
import { useMobileAuth } from '../../context/AuthContext';
import { mobileApiClient } from '../../services/apiClient';
import { Fingerprint, Globe, KeyRound, Lock, Mail, Shield, User } from 'lucide-react';

export function formatAuthError(err: any): string {
  if (!err) return 'Authentication failed. Please try again.';
  const rawMsg = err.message || (typeof err === 'string' ? err : '');

  // Network failures
  if (
    rawMsg.includes('Network failure') ||
    rawMsg.includes('Failed to fetch') ||
    rawMsg.includes('NetworkError') ||
    rawMsg.includes('fetch failed') ||
    err.status === 0
  ) {
    return 'LOVE cannot connect to the server. Please try again.';
  }

  // Rate limiting / lockouts
  if (
    rawMsg.includes('temporarily locked') ||
    rawMsg.includes('Too Many Requests') ||
    rawMsg.includes('Rate limit') ||
    err.status === 429
  ) {
    return 'Account is temporarily locked due to multiple failed attempts. Please try again later.';
  }

  // Invalid credentials
  if (
    rawMsg.includes('Invalid email/username or password') ||
    rawMsg.includes('Invalid credentials') ||
    err.status === 401
  ) {
    return 'Invalid email/username or password.';
  }

  // Validation errors
  if (
    rawMsg.includes('string_pattern_mismatch') ||
    rawMsg.includes('pattern') ||
    (rawMsg.includes('username') && (rawMsg.includes('valid') || rawMsg.includes('format') || rawMsg.includes('alphanumeric')))
  ) {
    return 'Please enter a valid username.';
  }
  if (
    rawMsg.includes('email') &&
    (rawMsg.includes('valid') || rawMsg.includes('format') || rawMsg.includes('value_error'))
  ) {
    return 'Please enter a valid email address.';
  }
  if (
    rawMsg.includes('fill in all') ||
    rawMsg.includes('required') ||
    rawMsg.includes('empty') ||
    rawMsg.includes('complete the required')
  ) {
    return 'Please complete the required fields.';
  }

  // Fallback: if raw JSON / Pydantic / traceback, map to friendly message
  if (rawMsg.startsWith('{') || rawMsg.startsWith('[') || rawMsg.includes('Traceback') || rawMsg.includes('body.')) {
    if (rawMsg.includes('username')) return 'Please enter a valid username.';
    if (rawMsg.includes('email')) return 'Please enter a valid email address.';
    if (rawMsg.includes('password')) return 'Please enter a valid password.';
    return 'Authentication failed. Please verify your credentials and try again.';
  }

  return rawMsg || 'Authentication failed. Please verify credentials and server reachability.';
}

export const MobileAuthScreen: React.FC = () => {
  const { login, register, unlockWithBiometrics, isBiometricSupported, isBiometricEnabled } = useMobileAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [emailOrUsername, setEmailOrUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [serverUrl, setServerUrl] = useState<string>(mobileApiClient.getBaseUrl());
  const [showServerConfig, setShowServerConfig] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    const syncUrl = () => {
      const current = mobileApiClient.getBaseUrl();
      if (current) {
        setServerUrl(current);
      }
    };
    syncUrl();
    const timer = setTimeout(syncUrl, 300);
    return () => clearTimeout(timer);
  }, []);

  const switchToMode = (targetMode: 'login' | 'register') => {
    setErrorMsg(null);
    if (targetMode === 'login' && mode === 'register') {
      // Transfer username or email to login field if available
      if (!emailOrUsername.trim()) {
        setEmailOrUsername(username.trim() || email.trim());
      }
    } else if (targetMode === 'register' && mode === 'login') {
      // Transfer login field to email or username
      const val = emailOrUsername.trim();
      if (val.includes('@')) {
        if (!email.trim()) setEmail(val);
      } else {
        if (!username.trim()) setUsername(val);
      }
    }
    setMode(targetMode);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      if (serverUrl && serverUrl.trim()) {
        await mobileApiClient.setBaseUrl(serverUrl.trim());
      }

      if (mode === 'register') {
        const normEmail = email.trim();
        const normUsername = username.trim();

        if (!normEmail || !normUsername || !password) {
          throw new Error('Please complete the required fields.');
        }

        await register({
          email: normEmail,
          username: normUsername,
          password, // NEVER trimmed or modified
        });
      } else {
        const normIdentifier = emailOrUsername.trim();

        if (!normIdentifier || !password) {
          throw new Error('Please complete the required fields.');
        }

        await login({
          email_or_username: normIdentifier,
          password, // NEVER trimmed or modified
        });
      }
    } catch (err: any) {
      setErrorMsg(formatAuthError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBiometricUnlock = async () => {
    setErrorMsg(null);
    try {
      const success = await unlockWithBiometrics();
      if (!success) {
        setErrorMsg('Biometric verification failed or was cancelled.');
      }
    } catch (err: any) {
      setErrorMsg(formatAuthError(err));
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-center px-6 py-8 overflow-y-auto bg-background">
      <div className="w-full max-w-sm mx-auto space-y-6">
        {/* Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-lg shadow-cyan-500/10">
            <span className="text-2xl font-black tracking-tighter">L</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">LOVE</h1>
          <p className="text-xs text-slate-400 font-medium">Independent Sovereign Personal AI Assistant</p>
        </div>

        {/* Segmented Mode Selector Tab */}
        <div role="tablist" className="flex rounded-xl bg-background-secondary p-1 border border-border-subtle">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            aria-label="Sign In Tab"
            onClick={() => switchToMode('login')}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition ${
              mode === 'login'
                ? 'bg-cyan-500 text-slate-950 shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            aria-label="Create Account Tab"
            onClick={() => switchToMode('register')}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition ${
              mode === 'register'
                ? 'bg-cyan-500 text-slate-950 shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Biometric Unlock Option (Login Mode Only) */}
        {isBiometricSupported && isBiometricEnabled && mode === 'login' && (
          <div className="p-4 rounded-2xl bg-cyan-950/30 border border-cyan-500/30 text-center space-y-3">
            <div className="flex items-center justify-center gap-2 text-cyan-400 text-xs font-semibold">
              <Shield className="w-4 h-4" />
              <span>Biometric Session Available</span>
            </div>
            <button
              type="button"
              onClick={handleBiometricUnlock}
              className="w-full py-2.5 px-4 rounded-xl bg-cyan-500 text-slate-950 font-semibold text-xs flex items-center justify-center gap-2 hover:bg-cyan-400 transition"
            >
              <Fingerprint className="w-4 h-4" />
              <span>Unlock with Biometrics</span>
            </button>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' ? (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@example.com"
                    required
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Username</label>
                <div className="relative">
                  <User className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="username"
                    required
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </>
          ) : (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Username or Email</label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={emailOrUsername}
                  onChange={(e) => setEmailOrUsername(e.target.value)}
                  placeholder="username or email"
                  required
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-background-secondary border border-border-subtle text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          {/* Server URL Config Toggle */}
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowServerConfig(!showServerConfig)}
              className="text-[11px] text-slate-400 hover:text-cyan-400 flex items-center gap-1.5 transition"
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Backend Endpoint: {serverUrl}</span>
            </button>
            {showServerConfig && (
              <div className="mt-2 p-3 rounded-xl bg-background-secondary border border-border-subtle space-y-1.5">
                <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Server Base URL (IP / Host)
                </label>
                <input
                  type="url"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="https://10.0.2.2:8000"
                  className="w-full px-2.5 py-1.5 rounded-lg bg-background-tertiary border border-border-subtle text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                />
                <p className="text-[10px] text-slate-500">
                  Android Emulator: <code className="text-cyan-300">https://10.0.2.2:8000</code> • Physical Device: LAN IP (e.g. <code className="text-cyan-300">https://192.168.0.176:8000</code>)
                </p>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs hover:bg-cyan-400 transition disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20"
          >
            <KeyRound className="w-4 h-4" />
            <span>{isSubmitting ? 'Authenticating...' : mode === 'register' ? 'Create Account' : 'Sign In'}</span>
          </button>
        </form>

        {/* Mode Toggle Footer */}
        <div className="text-center pt-1">
          <button
            type="button"
            onClick={() => switchToMode(mode === 'login' ? 'register' : 'login')}
            className="py-1 px-3 text-xs text-slate-400 hover:text-cyan-400 transition"
          >
            {mode === 'login' ? 'Need an owner account? Register' : 'Already have an account? Sign In'}
          </button>
        </div>
      </div>
    </div>
  );
};
