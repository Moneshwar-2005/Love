export type MemoryCategory = 'core' | 'preferences' | 'knowledge' | 'episodic' | 'contacts' | 'tasks';

export interface MemoryEntry {
  id: string;
  user_id: string;
  category: MemoryCategory;
  key: string;
  value: string;
  importance: number;
  tags: string[];
  source_conversation_id?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface MemorySuggestion {
  id: string;
  user_id: string;
  category: MemoryCategory;
  key: string;
  value: string;
  importance: number;
  reason: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
}
