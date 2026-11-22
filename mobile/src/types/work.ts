export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'awaiting_approval';
export type ActionRiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type ActionStatus = 'pending' | 'awaiting_approval' | 'running' | 'completed' | 'failed' | 'rejected';

export interface TaskPlanStep {
  step: number;
  description: string;
  tool?: string;
  risk_level: ActionRiskLevel;
}

export interface TaskAction {
  id: string;
  task_id: string;
  step_index: number;
  title: string;
  tool_name: string;
  risk_level: ActionRiskLevel;
  input: Record<string, any>;
  output?: Record<string, any> | null;
  status: ActionStatus;
  approval_state?: 'pending' | 'approved' | 'rejected' | null;
  error?: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  plan: TaskPlanStep[];
  actions: TaskAction[];
  total_steps: number;
  completed_steps: number;
  created_at: string;
  updated_at?: string | null;
}

export interface PendingApproval {
  task_id: string;
  task_title: string;
  action: TaskAction;
}

export interface CreateTaskPayload {
  title: string;
  description: string;
  auto_execute?: boolean;
}
