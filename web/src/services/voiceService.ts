import { apiClient } from './apiClient';
import { VoiceChatResponse, VoiceStatus } from '../types/voice';

export class VoiceService {
  async getStatus(): Promise<VoiceStatus> {
    return await apiClient.get<VoiceStatus>('/api/v1/voice/status');
  }

  async synthesize(text: string, voiceId?: string): Promise<{ audio_base64?: string; format: string }> {
    return await apiClient.post('/api/v1/voice/synthesize', {
      text,
      voice_id: voiceId,
      return_binary: false,
    });
  }

  async sendVoiceTurn(
    audioBlob: Blob,
    options?: {
      conversation_id?: string;
      session_id?: string;
      stt_provider_id?: string;
      tts_provider_id?: string;
      profile_id?: string;
    }
  ): Promise<VoiceChatResponse> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');

    if (options?.conversation_id) {
      formData.append('conversation_id', options.conversation_id);
    }
    if (options?.session_id) {
      formData.append('session_id', options.session_id);
    }
    if (options?.stt_provider_id) {
      formData.append('stt_provider_id', options.stt_provider_id);
    }
    if (options?.tts_provider_id) {
      formData.append('tts_provider_id', options.tts_provider_id);
    }
    if (options?.profile_id) {
      formData.append('profile_id', options.profile_id);
    }

    return await apiClient.post<VoiceChatResponse>('/api/v1/voice/chat', formData);
  }
}

export const voiceService = new VoiceService();
