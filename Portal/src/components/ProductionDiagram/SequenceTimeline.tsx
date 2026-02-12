/**
 * SequenceTimeline - Vertical time axis for sequence diagrams
 * Displays a timeline with markers showing elapsed time from the start of the sequence
 */

"use client";

interface SequenceTimelineProps {
  height: number;
  scale: number; // px per ms (e.g., 0.2 = 20px per 100ms)
  startTime: Date;
  endTime: Date;
}

const HEADER_HEIGHT = 60; // Must match SequenceSwimlane header height
const MARKER_INTERVAL_MS = 500; // Show a time marker every 500ms

export function SequenceTimeline({ height, scale, startTime, endTime }: SequenceTimelineProps) {
  const durationMs = endTime.getTime() - startTime.getTime();
  const markers = generateTimeMarkers(durationMs, MARKER_INTERVAL_MS);

  return (
    <g transform={`translate(40, 0)`}>
      {/* Timeline Label */}
      <text
        x={0}
        y={30}
        textAnchor="middle"
        fontSize={11}
        fontWeight="600"
        fill="#666"
        className="uppercase tracking-wide"
      >
        Time
      </text>

      {/* Vertical Axis Line */}
      <line
        x1={0}
        y1={HEADER_HEIGHT}
        x2={0}
        y2={height}
        stroke="#ccc"
        strokeWidth={1.5}
      />

      {/* Time Markers */}
      {markers.map((ms) => {
        const yPos = HEADER_HEIGHT + (ms * scale);

        return (
          <g key={ms}>
            {/* Horizontal tick mark */}
            <line
              x1={-6}
              y1={yPos}
              x2={6}
              y2={yPos}
              stroke="#999"
              strokeWidth={1}
            />

            {/* Time label */}
            <text
              x={-12}
              y={yPos + 4}
              textAnchor="end"
              fontSize={10}
              fill="#666"
              fontFamily="monospace"
            >
              {formatTimeLabel(ms)}
            </text>
          </g>
        );
      })}

      {/* Start Time Label (absolute time) */}
      <text
        x={0}
        y={HEADER_HEIGHT - 5}
        textAnchor="middle"
        fontSize={9}
        fill="#999"
      >
        {formatAbsoluteTime(startTime)}
      </text>

      {/* End Time Label (absolute time) */}
      <text
        x={0}
        y={height + 12}
        textAnchor="middle"
        fontSize={9}
        fill="#999"
      >
        {formatAbsoluteTime(endTime)}
      </text>

      {/* Duration Label */}
      <g transform={`translate(0, ${height + 25})`}>
        <rect
          x={-35}
          y={0}
          width={70}
          height={18}
          fill="#f5f5f5"
          stroke="#ddd"
          strokeWidth={1}
          rx={3}
        />
        <text
          x={0}
          y={13}
          textAnchor="middle"
          fontSize={10}
          fontWeight="600"
          fill="#333"
        >
          {formatDuration(durationMs)}
        </text>
      </g>
    </g>
  );
}

/**
 * Generate time marker positions
 * Returns array of millisecond values where markers should be placed
 */
function generateTimeMarkers(durationMs: number, intervalMs: number): number[] {
  const markers: number[] = [];
  let current = 0;

  while (current <= durationMs) {
    markers.push(current);
    current += intervalMs;
  }

  return markers;
}

/**
 * Format time label for markers (relative time)
 * Examples: "0ms", "500ms", "1.0s", "5.5s"
 */
function formatTimeLabel(ms: number): string {
  if (ms === 0) return "0ms";
  if (ms < 1000) return `${ms}ms`;

  const seconds = ms / 1000;
  return `${seconds.toFixed(1)}s`;
}

/**
 * Format absolute time (HH:MM:SS.mmm)
 */
function formatAbsoluteTime(date: Date): string {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  const ms = String(date.getMilliseconds()).padStart(3, "0");

  return `${hours}:${minutes}:${seconds}.${ms}`;
}

/**
 * Format duration for summary label
 * Examples: "450ms", "1.2s", "15.8s"
 */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;

  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}
