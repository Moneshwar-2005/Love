import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VoiceService } from '../services/voiceService';
import { apiClient } from '../services/apiClient';

describe('VoiceService', () => {
  let voice: VoiceService;

  beforeEach(() => {
    voice = new VoiceService();
    vi.restoreAllMocks();
  });

  it('retrieves voice system status', async () => {
    const mockStatus = {
      status: 'active',
      stt_active_provider: 'whisper',
      tts_active_provider: 'piper',
      active_personality_profile: 'assistant',
      wake_word_active: true,
      wake_word_ready: true,
      mic_permission_granted: true,
      hardware_acceleration: true,
    };
    vi.spyOn(apiClient, 'get').mockResolvedValue(mockStatus);

    const status = await voice.getStatus();
    expect(status.wake_word_active).toBe(true);
    expect(status.stt_active_provider).toBe('whisper');
  });

  it('toggles wake-word monitoring', async () => {
    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue({ success: true });

    await voice.toggleWakeWord(true, true);
    expect(postSpy).toHaveBeenCalledWith('/api/v1/voice/wake-word/toggle', {
      active: true,
      mic_permission_granted: true,
    });
  });

  it('sends voice audio turn using FormData', async () => {
    const mockAudioBlob = new Blob(['fake audio content'], { type: 'audio/wav' });
    const mockResponse = {
      transcript: 'Hello LOVE',
      reply_text: 'Hello, how can I assist you?',
      audio_base64: 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=',
      format: 'audio/wav',
      conversation_id: 'conv-voice',
      message_id: 'msg-voice',
      processing_time_ms: 320,
    };

    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockResponse);

    const result = await voice.sendVoiceTurn(mockAudioBlob, {
      conversation_id: 'conv-voice',
    });

    expect(result.transcript).toBe('Hello LOVE');
    expect(result.reply_text).toContain('Hello, how can I assist you?');
    expect(postSpy).toHaveBeenCalledWith(
      '/api/v1/voice/chat',
      expect.any(FormData)
    );
  });
});
