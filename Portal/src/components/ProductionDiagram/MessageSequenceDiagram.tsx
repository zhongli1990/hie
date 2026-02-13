/**
 * MessageSequenceDiagram - IRIS HealthConnect-style sequence diagram
 * Displays end-to-end message flow with vertical swimlanes and horizontal arrows
 */

"use client";

import { useState, useEffect } from "react";
import { X, ZoomIn, ZoomOut, Download, Maximize } from "lucide-react";
import { SequenceSwimlane, type SequenceItem } from "./SequenceSwimlane";
import { SequenceArrow, type SequenceMessage, type SwimlanePosition, ArrowheadMarker } from "./SequenceArrow";
import { SequenceTimeline } from "./SequenceTimeline";
import { getSessionTrace, type SessionTrace, type TraceMessage } from "@/lib/api-v2";

interface MessageSequenceDiagramProps {
  sessionId: string;
  projectId?: string;
  onClose: () => void;
}

interface SequenceDiagramData {
  sessionId: string;
  items: SequenceItem[];
  messages: SequenceMessage[];
  timeRange: { start: Date; end: Date };
}

// Layout constants
const COLUMN_WIDTH = 180;
const HEADER_HEIGHT = 60;
const MARGIN_LEFT = 100; // Space for timeline
const MARGIN_RIGHT = 50;
const MARGIN_TOP = 20;
const MARGIN_BOTTOM = 80;
const TIME_SCALE = 0.2; // 20px per 100ms

