/**
 * HIE API Client v2
 * 
 * Extended API client for workspaces, projects, items, and engine control.
 */

// Types

export interface Workspace {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  tenant_id?: string;
  settings: Record<string, unknown>;
  projects_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface WorkspaceCreate {
  name: string;
  display_name: string;
  description?: string;
  settings?: Record<string, unknown>;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  display_name: string;
  description?: string;
  enabled: boolean;
  state: 'stopped' | 'starting' | 'running' | 'stopping' | 'error';
  version: number;
  settings: Record<string, unknown>;
  items_count: number;
  connections_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectCreate {
  name: string;
  display_name: string;
  description?: string;
  enabled?: boolean;
  settings?: {
    actor_pool_size?: number;
    graceful_shutdown_timeout?: number;
    health_check_interval?: number;
    auto_start?: boolean;
    testing_enabled?: boolean;
  };
}

export interface ProjectDetail extends Project {
  items: ProjectItem[];
  connections: Connection[];
  routing_rules: RoutingRule[];
}

export interface ProjectItem {
  id: string;
  project_id: string;
  name: string;
  display_name?: string;
  item_type: 'service' | 'process' | 'operation';
  class_name: string;
  category?: string;
  enabled: boolean;
  pool_size: number;
  position_x: number;
  position_y: number;
  adapter_settings: Record<string, unknown>;
  host_settings: Record<string, unknown>;
  comment?: string;
  state?: string;
  metrics?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface ItemCreate {
  name: string;
  display_name?: string;
  item_type: 'service' | 'process' | 'operation';
  class_name: string;
  category?: string;
  enabled?: boolean;
  pool_size?: number;
  position?: { x: number; y: number };
  adapter_settings?: Record<string, unknown>;
  host_settings?: Record<string, unknown>;
  comment?: string;
}

export interface Connection {
  id: string;
  project_id: string;
  source_item_id: string;
  target_item_id: string;
  connection_type: 'standard' | 'error' | 'async';
  enabled: boolean;
  filter_expression?: Record<string, unknown>;
  comment?: string;
  created_at?: string;
}

export interface ConnectionCreate {
  source_item_id: string;
  target_item_id: string;
  connection_type?: 'standard' | 'error' | 'async';
  enabled?: boolean;
  filter_expression?: Record<string, unknown>;
  comment?: string;
}

export interface RoutingRule {
  id: string;
  project_id: string;
  name: string;
  enabled: boolean;
  priority: number;
  condition_expression?: string;
  action: 'send' | 'transform' | 'stop' | 'delete';
  target_items: string[];
  transform_name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface RoutingRuleCreate {
  name: string;
  enabled?: boolean;
  priority?: number;
  condition_expression?: string;
  action: 'send' | 'transform' | 'stop' | 'delete';
  target_items?: string[];
  transform_name?: string;
}

export interface ItemTypeDefinition {
  type: string;
  name: string;
  description: string;
  category: 'service' | 'process' | 'operation';
  iris_class_name: string;
  li_class_name: string;
  adapter_settings: SettingDefinition[];
  host_settings: SettingDefinition[];
}

export interface SettingDefinition {
  key: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect' | 'textarea';
  required: boolean;
  default?: unknown;
  options?: { value: string; label: string }[];
  description?: string;
  validation?: { min?: number; max?: number; pattern?: string };
}

export interface DeployResponse {
  status: string;
  engine_id: string;
  state: string;
  items_started: number;
  warnings: string[];
}

export interface ProjectStatus {
  project_id: string;
  state: string;
  engine_id?: string;
  started_at?: string;
  uptime_seconds: number;
  metrics: Record<string, unknown>;
}

export interface ImportResponse {
  status: string;
  project_id: string;
  project_name: string;
  items_imported: number;
  connections_imported: number;
  warnings: string[];
}

// API Client

// Always use relative URLs - Next.js rewrites will proxy to the backend
// This ensures browser requests work correctly in Docker environments
const API_BASE = '';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  
  // Add auth token if available
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('hie-token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new APIError(response.status, error.error || error.message || 'Request failed');
  }

  return response.json();
}

// Workspace APIs

export async function listWorkspaces(): Promise<{ workspaces: Workspace[]; total: number }> {
  return request('/api/workspaces');
}

export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  return request(`/api/workspaces/${workspaceId}`);
}

export async function createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
  return request('/api/workspaces', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateWorkspace(workspaceId: string, data: Partial<WorkspaceCreate>): Promise<Workspace> {
  return request(`/api/workspaces/${workspaceId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteWorkspace(workspaceId: string): Promise<{ status: string }> {
  return request(`/api/workspaces/${workspaceId}`, {
    method: 'DELETE',
  });
}

// Project APIs

export async function listProjects(workspaceId: string): Promise<{ projects: Project[]; total: number }> {
  return request(`/api/workspaces/${workspaceId}/projects`);
}

export async function getProject(workspaceId: string, projectId: string): Promise<ProjectDetail> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}`);
}

export async function createProject(workspaceId: string, data: ProjectCreate): Promise<Project> {
  return request(`/api/workspaces/${workspaceId}/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProject(workspaceId: string, projectId: string, data: Partial<ProjectCreate>): Promise<Project> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteProject(workspaceId: string, projectId: string): Promise<{ status: string }> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}`, {
    method: 'DELETE',
  });
}

// Project Engine Control

export async function deployProject(workspaceId: string, projectId: string, startAfterDeploy = true): Promise<DeployResponse> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}/deploy`, {
    method: 'POST',
    body: JSON.stringify({ start_after_deploy: startAfterDeploy }),
  });
}

export async function startProject(workspaceId: string, projectId: string): Promise<{ status: string; state: string }> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}/start`, {
    method: 'POST',
  });
}

