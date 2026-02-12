/**
 * SessionListView - Display message sessions grouped by session_id
 * Shows session metadata and allows clicking to view sequence diagram
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { RefreshCw, ChevronRight } from "lucide-react";
import { listSessions, type SessionSummary } from "@/lib/api-v2";

interface SessionListViewProps {
  itemId: string;
  projectId: string;
  onSessionClick: (sessionId: string) => void;
}

export function SessionListView({ itemId, projectId, onSessionClick }: SessionListViewProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchSessions = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);

      const response = await listSessions(projectId, {
        item: itemId,
        limit: 50,
        offset: 0,
      });

      setSessions(response.sessions);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch sessions");
      setLoading(false);
    }
  }, [itemId, projectId]);

  // Initial load
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchSessions();
    }, 10000);

    return () => clearInterval(interval);
  }, [autoRefresh, fetchSessions]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-gray-900">Message Sessions</h3>
          <span className="text-xs text-gray-500">
            {sessions.length} session{sessions.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh (10s)
          </label>
          <button
            onClick={fetchSessions}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors"
            title="Refresh now"
          >
            <RefreshCw className={`h-4 w-4 text-gray-600 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="m-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-900">{error}</p>
          </div>
        )}

        {loading && sessions.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 text-gray-300 animate-spin" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12 px-4">
            <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <svg
                className="h-8 w-8 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-700 mb-2">No message sessions found</p>
            <p className="text-xs text-gray-500 max-w-md mx-auto">
              Sessions will appear here when messages are processed with session tracking enabled.
              Each session groups related messages flowing through the integration pipeline.
            </p>
          </div>
        ) : (
          <div className="p-4 space-y-3">
            {sessions.map((session) => (
              <SessionCard
                key={session.session_id}
                session={session}
                onClick={() => onSessionClick(session.session_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface SessionCardProps {
  session: SessionSummary;
  onClick: () => void;
}

function SessionCard({ session, onClick }: SessionCardProps) {
  const successRate = Math.round(session.success_rate * 100);
  const statusColor =
    successRate === 100
      ? "bg-green-100 text-green-700 border-green-200"
      : successRate >= 50
      ? "bg-yellow-100 text-yellow-700 border-yellow-200"
      : "bg-red-100 text-red-700 border-red-200";

  return (
    <div
      onClick={onClick}
      className="border rounded-lg p-4 hover:bg-blue-50 hover:border-blue-300 cursor-pointer transition-all group"
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left: Session Info */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono text-gray-700 font-medium">
              {session.session_id}
            </code>
            <span className={`text-xs px-2 py-1 rounded border font-medium ${statusColor}`}>
              {successRate}% success
            </span>
          </div>

          {/* Metadata */}
          <div className="text-xs text-gray-600 space-y-1">
            <div className="flex items-center gap-2">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
              <span>
                {session.message_count} message{session.message_count !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{formatTimeRange(session.started_at, session.ended_at)}</span>
            </div>
          </div>

          {/* Message Types */}
          {session.message_types.length > 0 && (
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {session.message_types.map((type) => (
                <span
                  key={type}
                  className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-medium"
                >
                  {type}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Right: Action Button */}
        <button
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors"
          onClick={onClick}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          <span>View Diagram</span>
          <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
}

/**
 * Format time range for display
 */
function formatTimeRange(startedAt: string, endedAt: string): string {
  const start = new Date(startedAt);
  const end = new Date(endedAt);
  const durationMs = end.getTime() - start.getTime();

  const startTime = start.toLocaleTimeString();
  const duration = formatDuration(durationMs);

  return `${startTime} • ${duration}`;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

