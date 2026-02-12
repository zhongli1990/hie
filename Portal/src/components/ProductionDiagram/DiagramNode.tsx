/**
 * Custom node component for Production Topology
 * Renders service, process, and operation items with NHS styling
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { NodeTypeIcon } from "./NodeTypeIcon";
import type { DiagramNodeData, ItemType } from "./types";

// NHS color palette
const nodeStyles: Record<ItemType, { bg: string; border: string; text: string }> = {
  service: {
    bg: "bg-green-50",
    border: "border-green-600",
    text: "text-green-600",
  },
  process: {
    bg: "bg-blue-50",
    border: "border-nhs-blue",
    text: "text-nhs-blue",
  },
  operation: {
    bg: "bg-purple-50",
    border: "border-purple-600",
    text: "text-purple-600",
  },
};

export const DiagramNode = memo(({ data, selected }: NodeProps<DiagramNodeData>) => {
  const { item, label, status, metrics } = data;
  const styles = nodeStyles[item.item_type];

  // Format metrics for display
  const formatMetric = (value: number): string => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  return (
    <div
      className={`
        rounded-lg border-2 ${styles.border} ${styles.bg}
        px-4 py-3 shadow-md transition-all
        ${selected ? "ring-2 ring-nhs-blue ring-offset-2" : "hover:shadow-lg"}
        min-w-[180px] max-w-[220px]
      `}
    >
      {/* Inbound handle (left) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-gray-400 !w-3 !h-3"
      />

      {/* Header with icon and name */}
      <div className="flex items-start gap-2 mb-2">
        <NodeTypeIcon type={item.item_type} className={`h-5 w-5 ${styles.text} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <div className={`font-semibold text-sm ${styles.text} truncate`} title={label}>
            {label}
          </div>
        </div>
      </div>

      {/* Type description */}
      <div className="text-xs text-gray-600 mb-2 truncate" title={item.class_name}>
        {getTypeDescription(item.class_name)}
      </div>

      {/* Key settings */}
      {item.adapter_settings && Object.keys(item.adapter_settings).length > 0 && (
        <div className="text-xs text-gray-500 mb-2">
          {(item.adapter_settings as any).Port && (
            <div>Port: {String((item.adapter_settings as any).Port)}</div>
          )}
          {(item.adapter_settings as any).IPAddress && (
            <div className="truncate" title={String((item.adapter_settings as any).IPAddress)}>
              {String((item.adapter_settings as any).IPAddress)}
            </div>
          )}
        </div>
      )}

      {/* Status indicator */}
      <div className="flex items-center gap-2 text-xs mb-1">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            status === "running"
              ? "bg-green-500"
              : status === "error"
              ? "bg-red-500"
              : "bg-gray-400"
          }`}
          title={status}
        />
        <span className="text-gray-600 capitalize">{status}</span>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="text-xs text-gray-500">
          📊 {formatMetric(metrics.messages_received || 0)} msg/h
        </div>
      )}

      {/* Outbound handle (right) */}
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-gray-400 !w-3 !h-3"
      />
    </div>
  );
});

DiagramNode.displayName = "DiagramNode";

/**
 * Extract user-friendly type description from class name
 */
function getTypeDescription(className: string): string {
  // Extract from class name like "li.hosts.hl7.HL7TCPService"
  const parts = className.split(".");
  const name = parts[parts.length - 1];

  // Convert camelCase to spaced words
  const spaced = name.replace(/([A-Z])/g, " $1").trim();

  return spaced || className;
}
