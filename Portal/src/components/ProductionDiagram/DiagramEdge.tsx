/**
 * Custom edge component for Production Diagram
 * Renders standard, error, and async connections with NHS styling
 */

import { memo } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "reactflow";
import type { DiagramEdgeData } from "./types";

export const DiagramEdge = memo(
  ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style = {},
    markerEnd,
    data,
  }: EdgeProps<DiagramEdgeData>) => {
    const [edgePath, labelX, labelY] = getBezierPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
    });

    const connectionType = data?.connection?.connection_type || "standard";

    // Edge styles based on connection type
    const edgeStyle = getEdgeStyle(connectionType);
    const edgeLabel = getEdgeLabel(connectionType);

    return (
      <>
        <BaseEdge
          path={edgePath}
          markerEnd={markerEnd}
          style={{ ...edgeStyle, ...style }}
        />
        {edgeLabel && (
          <EdgeLabelRenderer>
            <div
              style={{
                position: "absolute",
                transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                fontSize: 10,
                pointerEvents: "all",
              }}
              className={`
                px-2 py-1 rounded text-white text-xs font-medium
                ${getLabelColorClass(connectionType)}
              `}
            >
              {edgeLabel}
            </div>
          </EdgeLabelRenderer>
        )}
      </>
    );
  }
);

DiagramEdge.displayName = "DiagramEdge";

/**
 * Get edge style based on connection type
 */
function getEdgeStyle(type: string): React.CSSProperties {
  switch (type) {
    case "error":
      return {
        stroke: "#da291c", // nhs-red
        strokeWidth: 2,
        strokeDasharray: "6 4",
      };
    case "async":
      return {
        stroke: "#ffb81c", // nhs-yellow
        strokeWidth: 2,
        strokeDasharray: "2 3",
      };
    default:
      return {
        stroke: "#005eb8", // nhs-blue
        strokeWidth: 2,
      };
  }
}

/**
 * Get edge label based on connection type
 */
function getEdgeLabel(type: string): string | null {
  switch (type) {
    case "error":
      return "Error";
    case "async":
      return "Async";
    default:
      return null;
  }
}

/**
 * Get label background color class
 */
function getLabelColorClass(type: string): string {
  switch (type) {
    case "error":
      return "bg-red-500";
    case "async":
      return "bg-yellow-500";
    default:
      return "bg-nhs-blue";
  }
}
