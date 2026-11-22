export interface TranscriptionResponse {
  text: string;
  language?: string;
  duration_seconds?: number;
  confidence?: number;
}

export interface VoiceSettings {
  voice_enabled: boolean;
  active_personality: string;
  auto_speak_responses: boolean;
  rate: number;
  pitch: number;
}
