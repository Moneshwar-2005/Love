export type AssistantState =
  | 'idle'
  | 'thinking'
  | 'responding'
  | 'listening'
  | 'speaking'
  | 'awaiting_approval'
  | 'offline';

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  is_archived: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  provider?: string | null;
  model?: string | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  latency_ms?: number | null;
  status: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface StreamChunk {
  conversation_id: string;
  message_id: string;
  delta: string;
  role: string;
  provider?: string | null;
  model?: string | null;
  is_done: boolean;
  finish_reason?: string | null;
  status: string;
}

export interface ProviderStatus {
  provider_id: string;
  name: string;
  provider?: string;
  display_name?: string;
  is_configured: boolean;
  is_available: boolean;
  is_local: boolean;
  is_default?: boolean;
  models_count: number;
  models?: string[];
  latency_ms?: number | null;
  error?: string | null;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_window: number;
  max_output_tokens: number;
  supports_streaming: boolean;
  is_local: boolean;
  is_recommended: boolean;
}

export interface HardwareProfile {
  gpu_name?: string | null;
  vram_gb?: number | null;
  is_cuda_available?: boolean | null;
  [key: string]: any;
}

export interface IntelligenceStatus {
  status: string;
  default_provider: string;
  default_model: string;
  routing_preference: string;
  active_routing_policy?: string;
  local_only_mode: boolean;
  active_providers_count: number;
  total_available_models: number;
  providers_available?: number;
  providers_configured?: number;
  fallback_provider?: string | null;
  providers?: ProviderStatus[];
  hardware_profile?: HardwareProfile | null;
}
