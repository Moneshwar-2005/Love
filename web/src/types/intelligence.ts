export type MessageRole = 'user' | 'assistant' | 'system';

export type AssistantState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'executing'
  | 'awaiting_approval'
  | 'offline';

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  provider?: string | null;
  model?: string | null;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  origin_device_id?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface StreamChunk {
  delta: string;
  is_done: boolean;
  message_id?: string;
  conversation_id?: string;
  tokens?: number;
  provider?: string;
  model?: string;
  latency_ms?: number;
}

export interface ProviderStatus {
  id: string;
  name: string;
  is_configured: boolean;
  is_available: boolean;
  is_local: boolean;
  default_model: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_length: number;
  is_local: boolean;
  capabilities: string[];
}

export interface IntelligenceStatus {
  active_provider: string;
  active_model: string;
  routing_preference: string;
  local_only_mode: boolean;
  providers_available: number;
  total_providers: number;
}