export async function stopProject(workspaceId: string, projectId: string): Promise<{ status: string; state: string }> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}/stop`, {
    method: 'POST',
  });
}

export async function getProjectStatus(workspaceId: string, projectId: string): Promise<ProjectStatus> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}/status`);
}

// Import/Export

export async function importIRISConfig(workspaceId: string, file: File, options?: { project_name?: string; overwrite_existing?: boolean }): Promise<ImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (options) {
    formData.append('options', JSON.stringify(options));
  }
  
  const url = `${API_BASE}/api/workspaces/${workspaceId}/projects/import`;
  
  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('hie-token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new APIError(response.status, error.error || 'Import failed');
  }
  
  return response.json();
}

export async function exportProjectConfig(workspaceId: string, projectId: string): Promise<ProjectDetail> {
  return request(`/api/workspaces/${workspaceId}/projects/${projectId}/export`);
}

// Item APIs

export async function listItems(projectId: string): Promise<{ items: ProjectItem[]; total: number }> {
  return request(`/api/projects/${projectId}/items`);
}

export async function getItem(projectId: string, itemId: string): Promise<ProjectItem> {
  return request(`/api/projects/${projectId}/items/${itemId}`);
}

export async function createItem(projectId: string, data: ItemCreate): Promise<ProjectItem> {
  return request(`/api/projects/${projectId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateItem(projectId: string, itemId: string, data: Partial<ItemCreate>): Promise<ProjectItem> {
  return request(`/api/projects/${projectId}/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteItem(projectId: string, itemId: string): Promise<{ status: string }> {
  return request(`/api/projects/${projectId}/items/${itemId}`, {
    method: 'DELETE',
  });
}

export async function reloadItem(projectId: string, itemId: string): Promise<{ status: string; item_id: string; message?: string; engine_state?: Record<string, unknown> }> {
  return request(`/api/projects/${projectId}/items/${itemId}/reload`, {
    method: 'POST',
  });
}

export interface TestMessageResult {
  status: string;
  item_name: string;
  ack?: string;
  result?: string;
  message_id?: string;
  error?: string;
}

export async function testItem(projectId: string, itemName: string, message?: string): Promise<TestMessageResult> {
  return request(`/api/projects/${projectId}/items/${itemName}/test`, {
    method: 'POST',
    body: message ? JSON.stringify({ message }) : undefined,
  });
}

// Portal Message APIs

export interface PortalMessage {
  id: string;
  project_id: string;
  item_name: string;
  item_type: string;
  direction: string;
  message_type: string | null;
  correlation_id: string | null;
  session_id: string | null;
  status: string;
  content_preview: string | null;
  content_size: number;
  source_item: string | null;
  destination_item: string | null;
  remote_host: string | null;
  remote_port: number | null;
  ack_type: string | null;
  error_message: string | null;
  latency_ms: number | null;
  retry_count: number;
  received_at: string;
  completed_at: string | null;
}

export interface PortalMessageDetail extends PortalMessage {
  raw_content_base64?: string;
  raw_content_text?: string;
  ack_content_base64?: string;
  ack_content_text?: string;
}

export interface PortalMessageListResponse {
  messages: PortalMessage[];
  total: number;
  limit: number;
  offset: number;
}

export interface PortalMessageStats {
  total: number;
  successful: number;
  failed: number;
  processing: number;
  inbound: number;
  outbound: number;
  avg_latency_ms: number | null;
}

export interface SessionSummary {
  session_id: string;
  message_count: number;
  started_at: string;
  ended_at: string;
  success_rate: number; // 0.0 to 1.0
  message_types: string[];
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
}

// V2 trace message (IRIS convention: one row per message leg)
export interface TraceMessage {
  id: string;
  sequence_num: number;
  source_config_name: string;
  target_config_name: string;
  source_business_type: string;
  target_business_type: string;
  message_type: string | null;
  body_class_name: string;
  type: string; // "Request" | "Response"
  status: string;
  is_error: boolean;
  error_status: string | null;
  time_created: string;
  time_processed: string | null;
  latency_ms: number | null;
  content_preview: string | null;
  correlation_id: string | null;
  description: string | null;
  parent_header_id: string | null;
  corresponding_header_id: string | null;
  session_id: string;
  hl7_doc_type: string | null;
}

export interface SessionTrace {
  session_id: string;
  messages: (PortalMessage | TraceMessage)[];
  items: Array<{ item_name: string; item_type: string }>;
  started_at: string | null;
  ended_at: string | null;
  trace_version?: "v1" | "v2";
}

export async function listMessages(
  projectId: string,
  options?: {
    item?: string;
    status?: string;
    type?: string;
    direction?: string;
    limit?: number;
    offset?: number;
  }
): Promise<PortalMessageListResponse> {
  const params = new URLSearchParams();
  if (options?.item) params.set('item', options.item);
  if (options?.status) params.set('status', options.status);
  if (options?.type) params.set('type', options.type);
  if (options?.direction) params.set('direction', options.direction);
  if (options?.limit) params.set('limit', String(options.limit));
  if (options?.offset) params.set('offset', String(options.offset));
  
  const query = params.toString();
  return request(`/api/projects/${projectId}/messages${query ? `?${query}` : ''}`);
}

export async function getMessage(projectId: string, messageId: string): Promise<PortalMessageDetail> {
  return request(`/api/projects/${projectId}/messages/${messageId}`);
}

export async function getMessageStats(projectId: string): Promise<PortalMessageStats> {
  return request(`/api/projects/${projectId}/messages/stats`);
}

export async function resendMessage(projectId: string, messageId: string): Promise<{ status: string; message_id: string; ack?: string }> {
  return request(`/api/projects/${projectId}/messages/${messageId}/resend`, {
    method: 'POST',
  });
}

// Session APIs

export async function listSessions(
  projectId: string,
  options?: {
    item?: string;
    limit?: number;
    offset?: number;
  }
): Promise<SessionListResponse> {
  const params = new URLSearchParams();
  if (options?.item) params.set('item', options.item);
  if (options?.limit) params.set('limit', options.limit.toString());
  if (options?.offset) params.set('offset', options.offset.toString());

  const query = params.toString();
  const url = `/api/projects/${projectId}/sessions${query ? `?${query}` : ''}`;

  return request(url);
}

export async function getSessionTrace(sessionId: string): Promise<SessionTrace> {
  return request(`/api/sessions/${sessionId}/trace`);
}

// Connection APIs

export async function listConnections(projectId: string): Promise<{ connections: Connection[]; total: number }> {
  return request(`/api/projects/${projectId}/connections`);
}

export async function createConnection(projectId: string, data: ConnectionCreate): Promise<Connection> {
  return request(`/api/projects/${projectId}/connections`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateConnection(projectId: string, connectionId: string, data: Partial<ConnectionCreate>): Promise<Connection> {
  return request(`/api/projects/${projectId}/connections/${connectionId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteConnection(projectId: string, connectionId: string): Promise<{ status: string }> {
  return request(`/api/projects/${projectId}/connections/${connectionId}`, {
    method: 'DELETE',
  });
}

// Routing Rule APIs

export async function listRoutingRules(projectId: string): Promise<{ routing_rules: RoutingRule[]; total: number }> {
  return request(`/api/projects/${projectId}/routing-rules`);
}

export async function createRoutingRule(projectId: string, data: RoutingRuleCreate): Promise<RoutingRule> {
  return request(`/api/projects/${projectId}/routing-rules`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateRoutingRule(projectId: string, ruleId: string, data: Partial<RoutingRuleCreate>): Promise<RoutingRule> {
  return request(`/api/projects/${projectId}/routing-rules/${ruleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteRoutingRule(projectId: string, ruleId: string): Promise<{ status: string }> {
  return request(`/api/projects/${projectId}/routing-rules/${ruleId}`, {
    method: 'DELETE',
  });
}

// Item Type Registry

export async function listItemTypes(category?: string): Promise<{ item_types: ItemTypeDefinition[] }> {
  const query = category ? `?category=${category}` : '';
  return request(`/api/item-types${query}`);
}

export async function getItemType(typeId: string): Promise<ItemTypeDefinition> {
  return request(`/api/item-types/${typeId}`);
}

export async function getItemTypeByClass(className: string): Promise<ItemTypeDefinition> {
  return request(`/api/item-types/by-class?class_name=${encodeURIComponent(className)}`);
}

// Dashboard Types
export interface DashboardStats {
  projects_count: number;
  projects_running: number;
  items_count: number;
  items_services: number;
  items_processes: number;
  items_operations: number;
  messages_today: number;
  messages_total: number;
  messages_failed: number;
  error_rate: number;
  message_trend: number;
  uptime_percent: number;
}

export interface DashboardThroughput {
  period: string;
  bucket_minutes: number;
  data: Array<{
    time: string;
    total: number;
    inbound: number;
    outbound: number;
  }>;
  peak: number;
  average: number;
}

export interface DashboardActivity {
  id: string;
  type: 'message' | 'error' | 'state_change';
  description: string;
  project_name: string;
  item_name: string;
  timestamp: string;
}

export interface DashboardProject {
  id: string;
  name: string;
  display_name: string;
  state: string;
  enabled: boolean;
  items_count: number;
  message_count: number;
  error_count: number;
  items: Array<{
    id: string;
    name: string;
    type: string;
    enabled: boolean;
    class_name: string;
    message_count: number;
    error_count: number;
  }>;
}

// Dashboard APIs
export async function getDashboardStats(): Promise<DashboardStats> {
  return request('/api/dashboard/stats');
}

export async function getDashboardThroughput(period: string = '1h'): Promise<DashboardThroughput> {
  return request(`/api/dashboard/throughput?period=${period}`);
}

export async function getDashboardActivity(limit: number = 10): Promise<{ activities: DashboardActivity[]; total: number }> {
  return request(`/api/dashboard/activity?limit=${limit}`);
}

export async function getDashboardProjects(): Promise<{ projects: DashboardProject[]; total: number }> {
  return request('/api/dashboard/projects');
}

// Monitoring Types
export interface MonitoringMetrics {
  messages_per_second: number;
  avg_latency_ms: number;
  p99_latency_ms: number;
  error_rate: number;
  queue_depth: number;
  messages_last_hour: number;
  errors_last_hour: number;
  timestamp: string;
}

export interface MonitoringThroughputPoint {
  time: string;
  total: number;
  inbound: number;
  outbound: number;
  errors: number;
  avg_latency: number;
}

export interface MonitoringThroughput {
  minutes: number;
  data: MonitoringThroughputPoint[];
  total_messages: number;
  total_errors: number;
}

export interface MonitoringItem {
  name: string;
  type: string;
  direction: string;
  message_count: number;
  error_count: number;
  avg_latency_ms: number;
  max_latency_ms: number;
  error_rate: number;
}

export interface MonitoringProject {
  id: string;
  name: string;
  state: string;
  messages_processed: number;
  messages_per_second: number;
  avg_latency_ms: number;
  error_rate: number;
  status: 'healthy' | 'warning' | 'critical';
}

// Monitoring APIs
export async function getMonitoringMetrics(): Promise<MonitoringMetrics> {
  return request('/api/monitoring/metrics');
}

export async function getMonitoringThroughput(minutes: number = 30): Promise<MonitoringThroughput> {
  return request(`/api/monitoring/throughput?minutes=${minutes}`);
}

export async function getMonitoringItems(): Promise<{ items: MonitoringItem[]; total: number }> {
  return request('/api/monitoring/items');
}

export async function getMonitoringProjects(): Promise<{ projects: MonitoringProject[]; total: number }> {
  return request('/api/monitoring/projects');
}

// Export all
export const apiV2 = {
  // Workspaces
  listWorkspaces,
  getWorkspace,
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
  // Projects
  listProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  // Engine Control
  deployProject,
  startProject,
  stopProject,
  getProjectStatus,
  // Import/Export
  importIRISConfig,
  exportProjectConfig,
  // Items
  listItems,
  getItem,
  createItem,
  updateItem,
  deleteItem,
  // Connections
  listConnections,
  createConnection,
  updateConnection,
  deleteConnection,
  // Routing Rules
  listRoutingRules,
  createRoutingRule,
  updateRoutingRule,
  deleteRoutingRule,
  // Item Types
  listItemTypes,
  getItemType,
  getItemTypeByClass,
  // Portal Messages
  listMessages,
  getMessage,
  getMessageStats,
  resendMessage,
};

export default apiV2;
