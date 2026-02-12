/**
 * SequenceArrow - Message flow arrows for sequence diagrams
 * Displays curved arrows between swimlanes showing message flow with timing information
 */

"use client";

export interface SequenceMessage {
  messageId: string;
  sourceItemId: string;
  targetItemId: string;
  timestamp: Date;
  duration_ms: number;
  status: "success" | "error" | "pending";
  transformation?: string;
  inputMessage?: string;
  outputMessage?: string;
}

export interface SwimlanePosition {
  itemId: string;
  x: number;
  width: number;
  centerX: number;
}

interface SequenceArrowProps {
  message: SequenceMessage;
  sourceLane: SwimlanePosition;
  targetLane: SwimlanePosition;
  yPosition: number;
  verticalOffset?: number; // For collision avoidance
  onArrowClick?: () => void;
}

// Message status colors
const MESSAGE_COLORS = {
  success: "#00c853",  // Green
  error: "#da291c",    // Red
  pending: "#ffb81c",  // Yellow
};

export function SequenceArrow({
  message,
  sourceLane,
  targetLane,
  yPosition,
  verticalOffset = 0,
  onArrowClick,
}: SequenceArrowProps) {
  const color = MESSAGE_COLORS[message.status];
  const strokeWidth = message.status === "pending" ? 2 : 3;
  const isDashed = message.status !== "success";

  // Calculate Bezier curve path
  const path = calculateBezierPath(
    sourceLane.centerX,
    targetLane.centerX,
    yPosition + verticalOffset
  );

  // Calculate midpoint for labels
  const midX = (sourceLane.centerX + targetLane.centerX) / 2;
  const labelY = yPosition + verticalOffset;

  return (
    <g
      className="cursor-pointer hover:opacity-80 transition-opacity"
      onClick={onArrowClick}
    >
      {/* Arrow Path */}
      <path
        d={path}
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={isDashed ? "5,5" : "none"}
        fill="none"
        markerEnd="url(#arrowhead)"
      />

      {/* Timing Label (above arrow) */}
      <g>
        {/* Background box for label */}
        <rect
          x={midX - 30}
          y={labelY - 20}
          width={60}
          height={14}
          fill="white"
          fillOpacity={0.9}
          rx={3}
          stroke={color}
          strokeWidth={1}
        />
        <text
          x={midX}
          y={labelY - 10}
          textAnchor="middle"
          fontSize={10}
          fontWeight="600"
          fill={color}
        >
          +{message.duration_ms}ms
        </text>
      </g>

      {/* Transformation Label (below arrow, if applicable) */}
      {message.transformation && (
        <g>
          {/* Background box for transformation label */}
          <rect
            x={midX - 40}
            y={labelY + 8}
            width={80}
            height={14}
            fill="white"
            fillOpacity={0.85}
            rx={3}
            stroke="#999"
            strokeWidth={0.5}
          />
          <text
            x={midX}
            y={labelY + 18}
            textAnchor="middle"
            fontSize={9}
            fontStyle="italic"
            fill="#666"
          >
            {truncateText(message.transformation, 12)}
          </text>
        </g>
      )}

      {/* Hover tooltip */}
      <title>
        {message.status === "success" ? "✓" : message.status === "error" ? "✗" : "⏳"}{" "}
        Message • {message.duration_ms}ms
        {message.transformation ? ` • ${message.transformation}` : ""}
      </title>
    </g>
  );
}

/**
 * Calculate Bezier curve path for arrow
 * Control points at 40% of horizontal distance for smooth curves
 */
function calculateBezierPath(startX: number, endX: number, y: number): string {
  const controlPointOffset = Math.abs(endX - startX) * 0.4;

  // Control points create a horizontal curve
  const cp1x = startX + controlPointOffset;
  const cp1y = y;
  const cp2x = endX - controlPointOffset;
  const cp2y = y;

  return `M ${startX} ${y} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${endX} ${y}`;
}

/**
 * Truncate text to fit within label
 */
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 1) + "…";
}

/**
 * SVG Arrowhead Marker Definition
 * Should be added to the parent SVG <defs> section
 */
export function ArrowheadMarker() {
  return (
    <defs>
      <marker
        id="arrowhead"
        markerWidth="10"
        markerHeight="10"
        refX="9"
        refY="3"
        orient="auto"
        markerUnits="strokeWidth"
      >
        <path d="M0,0 L0,6 L9,3 z" fill="context-stroke" />
      </marker>
    </defs>
  );
}
