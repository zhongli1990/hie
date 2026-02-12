/**
 * Type definitions for Visual Production Topology
 */

import type { ProjectItem, Connection, RoutingRule } from "@/lib/api-v2";

export type { ProjectItem, Connection, RoutingRule };

export type ItemType = "service" | "process" | "operation";

export type ConnectionType = "standard" | "error" | "async";

export type ViewMode = "column" | "graph" | "topology" | "table";

export type ItemStatus = "running" | "stopped" | "error";

export interface ItemMetrics {
  messages_received: number;
  messages_sent: number;
  errors: number;
  avg_latency_ms: number;
  last_updated: string;
}

export interface DiagramNodeData {
  item: ProjectItem;
  label: string;
  className: string;
  enabled: boolean;
  status: ItemStatus;
  metrics?: ItemMetrics;
}

export interface DiagramEdgeData {
  connection: Connection;
  routingRules: RoutingRule[];
}
