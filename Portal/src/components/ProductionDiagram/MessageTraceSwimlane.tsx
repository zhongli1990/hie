/**
 * Message Trace Swimlane Viewer
 * Displays end-to-end transaction flow through the integration engine
 * Shows message progression from inbound service → processes → outbound operations
 */

"use client";

import { useState, useEffect } from "react";
import {
  X,
  Clock,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  ChevronRight,
  Download,
  Maximize2,
  Copy,
  RefreshCw
} from "lucide-react";

// Types matching backend schema (MESSAGE_TRACE_SWIMLANES.md)
export interface MessageTrace {
  trace_id: string;
  session_id: string;
  message_id: string;
  message_type: string;
  started_at: string;
  completed_at: string | null;
  total_duration_ms: number;
  status: "success" | "error" | "in_progress";
  error_message?: string;
}

export interface TraceStage {
  stage_id: string;
  trace_id: string;
  item_id: string;
  item_name: string;
  item_type: "service" | "process" | "operation";
  sequence_number: number;
  entered_at: string;
  exited_at: string | null;
  duration_ms: number;
  queue_wait_ms: number;
  status: "success" | "error" | "in_progress";
  input_message?: string;
  output_message?: string;
  transformation?: string;
  error_message?: string;
}

interface MessageTraceSwimlaneProps {
  messageId: string;
  onClose: () => void;
}

