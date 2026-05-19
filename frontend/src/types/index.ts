export type WakeState = "idle" | "listening" | "processing" | "responding";

export type Mode = "voice" | "text";

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  attendees?: string[];
  source: "google" | "outlook";
}

export interface EmailItem {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  received: string;
  priority: number;
  source: "gmail" | "outlook";
  unread: boolean;
}

export interface MessageItem {
  id: string;
  from: string;
  text: string;
  channel?: string;
  received: string;
  source: "slack" | "teams" | "whatsapp";
}

export interface TaskItem {
  id: string;
  title: string;
  due?: string;
  status: string;
  source: "linear" | "jira" | "notion" | "github";
  url?: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}

export interface ConnectorStatus {
  name: string;
  connected: boolean;
  configured: boolean;
  display: string;
}

export type PanelKey = "calendar" | "email" | "tasks" | "projects";

export interface ToastItem {
  id: string;
  type: "success" | "error" | "info" | "warning";
  message: string;
  duration?: number;
}
