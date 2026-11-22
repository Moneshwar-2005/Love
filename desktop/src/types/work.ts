export type TaskStatus =
  | 'pending'
  | 'planning'
  | 'in_progress'
  | 'awaiting_approval'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type ActionStatus =
  | 'pending'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'cancelled';

export type ApprovalState =
  | 'not_required'
  | 'pending'
  | 'approved'
  | 'rejected';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface TaskStepPlan {
  step_index: number;
  title: string;
  tool_name: string;
  risk_level: RiskLevel;
  description?: string | null;
}

export interface TaskAction {
  id: string;
  task_id: string;
  step_index: number;
  title: string;
  tool_name: string;
  risk_level: RiskLevel;
  input: Record<string, any>;
  output?: Record<string, any> | null;
  status: ActionStatus;
  approval_state: ApprovalState;
  approved_by?: string | null;
  approved_at?: string | null;
  error_message?: string | null;
  execution_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface Task {
  id: string;
  user_id: string;
  conversation_id?: string | null;
  title: string;
  description: string;
  status: TaskStatus;
  plan: TaskStepPlan[];
  actions: TaskAction[];
  result_summary?: string | null;
  error_message?: string | null;
  total_steps: number;
  completed_steps: number;
  completed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface PendingApproval {
  task_id: string;
  task_title: string;
  action: TaskAction;
}

export interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  risk_level: RiskLevel;
  parameters_schema: Record<string, any>;
  is_available: boolean;
}
