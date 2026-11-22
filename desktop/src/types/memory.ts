export type MemoryCategory =
  | 'personal'
  | 'project'
  | 'conversational'
  | 'knowledge';

export interface Memory {
  id: string;
  user_id: string;
  key?: string | null;
  content: string;
  category: MemoryCategory;
  tags: string[];
  confidence_score: number;
  source_type: string;
  is_archived: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface MemorySuggestion {
  id: string;
  user_id: string;
  content: string;
  category: MemoryCategory;
  tags: string[];
  confidence: number;
  rationale?: string | null;
  status: 'pending' | 'approved' | 'rejected';
  source_conversation_id?: string | null;
  created_at: string;
}

export interface MemoryStats {
  total_memories: number;
  active_memories: number;
  archived_memories: number;
  categories_breakdown: Record<string, number>;
  vector_store_type: string;
  vector_index_size: number;
  embedding_provider: string;
  embedding_dimension: number;
  cloud_embeddings_permitted: boolean;
}
