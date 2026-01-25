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
    const token = localStorage.getItem('hie_token');
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
    const token = localStorage.getItem('hie_token');
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
};

export default apiV2;
