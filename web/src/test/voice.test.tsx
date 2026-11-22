import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../context/AppContext';
import { AuthProvider } from '../context/AuthContext';
import { VoiceWorkspace } from '../components/voice/VoiceWorkspace';
import { voiceService } from '../services/voiceService';

describe('Web Voice Engine & Push-to-Talk', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders voice workspace with honest wake-word privacy disclosure', async () => {
    vi.spyOn(voiceService, 'getStatus').mockResolvedValue({
      is_enabled: true,
      local_only_mode: true,
      stt: {
        active_provider: 'whisper',
        name: 'Whisper Local',
        is_local: true,
        is_configured: true,
        is_available: true,
      },
      tts: {
        active_provider: 'piper',
        name: 'Piper Neural TTS',
        is_local: true,
        is_configured: true,
        is_available: true,
      },
      wake_word: {
        active: false,
        model_name: 'hey_love',
        threshold: 0.5,
        model_available: false,
        mic_permission_granted: false,
        message: 'Acoustic model not installed',
      },
      personality: {
        profile_id: 'default',
        name: 'LOVE Core',
        preferred_accent: 'British RP',
        style_description: 'Calm, articulate, efficient',
      },
    });

    render(
      <AuthProvider>
        <AppProvider>
          <VoiceWorkspace />
        </AppProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Voice Engine & Speech Interaction')).toBeInTheDocument();
      expect(screen.getByText('Wake-Word Status Notice')).toBeInTheDocument();
      expect(screen.getByText(/hey_love.onnx/i)).toBeInTheDocument();
      expect(screen.getByText('British RP')).toBeInTheDocument();
      expect(screen.getByText('Click microphone to speak')).toBeInTheDocument();
    });
  });
});
