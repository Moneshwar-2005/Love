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
  // Fallbacks for flat representation
  stt_active_provider?: string;
  tts_active_provider?: string;
  active_personality_profile?: string;
  wake_word_active?: boolean;
}

export interface VoiceSession {
  session_id: string;
  user_id: string;
  conversation_id?: string | null;
  state: string;
  wake_word_active: boolean;
  created_at: string;
  updated_at: string;
  error_message?: string | null;
}

export interface VoiceChatResponse {
  session_id?: string | null;
  conversation_id: string;
  user_text?: string;
  assistant_text?: string;
  transcript?: string;
  reply_text?: string;
  transcription?: {
    text: string;
    confidence: number;
    language: string;
    latency_ms: number;
  };
  synthesis?: {
    audio_base64?: string | null;
    format: string;
    latency_ms: number;
    provider_used: string;
  } | null;
  audio_base64?: string | null;
  format?: string;
  approval_required?: boolean;
  pending_action_id?: string | null;
  model_used?: string;
  processing_time_ms?: number;
  latency_ms?: number;
}
