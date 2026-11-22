/**
 * LOVE Mobile Voice Service.
 * Implements permission-gated push-to-talk recording, transcription upload, and speech playback.
 * Continuous "Hey LOVE" wake word is explicitly disabled on mobile for battery and privacy.
 */

import { TranscriptionResponse, VoiceSettings } from '../types/voice';
import { mobileApiClient } from './apiClient';

export class MobileVoiceService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private mediaStream: MediaStream | null = null;
  private recordedMimeType: string = 'audio/webm';
  private recordedExtension: string = 'webm';

  private getSupportedMimeType(): { mimeType: string; extension: string } {
    if (typeof MediaRecorder !== 'undefined') {
      if (typeof MediaRecorder.isTypeSupported === 'function') {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          return { mimeType: 'audio/webm;codecs=opus', extension: 'webm' };
        }
        if (MediaRecorder.isTypeSupported('audio/webm')) {
          return { mimeType: 'audio/webm', extension: 'webm' };
        }
        if (MediaRecorder.isTypeSupported('audio/mp4')) {
          return { mimeType: 'audio/mp4', extension: 'm4a' };
        }
        if (MediaRecorder.isTypeSupported('audio/aac')) {
          return { mimeType: 'audio/aac', extension: 'aac' };
        }
      }
    }
    return { mimeType: 'audio/webm', extension: 'webm' };
  }

  async requestPermission(): Promise<boolean> {
    try {
      if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return false;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Close immediate test stream
      stream.getTracks().forEach((t) => t.stop());
      return true;
    } catch (err) {
      console.warn('Microphone permission request rejected:', err);
      return false;
    }
  }

  async startRecording(): Promise<void> {
    const hasPermission = await this.requestPermission();
    if (!hasPermission) {
      throw new Error('Microphone permission not granted');
    }

    const { mimeType, extension } = this.getSupportedMimeType();
    this.recordedMimeType = mimeType;
    this.recordedExtension = extension;

    this.audioChunks = [];
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    try {
      this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: this.recordedMimeType });
    } catch {
      // Fallback if specific codec option rejected
      this.mediaRecorder = new MediaRecorder(this.mediaStream);
    }

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.start();
  }

  async stopRecording(): Promise<Blob> {
    return new Promise<Blob>((resolve, reject) => {
      if (!this.mediaRecorder) {
        return reject(new Error('MediaRecorder is not initialized'));
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: this.recordedMimeType });
        this.audioChunks = [];

        if (this.mediaStream) {
          this.mediaStream.getTracks().forEach((track) => track.stop());
          this.mediaStream = null;
        }

        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  async transcribeAudio(audioBlob: Blob): Promise<TranscriptionResponse> {
    const formData = new FormData();
    // Use 'file' parameter expected by backend transcribe endpoint
    const fileName = `recording.${this.recordedExtension}`;
    formData.append('file', audioBlob, fileName);

    return await mobileApiClient.post<TranscriptionResponse>('/api/v1/voice/transcribe', formData);
  }

  async synthesizeSpeech(text: string): Promise<ArrayBuffer> {
    const fullUrl = `${mobileApiClient.getBaseUrl()}/api/v1/voice/synthesize`;
    const response = await fetch(fullUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${mobileApiClient.getAccessToken() || ''}`,
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error(`Speech synthesis failed with status ${response.status}`);
    }

    return await response.arrayBuffer();
  }

  async getVoiceSettings(): Promise<VoiceSettings> {
    return {
      voice_enabled: true,
      active_personality: 'love_classic',
      auto_speak_responses: false,
      rate: 1.0,
      pitch: 1.0,
    };
  }
}

export const mobileVoiceService = new MobileVoiceService();
