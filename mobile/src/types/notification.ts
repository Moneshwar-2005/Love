export interface NotificationPreferences {
  enabled: boolean;
  task_approvals: boolean;
  task_completions: boolean;
  security_alerts: boolean;
}

export interface PushTokenRegistration {
  device_id: string;
  token: string;
  platform: 'android' | 'ios';
}

export interface PushNotificationPayload {
  title: string;
  body: string;
  data: {
    type: 'task_approval' | 'task_completion' | 'security_alert' | 'general';
    id?: string;
    risk_level?: string;
  };
}
