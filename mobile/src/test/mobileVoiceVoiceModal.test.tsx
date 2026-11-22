import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MobileVoiceModal } from '../components/voice/MobileVoiceModal';
import { mobileVoiceService } from '../services/voiceService';

describe('LOVE Mobile Voice & Push-to-Talk Modal', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders push-to-talk modal with microphone indicator and privacy notice', () => {
    render(
      <MobileVoiceModal
        isOpen={true}
        onClose={vi.fn()}
        onTranscriptionComplete={vi.fn()}
      />
    );

    expect(screen.getByText('Push-to-Talk Voice Engine')).toBeInTheDocument();
    expect(screen.getByText('Tap to Speak to LOVE')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start Speaking/i })).toBeInTheDocument();
    expect(screen.getByText(/Raw audio recordings are never stored permanently/i)).toBeInTheDocument();
  });

  it('starts and stops recording, transcribing speech through backend voice API', async () => {
    const onCompleteMock = vi.fn();
    const startSpy = vi.spyOn(mobileVoiceService, 'startRecording').mockResolvedValue();
    const stopSpy = vi.spyOn(mobileVoiceService, 'stopRecording').mockResolvedValue(new Blob(['audio'], { type: 'audio/webm' }));
    const transcribeSpy = vi.spyOn(mobileVoiceService, 'transcribeAudio').mockResolvedValue({
      text: 'What is the system status?',
    });

    render(
      <MobileVoiceModal
        isOpen={true}
        onClose={vi.fn()}
        onTranscriptionComplete={onCompleteMock}
      />
    );

    // 1. Click Start Speaking
    fireEvent.click(screen.getByRole('button', { name: /Start Speaking/i }));

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalled();
      expect(screen.getByRole('button', { name: /Stop Recording & Send/i })).toBeInTheDocument();
    });

    // 2. Click Stop Recording
    fireEvent.click(screen.getByRole('button', { name: /Stop Recording & Send/i }));

    await waitFor(() => {
      expect(stopSpy).toHaveBeenCalled();
      expect(transcribeSpy).toHaveBeenCalled();
      expect(onCompleteMock).toHaveBeenCalledWith('What is the system status?');
    });
  });
});
