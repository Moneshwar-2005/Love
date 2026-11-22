export interface WakeWordStatus {
  active: boolean;
  model_name: string;
  threshold: number;
  model_available: boolean;
  model_path?: string | null;
  mic_permission_granted: boolean;
  message: string;
}

export interface VoiceStatus {
  is_enabled: boolean;
  local_only_mode: boolean;
  stt: {
    active_provider: string;
    name: string;
    is_local: boolean;
    is_configured: boolean;
    is_available: boolean;
    model_info?: any;
    available_providers?: any[];
  };
  tts: {
    active_provider: string;
    name: string;
    is_local: boolean;
    is_configured: boolean;
    is_available: boolean;
    all_providers?: any[];
  };
  wake_word: WakeWordStatus;
  personality: {
    profile_id: string;
    name: string;
    preferred_accent: string;
    style_description: string;
  };
  hardware?: Record<string, any>;
  stt_active_provider?: string;
  tts_active_provider?: string;
  active_personality_profile?: string;
  wake_word_active?: boolean;
}

export interface VoiceChatResponse {
  session_id?: string | null;
  conversation_id: string;
  user_text?: string;
  assistant_text?: string;
  audio_base64?: string | null;
  audio_format?: string;
  latency_ms?: number;
}