export function MessageSequenceDiagram({ sessionId, projectId, onClose }: MessageSequenceDiagramProps) {
  const [sequenceData, setSequenceData] = useState<SequenceDiagramData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1.0);

  // Fetch and transform trace data
  useEffect(() => {
    fetchSequenceData(sessionId);
  }, [sessionId]);

  async function fetchSequenceData(sessionId: string) {
    try {
      setLoading(true);
      setError(null);

      const traceData = await getSessionTrace(sessionId);
      const sequenceData = buildSequenceDiagram(traceData);

      setSequenceData(sequenceData);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sequence diagram");
      setLoading(false);
    }
  }

  function handleExport() {
    if (!sequenceData) return;

    // Export as JSON
    const dataStr = JSON.stringify(sequenceData, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `message-trace-${sessionId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleZoomIn() {
    setZoom((prev) => Math.min(prev + 0.2, 3.0));
  }

  function handleZoomOut() {
    setZoom((prev) => Math.max(prev - 0.2, 0.5));
  }

  function handleFitView() {
    setZoom(1.0);
  }

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-white rounded-lg p-8 shadow-xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-nhs-blue mx-auto mb-4"></div>
          <p className="text-sm text-gray-600">Loading sequence diagram...</p>
        </div>
      </div>
    );
  }

  if (error || !sequenceData) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-white rounded-lg p-8 shadow-xl max-w-md">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Diagram</h3>
          <p className="text-sm text-gray-600 mb-4">{error || "No data available"}</p>
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-nhs-blue text-white rounded-lg hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  // Calculate dimensions
  const totalWidth = MARGIN_LEFT + (sequenceData.items.length * COLUMN_WIDTH) + MARGIN_RIGHT;
  const durationMs = sequenceData.timeRange.end.getTime() - sequenceData.timeRange.start.getTime();
  const contentHeight = Math.max(durationMs * TIME_SCALE, 400);
  const totalHeight = MARGIN_TOP + HEADER_HEIGHT + contentHeight + MARGIN_BOTTOM;

  // Calculate swimlane positions
  const swimlanePositions: Map<string, SwimlanePosition> = new Map();
  sequenceData.items.forEach((item, idx) => {
    const x = MARGIN_LEFT + (idx * COLUMN_WIDTH);
    const centerX = x + ((COLUMN_WIDTH - 40) / 2); // 40 is HEADER_PADDING from SequenceSwimlane
    swimlanePositions.set(item.itemId, {
      itemId: item.itemId,
      x,
      width: COLUMN_WIDTH - 40,
      centerX,
    });
  });

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-semibold text-gray-900">
            Message Sequence Diagram
          </h2>
          <p className="text-sm text-gray-500">
            Session: <code className="bg-gray-100 px-2 py-0.5 rounded font-mono text-xs">{sessionId}</code>
            {" • "}
            Duration: {formatDuration(durationMs)}
            {" • "}
            {sequenceData.messages.length} messages
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 ml-4">
          <button
            onClick={handleZoomOut}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="h-5 w-5 text-gray-600" />
          </button>
          <span className="text-sm text-gray-600 font-mono min-w-[60px] text-center">
            {(zoom * 100).toFixed(0)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="h-5 w-5 text-gray-600" />
          </button>
          <button
            onClick={handleFitView}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Fit to View"
          >
            <Maximize className="h-5 w-5 text-gray-600" />
          </button>
          <button
            onClick={handleExport}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Export as JSON"
          >
            <Download className="h-5 w-5 text-gray-600" />
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Close"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Diagram Canvas */}
      <div className="flex-1 overflow-auto bg-gray-50">
        <div className="p-8">
          <svg
            viewBox={`0 0 ${totalWidth} ${totalHeight}`}
            className="w-full h-full bg-white rounded-lg shadow-lg"
            style={{
              minWidth: `${totalWidth * zoom}px`,
              minHeight: `${totalHeight * zoom}px`,
            }}
          >
            {/* Arrowhead marker definition */}
            <ArrowheadMarker />

            {/* Timeline */}
            <SequenceTimeline
              height={HEADER_HEIGHT + contentHeight}
              scale={TIME_SCALE}
              startTime={sequenceData.timeRange.start}
              endTime={sequenceData.timeRange.end}
            />

            {/* Swimlanes */}
            {sequenceData.items.map((item, idx) => (
              <SequenceSwimlane
                key={item.itemId}
                item={item}
                x={MARGIN_LEFT + (idx * COLUMN_WIDTH)}
                height={MARGIN_TOP + HEADER_HEIGHT + contentHeight}
              />
            ))}

            {/* Message Arrows */}
            {sequenceData.messages.map((msg, idx) => {
              const sourceLane = swimlanePositions.get(msg.sourceItemId);
              const targetLane = swimlanePositions.get(msg.targetItemId);

              if (!sourceLane || !targetLane) return null;

              // Calculate Y position based on timestamp
              const relativeTime = msg.timestamp.getTime() - sequenceData.timeRange.start.getTime();
              const yPosition = MARGIN_TOP + HEADER_HEIGHT + (relativeTime * TIME_SCALE);

              return (
                <SequenceArrow
                  key={msg.messageId}
                  message={msg}
                  sourceLane={sourceLane}
                  targetLane={targetLane}
                  yPosition={yPosition}
                  onArrowClick={() => console.log("Clicked message:", msg)}
                />
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}

/**
 * Transform API trace data into sequence diagram format.
 *
 * Uses IRIS-convention per-leg trace (message_headers).
 * Each message row IS one arrow. source_config_name → target_config_name.
 * Swimlanes derived from items[] with accurate business_type.
 */
function buildSequenceDiagram(trace: SessionTrace): SequenceDiagramData {
  const itemsMap = new Map<string, SequenceItem>();

  // Build swimlanes from trace.items (already sorted by backend)
  trace.items.forEach((item) => {
    if (item.item_name && !itemsMap.has(item.item_name)) {
      itemsMap.set(item.item_name, {
        itemId: item.item_name,
        itemName: item.item_name,
        itemType: item.item_type as "service" | "process" | "operation",
        columnIndex: 0,
      });
    }
  });

  // Sort: service → process → operation → alphabetical
  const typeOrder: Record<string, number> = { service: 0, process: 1, operation: 2 };
  const items = Array.from(itemsMap.values())
    .sort((a, b) => {
      const typeA = typeOrder[a.itemType] ?? 1;
      const typeB = typeOrder[b.itemType] ?? 1;
      if (typeA !== typeB) return typeA - typeB;
      return a.itemName.localeCompare(b.itemName);
    })
    .map((item, idx) => ({ ...item, columnIndex: idx }));

  // Each message row IS one arrow
  const messages = (trace.messages as TraceMessage[])
    .map((msg) => {
      const src = msg.source_config_name;
      const tgt = msg.target_config_name;
      if (!src || !tgt) return null;

      let status: "success" | "error" | "pending" = "success";
      if (msg.is_error || msg.status === "Error") {
        status = "error";
      } else if (msg.status === "Created" || msg.status === "Queued") {
        status = "pending";
      }

      // Build label: message_type or description
      const label = msg.message_type || msg.description || undefined;

      return {
        messageId: msg.id,
        sourceItemId: src,
        targetItemId: tgt,
        timestamp: new Date(msg.time_created),
        duration_ms: msg.latency_ms || 0,
        status,
        transformation: label,
      } as SequenceMessage;
    })
    .filter((msg): msg is SequenceMessage => msg !== null);

  // Time range from first/last headers
  const v2msgs = trace.messages as TraceMessage[];
  const timestamps = v2msgs.map((m) => new Date(m.time_created).getTime());
  const processedTimestamps = v2msgs
    .filter((m) => m.time_processed)
    .map((m) => new Date(m.time_processed!).getTime());

  const startTime = timestamps.length > 0 ? new Date(Math.min(...timestamps)) : new Date();
  const endTime =
    processedTimestamps.length > 0
      ? new Date(Math.max(...processedTimestamps))
      : timestamps.length > 0
      ? new Date(Math.max(...timestamps) + 1000)
      : new Date(startTime.getTime() + 1000);

  return {
    sessionId: trace.session_id,
    items,
    messages,
    timeRange: { start: startTime, end: endTime },
  };
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}
