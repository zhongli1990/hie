/**
 * Main Production Diagram Component
 * Visual representation of HIE production items and message flow
 */

"use client";

import { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
} from "reactflow";
import "reactflow/dist/style.css";

import { DiagramNode } from "./DiagramNode";
import { DiagramEdge } from "./DiagramEdge";
import { DiagramToolbar } from "./DiagramToolbar";
import { DiagramLegend } from "./DiagramLegend";
import type {
  ProjectItem,
  Connection,
  RoutingRule,
  ViewMode,
  ItemType,
  DiagramNodeData,
  DiagramEdgeData,
} from "./types";

interface ProductionDiagramProps {
  items: ProjectItem[];
  connections: Connection[];
  routingRules?: RoutingRule[];
  onNodeClick?: (itemId: string) => void;
  onUpdatePosition?: (itemId: string, x: number, y: number) => void;
}

// Custom node types for ReactFlow
const nodeTypes = {
  service: DiagramNode,
  process: DiagramNode,
  operation: DiagramNode,
};

// Custom edge types for ReactFlow
const edgeTypes = {
  standard: DiagramEdge,
  error: DiagramEdge,
  async: DiagramEdge,
};

export function ProductionDiagram({
  items,
  connections,
  routingRules = [],
  onNodeClick,
  onUpdatePosition,
}: ProductionDiagramProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("column");
  const [showStatus, setShowStatus] = useState(true);
  const [showMetrics, setShowMetrics] = useState(true);
  const [showLabels, setShowLabels] = useState(true);

  const { fitView, zoomIn, zoomOut } = useReactFlow();

  // Transform items to ReactFlow nodes
  const initialNodes = useMemo(() => {
    return itemsToNodes(items, viewMode);
  }, [items, viewMode]);

  // Transform connections to ReactFlow edges
  const initialEdges = useMemo(() => {
    return connectionsToEdges(connections, routingRules);
  }, [connections, routingRules]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Handle node click
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [onNodeClick]
  );

  // Handle node drag end - update position in backend
  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onUpdatePosition && viewMode === "graph") {
        onUpdatePosition(node.id, node.position.x, node.position.y);
      }
    },
    [onUpdatePosition, viewMode]
  );

  // Handle view mode change
  const handleViewModeChange = useCallback(
    (mode: ViewMode) => {
      setViewMode(mode);
      // Recalculate positions for new view mode
      const updatedNodes = itemsToNodes(items, mode);
      setNodes(updatedNodes);
      // Fit view after layout change
      setTimeout(() => fitView({ duration: 300 }), 50);
    },
    [items, setNodes, fitView]
  );

  // Handle fit view
  const handleFitView = useCallback(() => {
    fitView({ duration: 300, padding: 0.2 });
  }, [fitView]);

  // If table view, show fallback table
  if (viewMode === "table") {
    return (
      <div className="space-y-4">
        <DiagramToolbar
          viewMode={viewMode}
          onViewModeChange={handleViewModeChange}
          onZoomIn={() => {}}
          onZoomOut={() => {}}
          onFitView={() => {}}
          showStatus={showStatus}
          showMetrics={showMetrics}
          showLabels={showLabels}
          onToggleStatus={() => setShowStatus(!showStatus)}
          onToggleMetrics={() => setShowMetrics(!showMetrics)}
          onToggleLabels={() => setShowLabels(!showLabels)}
        />
        <div className="bg-white rounded-lg border p-6">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-4">Name</th>
                <th className="text-left py-2 px-4">Type</th>
                <th className="text-left py-2 px-4">Class</th>
                <th className="text-left py-2 px-4">Status</th>
                <th className="text-left py-2 px-4">Pool Size</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-4">{item.name}</td>
                  <td className="py-2 px-4 capitalize">{item.item_type}</td>
                  <td className="py-2 px-4 text-sm text-gray-600">{item.class_name}</td>
                  <td className="py-2 px-4">
                    <span
                      className={`inline-flex items-center gap-2 text-sm ${
                        item.enabled ? "text-green-600" : "text-gray-400"
                      }`}
                    >
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${
                          item.enabled ? "bg-green-500" : "bg-gray-400"
                        }`}
                      />
                      {item.enabled ? "Running" : "Stopped"}
                    </span>
                  </td>
                  <td className="py-2 px-4">{item.pool_size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <DiagramToolbar
        viewMode={viewMode}
        onViewModeChange={handleViewModeChange}
        onZoomIn={() => zoomIn({ duration: 300 })}
        onZoomOut={() => zoomOut({ duration: 300 })}
        onFitView={handleFitView}
        showStatus={showStatus}
        showMetrics={showMetrics}
        showLabels={showLabels}
        onToggleStatus={() => setShowStatus(!showStatus)}
        onToggleMetrics={() => setShowMetrics(!showMetrics)}
        onToggleLabels={() => setShowLabels(!showLabels)}
      />

      {/* Diagram */}
      <div className="bg-white rounded-lg border shadow-sm" style={{ height: "600px" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onNodeDragStop={handleNodeDragStop}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          attributionPosition="bottom-left"
          nodesDraggable={viewMode === "graph"}
          nodesConnectable={false}
          elementsSelectable={true}
        >
          <Background color="#e5e7eb" gap={16} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      {/* Legend */}
      <DiagramLegend />
    </div>
  );
}

/**
 * Transform ProjectItems to ReactFlow Nodes
 */
function itemsToNodes(items: ProjectItem[], viewMode: ViewMode): Node<DiagramNodeData>[] {
  return items.map((item, index) => {
    const position =
      viewMode === "column"
        ? calculateColumnPosition(item, items)
        : viewMode === "topology"
        ? calculateTopologyPosition(item, items, index)
        : { x: item.position_x || 0, y: item.position_y || 0 };

    return {
      id: item.id,
      type: item.item_type,
      position,
      data: {
        item,
        label: item.name,
        className: item.class_name,
        enabled: item.enabled,
        status: item.enabled ? "running" : "stopped",
        metrics: undefined, // Will be populated by API polling
      },
    };
  });
}

/**
 * Calculate position for column view
 * Services on left, processes in middle, operations on right
 */
function calculateColumnPosition(item: ProjectItem, allItems: ProjectItem[]): { x: number; y: number } {
  const columnMap: Record<ItemType, number> = {
    service: 0,
    process: 1,
    operation: 2,
  };

  const column = columnMap[item.item_type];

  // Get items in same column
  const itemsInColumn = allItems.filter((i) => i.item_type === item.item_type);
  const indexInColumn = itemsInColumn.findIndex((i) => i.id === item.id);

  return {
    x: column * 400 + 50, // 400px column width, 50px margin
    y: indexInColumn * 220 + 50, // 220px vertical spacing, 50px top margin
  };
}

/**
 * Calculate position for topology view
 * Simple hierarchical layout
 */
function calculateTopologyPosition(
  item: ProjectItem,
  allItems: ProjectItem[],
  index: number
): { x: number; y: number } {
  // For now, use same as column view
  // In Phase 3, implement proper Dagre/Elk layout
  return calculateColumnPosition(item, allItems);
}

/**
 * Transform Connections to ReactFlow Edges
 */
function connectionsToEdges(
  connections: Connection[],
  routingRules: RoutingRule[]
): Edge<DiagramEdgeData>[] {
  return connections.map((conn) => ({
    id: conn.id,
    source: conn.source_item_id,
    target: conn.target_item_id,
    type: conn.connection_type || "standard",
    animated: conn.connection_type !== "error",
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: getEdgeColor(conn.connection_type),
    },
    data: {
      connection: conn,
      routingRules: routingRules.filter((rule) =>
        // Match routing rules that target this connection
        rule.target_items.some((targetName) => targetName === conn.target_item_id)
      ),
    },
  }));
}

/**
 * Get edge color based on connection type
 */
function getEdgeColor(type?: string): string {
  switch (type) {
    case "error":
      return "#da291c"; // nhs-red
    case "async":
      return "#ffb81c"; // nhs-yellow
    default:
      return "#005eb8"; // nhs-blue
  }
}
