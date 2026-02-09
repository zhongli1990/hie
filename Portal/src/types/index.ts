// HIE Portal Type Definitions

export type ItemCategory = "service" | "process" | "operation";
export type ConnectionType = "standard" | "error" | "async";
export type ProductionState = "running" | "stopped" | "paused" | "error" | "starting" | "stopping";
export type ItemState = "running" | "stopped" | "paused" | "error" | "starting" | "stopping";

export interface Position {
  x: number;
  y: number;
}

export interface FilterCondition {
  field: string;
  operator: string;
  value: unknown;
}

export interface FilterGroup {
  logic: "and" | "or";
  conditions: (FilterCondition | FilterGroup)[];
}

export interface ItemSettings {
  poolSize?: number;
  queueSize?: number;
  timeout?: number;
  retryCount?: number;
  retryInterval?: number;
  [key: string]: unknown;
}

export interface Item {
  id: string;
  name: string;
  type: string;
  category: ItemCategory;
  className?: string;
  enabled: boolean;
  displayCategory?: string;
  comment?: string;
  settings: ItemSettings;
  position?: Position;
  // Runtime state
  state?: ItemState;
  metrics?: ItemMetrics;
}

export interface ItemMetrics {
  messagesReceived: number;
  messagesProcessed: number;
  messagesFailed: number;
  messagesInQueue: number;
  avgLatencyMs: number;
  lastMessageAt?: string;
  lastErrorAt?: string;
  lastErrorMessage?: string;
}

export interface Connection {
  id: string;
  source: string;
  target: string;
  type: ConnectionType;
  filter?: FilterGroup;
  enabled: boolean;
  comment?: string;
  waypoints?: Position[];
}

export interface RoutingRule {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  filter?: FilterGroup;
  targets: string[];
  transform?: string;
  stopProcessing: boolean;
}

export interface ProductionSettings {
  actorPoolSize: number;
  gracefulShutdownTimeout: number;
  healthCheckInterval: number;
  autoStart: boolean;
  testingEnabled: boolean;
}

export interface Production {
  name: string;
  description: string;
  enabled: boolean;
  settings: ProductionSettings;
  items: Item[];
  connections: Connection[];
  routingRules: RoutingRule[];
  createdAt?: string;
  updatedAt?: string;
  createdBy?: string;
  version: number;
  // Runtime state
  state?: ProductionState;
  metrics?: ProductionMetrics;
}

export interface ProductionMetrics {
  totalMessagesReceived: number;
  totalMessagesProcessed: number;
  totalMessagesFailed: number;
  itemsRunning: number;
  itemsError: number;
  uptimeSeconds: number;
}

export interface SystemHealth {
  services: ServiceHealth[];
}

export interface ServiceHealth {
  service: string;
  status: "healthy" | "unhealthy" | "unreachable";
  latencyMs: number | null;
}

export interface DashboardStats {
  productionsCount: number;
  itemsCount: number;
  messagesProcessedToday: number;
  messagesProcessedTotal: number;
  errorRate: number;
  recentActivity: ActivityItem[];
}

export interface ActivityItem {
  type: "message" | "error" | "config_change" | "state_change";
  description: string;
  productionName?: string;
  itemName?: string;
  timestamp: string;
}

// Item type definitions for the item library
export interface ItemTypeDefinition {
  type: string;
  name: string;
  description: string;
  category: ItemCategory;
  icon: string;
  settings: SettingDefinition[];
}

export interface SettingDefinition {
  key: string;
  label: string;
  type: "string" | "number" | "boolean" | "select" | "multiselect" | "textarea";
  required: boolean;
  default?: unknown;
  options?: { value: string; label: string }[];
  description?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
}