export function MessageTraceSwimlane({ messageId, onClose }: MessageTraceSwimlaneProps) {
  const [trace, setTrace] = useState<MessageTrace | null>(null);
  const [stages, setStages] = useState<TraceStage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStage, setSelectedStage] = useState<TraceStage | null>(null);
  const [showMessageDiff, setShowMessageDiff] = useState(false);

  // Fetch trace data from API
  useEffect(() => {
    fetchTraceData();
  }, [messageId]);

  const fetchTraceData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch(`/api/projects/${projectId}/messages/${messageId}/trace`);
      // const data = await response.json();
      // setTrace(data.trace);
      // setStages(data.stages);

      // Mock data for demonstration
      const mockData = generateMockTraceData(messageId);
      setTrace(mockData.trace);
      setStages(mockData.stages);

      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trace data");
      setIsLoading(false);
    }
  };

  const handleExportTrace = () => {
    if (!trace || !stages) return;

    const exportData = {
      trace,
      stages,
      exported_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `message-trace-${messageId}-${Date.now()}.json`;
    link.click();
  };

  const handleCopyMessageId = () => {
    navigator.clipboard.writeText(messageId);
    // TODO: Show toast notification
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-40 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Swimlane Modal - Full Screen */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-2xl w-full h-full max-w-[95vw] max-h-[95vh] flex flex-col animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-nhs-blue to-blue-600">
            <div className="flex items-center gap-4 text-white">
              <div>
                <h2 className="text-xl font-bold">Message Trace Swimlane</h2>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-sm opacity-90">Message ID:</span>
                  <code className="bg-white/20 px-2 py-0.5 rounded text-sm font-mono">
                    {messageId}
                  </code>
                  <button
                    onClick={handleCopyMessageId}
                    className="p-1 hover:bg-white/20 rounded transition-colors"
                    title="Copy Message ID"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchTraceData}
                className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                title="Refresh trace"
              >
                <RefreshCw className={`h-5 w-5 ${isLoading ? "animate-spin" : ""}`} />
              </button>
              <button
                onClick={handleExportTrace}
                className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                title="Export trace data"
              >
                <Download className="h-5 w-5" />
              </button>
              <button
                onClick={onClose}
                className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                title="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <RefreshCw className="h-12 w-12 text-gray-300 animate-spin mx-auto mb-4" />
                <p className="text-gray-600">Loading message trace...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center p-6">
              <div className="max-w-md text-center">
                <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Failed to Load Trace
                </h3>
                <p className="text-sm text-gray-600 mb-4">{error}</p>
                <button
                  onClick={fetchTraceData}
                  className="px-4 py-2 bg-nhs-blue text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* Trace Summary */}
              {trace && <TraceSummary trace={trace} />}

              {/* Timeline Swimlane */}
              <div className="flex-1 overflow-auto p-6 bg-gray-50">
                <div className="min-w-max">
                  <TimelineSwimlane
                    stages={stages}
                    onStageClick={setSelectedStage}
                    selectedStageId={selectedStage?.stage_id}
                  />
                </div>
              </div>

              {/* Stage Detail Panel */}
              {selectedStage && (
                <StageDetailPanel
                  stage={selectedStage}
                  onClose={() => setSelectedStage(null)}
                  showMessageDiff={showMessageDiff}
                  onToggleMessageDiff={() => setShowMessageDiff(!showMessageDiff)}
                />
              )}
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in {
          animation: fadeIn 200ms ease-out;
        }
      `}</style>
    </>
  );
}

function TraceSummary({ trace }: { trace: MessageTrace }) {
  const isComplete = trace.status === "success" || trace.status === "error";
  const duration = trace.total_duration_ms;

  return (
    <div className="px-6 py-4 bg-white border-b">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Status */}
          <div className="flex items-center gap-2">
            {trace.status === "success" && (
              <CheckCircle className="h-6 w-6 text-green-500" />
            )}
            {trace.status === "error" && (
              <AlertCircle className="h-6 w-6 text-red-500" />
            )}
            {trace.status === "in_progress" && (
              <Clock className="h-6 w-6 text-yellow-500 animate-pulse" />
            )}
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-semibold ${
                trace.status === "success" ? "text-green-700" :
                trace.status === "error" ? "text-red-700" :
                "text-yellow-700"
              }`}>
                {trace.status === "success" ? "Completed Successfully" :
                 trace.status === "error" ? "Failed" :
                 "In Progress"}
              </p>
            </div>
          </div>

          {/* Message Type */}
          <div>
            <p className="text-sm text-gray-600">Message Type</p>
            <p className="font-semibold text-gray-900">{trace.message_type}</p>
          </div>

          {/* Duration */}
          <div>
            <p className="text-sm text-gray-600">Total Duration</p>
            <p className="font-semibold text-gray-900">{formatDuration(duration)}</p>
          </div>

          {/* Started At */}
          <div>
            <p className="text-sm text-gray-600">Started</p>
            <p className="font-semibold text-gray-900">
              {new Date(trace.started_at).toLocaleTimeString()}
            </p>
          </div>

          {isComplete && trace.completed_at && (
            <div>
              <p className="text-sm text-gray-600">Completed</p>
              <p className="font-semibold text-gray-900">
                {new Date(trace.completed_at).toLocaleTimeString()}
              </p>
            </div>
          )}
        </div>

        {trace.error_message && (
          <div className="max-w-md">
            <p className="text-sm text-red-600 font-medium">{trace.error_message}</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface TimelineSwimlaneProps {
  stages: TraceStage[];
  onStageClick: (stage: TraceStage) => void;
  selectedStageId?: string;
}

function TimelineSwimlane({ stages, onStageClick, selectedStageId }: TimelineSwimlaneProps) {
  return (
    <div className="space-y-6">
      {/* Timeline Header */}
      <div className="flex items-center gap-4 text-sm font-medium text-gray-600">
        <div className="w-8">#</div>
        <div className="w-48">Stage</div>
        <div className="flex-1 min-w-[600px]">Timeline</div>
        <div className="w-32 text-right">Duration</div>
        <div className="w-32 text-right">Queue Wait</div>
      </div>

      {/* Timeline Rows */}
      <div className="space-y-3">
        {stages.map((stage, index) => (
          <div key={stage.stage_id}>
            <div className="flex items-center gap-4">
              {/* Sequence Number */}
              <div className="w-8">
                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 text-gray-700 text-sm font-semibold">
                  {stage.sequence_number}
                </span>
              </div>

              {/* Stage Info */}
              <div className="w-48">
                <p className="font-medium text-gray-900">{stage.item_name}</p>
                <p className="text-xs text-gray-500 capitalize">{stage.item_type}</p>
              </div>

              {/* Timeline Bar */}
              <div className="flex-1 min-w-[600px]">
                <StageTimelineBar
                  stage={stage}
                  isSelected={stage.stage_id === selectedStageId}
                  onClick={() => onStageClick(stage)}
                />
              </div>

              {/* Metrics */}
              <div className="w-32 text-right">
                <p className="text-sm font-semibold text-gray-900">
                  {formatDuration(stage.duration_ms)}
                </p>
              </div>

              <div className="w-32 text-right">
                <p className={`text-sm ${
                  stage.queue_wait_ms > 1000 ? "text-yellow-700 font-semibold" : "text-gray-600"
                }`}>
                  {formatDuration(stage.queue_wait_ms)}
                </p>
              </div>
            </div>

            {/* Connection Arrow */}
            {index < stages.length - 1 && (
              <div className="flex items-center gap-4 my-2">
                <div className="w-8"></div>
                <div className="w-48"></div>
                <div className="flex-1 min-w-[600px] flex items-center">
                  <div className="ml-4">
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface StageTimelineBarProps {
  stage: TraceStage;
  isSelected: boolean;
  onClick: () => void;
}

function StageTimelineBar({ stage, isSelected, onClick }: StageTimelineBarProps) {
  const statusColor =
    stage.status === "success" ? "bg-green-500" :
    stage.status === "error" ? "bg-red-500" :
    "bg-yellow-500";

  const statusBorder =
    stage.status === "success" ? "border-green-600" :
    stage.status === "error" ? "border-red-600" :
    "border-yellow-600";

  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-2 px-4 py-3 rounded-lg border-2 transition-all
        ${isSelected
          ? `${statusBorder} shadow-lg scale-105`
          : "border-gray-300 hover:border-gray-400 hover:shadow-md"
        }
        bg-white
      `}
    >
      {/* Status Indicator */}
      <div className={`w-3 h-3 rounded-full ${statusColor}`} />

      {/* Stage Name & Timing */}
      <div className="flex-1 text-left">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900">
            {stage.transformation || stage.item_name}
          </span>
          <span className="text-xs text-gray-500">
            {new Date(stage.entered_at).toLocaleTimeString()} →
            {stage.exited_at && ` ${new Date(stage.exited_at).toLocaleTimeString()}`}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${statusColor} transition-all duration-500`}
            style={{ width: stage.exited_at ? "100%" : "60%" }}
          />
        </div>
      </div>

      {/* Status Icon */}
      {stage.status === "success" && <CheckCircle className="h-5 w-5 text-green-500" />}
      {stage.status === "error" && <AlertCircle className="h-5 w-5 text-red-500" />}
      {stage.status === "in_progress" && <Clock className="h-5 w-5 text-yellow-500" />}
    </button>
  );
}

interface StageDetailPanelProps {
  stage: TraceStage;
  onClose: () => void;
  showMessageDiff: boolean;
  onToggleMessageDiff: () => void;
}

function StageDetailPanel({ stage, onClose, showMessageDiff, onToggleMessageDiff }: StageDetailPanelProps) {
  return (
    <div className="border-t bg-white">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Stage Details</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        <div className="grid grid-cols-4 gap-6 mb-6">
          <div>
            <p className="text-xs text-gray-600 mb-1">Item Name</p>
            <p className="font-medium text-gray-900">{stage.item_name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Type</p>
            <p className="font-medium text-gray-900 capitalize">{stage.item_type}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Duration</p>
            <p className="font-medium text-gray-900">{formatDuration(stage.duration_ms)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Queue Wait</p>
            <p className={`font-medium ${
              stage.queue_wait_ms > 1000 ? "text-yellow-700" : "text-gray-900"
            }`}>
              {formatDuration(stage.queue_wait_ms)}
            </p>
          </div>
        </div>

        {stage.transformation && (
          <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <p className="text-sm">
              <span className="font-medium text-purple-900">Transformation:</span>
              <code className="ml-2 text-purple-700">{stage.transformation}</code>
            </p>
          </div>
        )}

        {stage.error_message && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm">
              <span className="font-medium text-red-900">Error:</span>
              <span className="ml-2 text-red-700">{stage.error_message}</span>
            </p>
          </div>
        )}

        {/* Message Content */}
        {(stage.input_message || stage.output_message) && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-gray-900">Message Content</h4>
              {stage.input_message && stage.output_message && (
                <button
                  onClick={onToggleMessageDiff}
                  className="text-sm text-nhs-blue hover:underline"
                >
                  {showMessageDiff ? "Show Separate" : "Show Diff"}
                </button>
              )}
            </div>

            {showMessageDiff && stage.input_message && stage.output_message ? (
              <MessageDiffViewer
                input={stage.input_message}
                output={stage.output_message}
              />
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {stage.input_message && (
                  <MessageViewer label="Input" message={stage.input_message} />
                )}
                {stage.output_message && (
                  <MessageViewer label="Output" message={stage.output_message} />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageViewer({ label, message }: { label: string; message: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-700 mb-2">{label} Message</p>
      <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-auto">
        <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
          {message}
        </pre>
      </div>
    </div>
  );
}

function MessageDiffViewer({ input, output }: { input: string; output: string }) {
  // Simple diff highlighting (production would use a proper diff library)
  const inputLines = input.split('\n');
  const outputLines = output.split('\n');

  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-xs font-medium text-gray-700 mb-2">Input (Before)</p>
        <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-auto">
          <pre className="text-xs text-green-400 font-mono">
            {inputLines.map((line, i) => (
              <div key={i} className={outputLines[i] !== line ? "bg-red-900/30" : ""}>
                {line}
              </div>
            ))}
          </pre>
        </div>
      </div>
      <div>
        <p className="text-xs font-medium text-gray-700 mb-2">Output (After)</p>
        <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-auto">
          <pre className="text-xs text-green-400 font-mono">
            {outputLines.map((line, i) => (
              <div key={i} className={inputLines[i] !== line ? "bg-green-900/30" : ""}>
                {line}
              </div>
            ))}
          </pre>
        </div>
      </div>
    </div>
  );
}

// Utility Functions
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

// Mock data generator (will be replaced with real API)
function generateMockTraceData(messageId: string): { trace: MessageTrace; stages: TraceStage[] } {
  const startTime = new Date(Date.now() - 5000);
  const hasError = Math.random() > 0.8;

  const trace: MessageTrace = {
    trace_id: `trace-${Date.now()}`,
    session_id: `session-${Math.floor(Math.random() * 1000)}`,
    message_id: messageId,
    message_type: "ADT^A01",
    started_at: startTime.toISOString(),
    completed_at: hasError ? null : new Date().toISOString(),
    total_duration_ms: 2450,
    status: hasError ? "error" : "success",
    error_message: hasError ? "Transformation validation failed" : undefined,
  };

  const stages: TraceStage[] = [
    {
      stage_id: "stage-1",
      trace_id: trace.trace_id,
      item_id: "item-1",
      item_name: "HL7.In.PAS",
      item_type: "service",
      sequence_number: 1,
      entered_at: new Date(startTime.getTime()).toISOString(),
      exited_at: new Date(startTime.getTime() + 450).toISOString(),
      duration_ms: 450,
      queue_wait_ms: 0,
      status: "success",
      input_message: "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.4\nEVN|A01|20240210120000\nPID|1||12345^^^MRN||Doe^John||19800101|M",
      output_message: "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.4\nEVN|A01|20240210120000\nPID|1||12345^^^MRN||Doe^John||19800101|M",
    },
    {
      stage_id: "stage-2",
      trace_id: trace.trace_id,
      item_id: "item-2",
      item_name: "Process.Transform.v23_to_v251",
      item_type: "process",
      sequence_number: 2,
      entered_at: new Date(startTime.getTime() + 450).toISOString(),
      exited_at: new Date(startTime.getTime() + 1650).toISOString(),
      duration_ms: 1200,
      queue_wait_ms: 150,
      status: hasError ? "error" : "success",
      input_message: "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.4",
      output_message: hasError ? undefined : "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.5.1",
      transformation: "custom.transforms.hl7.v23_to_v251",
      error_message: hasError ? "Field validation failed: PID-8 (Sex) contains invalid value" : undefined,
    },
  ];

  if (!hasError) {
    stages.push({
      stage_id: "stage-3",
      trace_id: trace.trace_id,
      item_id: "item-3",
      item_name: "HL7.Out.EPR",
      item_type: "operation",
      sequence_number: 3,
      entered_at: new Date(startTime.getTime() + 1650).toISOString(),
      exited_at: new Date(startTime.getTime() + 2450).toISOString(),
      duration_ms: 800,
      queue_wait_ms: 50,
      status: "success",
      input_message: "MSH|^~\\&|PAS|HOSP|HIE|HIE|20240210120000||ADT^A01|MSG001|P|2.5.1",
      output_message: "MSH|^~\\&|HIE|HIE|EPR|HOSP|20240210120001||ADT^A01|MSG001|P|2.5.1\nMSA|AA|MSG001",
    });
  }

  return { trace, stages };
}
