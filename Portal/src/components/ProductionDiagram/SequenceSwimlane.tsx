/**
 * SequenceSwimlane - Individual swimlane column for sequence diagrams
 * Displays a vertical column representing a single project item (Service, Process, or Operation)
 * with a header and a vertical dashed line extending down the timeline
 */

"use client";

export interface SequenceItem {
  itemId: string;
  itemName: string;
  itemType: "service" | "process" | "operation";
  columnIndex: number;
}

interface SequenceSwimlaneProps {
  item: SequenceItem;
  x: number;
  height: number;
  onItemClick?: () => void;
}

// NHS Digital Design System color scheme
const SWIMLANE_COLORS = {
  service: {
    bg: "#E8F5E9",      // Light green
    border: "#4CAF50",  // Green
    header: "#2E7D32",  // Dark green
  },
  process: {
    bg: "#E3F2FD",      // Light blue
    border: "#2196F3",  // Blue
    header: "#1565C0",  // Dark blue
  },
  operation: {
    bg: "#F3E5F5",      // Light purple
    border: "#9C27B0",  // Purple
    header: "#6A1B9A",  // Dark purple
  },
};

const COLUMN_WIDTH = 180;
const HEADER_HEIGHT = 60;
const HEADER_PADDING = 40; // Horizontal padding around header

export function SequenceSwimlane({ item, x, height, onItemClick }: SequenceSwimlaneProps) {
  const colors = SWIMLANE_COLORS[item.itemType];
  const headerWidth = COLUMN_WIDTH - HEADER_PADDING;
  const centerX = headerWidth / 2;

  return (
    <g transform={`translate(${x}, 0)`}>
      {/* Header Box */}
      <rect
        x={0}
        y={0}
        width={headerWidth}
        height={HEADER_HEIGHT}
        fill={colors.bg}
        stroke={colors.border}
        strokeWidth={2}
        rx={4}
        className="cursor-pointer hover:opacity-80 transition-opacity"
        onClick={onItemClick}
      />

      {/* Item Type Label */}
      <text
        x={centerX}
        y={18}
        textAnchor="middle"
        fill={colors.header}
        fontSize={10}
        fontWeight="600"
        className="uppercase tracking-wide"
      >
        {item.itemType}
      </text>

      {/* Item Name */}
      <text
        x={centerX}
        y={38}
        textAnchor="middle"
        fill={colors.header}
        fontSize={14}
        fontWeight="700"
        className="cursor-pointer"
        onClick={onItemClick}
      >
        {truncateText(item.itemName, 16)}
      </text>

      {/* Tooltip on hover (SVG title element) */}
      {item.itemName.length > 16 && (
        <title>{item.itemName}</title>
      )}

      {/* Vertical Dashed Line */}
      <line
        x1={centerX}
        y1={HEADER_HEIGHT}
        x2={centerX}
        y2={height}
        stroke={colors.border}
        strokeWidth={2}
        strokeDasharray="5,5"
        opacity={0.6}
      />

      {/* Connection Point Indicator (small circle at top of line) */}
      <circle
        cx={centerX}
        cy={HEADER_HEIGHT + 5}
        r={4}
        fill={colors.border}
        stroke="white"
        strokeWidth={2}
      />
    </g>
  );
}

/**
 * Truncate text to fit within swimlane width
 */
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 1) + "…";
}
