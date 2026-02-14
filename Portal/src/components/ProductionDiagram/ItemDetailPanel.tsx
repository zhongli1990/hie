/**
 * Right-side detail panel for topology items
 * Shows detailed configuration, events, messages, and metrics
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { X, Settings, Activity, MessageSquare, BarChart3, AlertCircle, AlertTriangle, Info, CheckCircle, Filter, RefreshCw } from "lucide-react";
import type { ProjectItem } from "./types";
import { SessionListView } from "./SessionListView";
import { MessageSequenceDiagram } from "./MessageSequenceDiagram";
import { listMessages, type PortalMessage } from "@/lib/api-v2";

interface ItemDetailPanelProps {
  item: ProjectItem | null;
  onClose: () => void;
}

type TabType = "config" | "events" | "messages" | "metrics";

export function ItemDetailPanel({ item, onClose }: ItemDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("config");
  const [panelWidth, setPanelWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);

  // Load saved width from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('itemDetailPanelWidth');
    if (saved) {
      const width = parseInt(saved, 10);
      if (width >= 400 && width <= 800) {
        setPanelWidth(width);
      }
    }
  }, []);

  // Save width to localStorage
  useEffect(() => {
    localStorage.setItem('itemDetailPanelWidth', panelWidth.toString());
  }, [panelWidth]);

  // Handle resize
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    function handleMouseMove(e: MouseEvent) {
      const newWidth = window.innerWidth - e.clientX;
      setPanelWidth(Math.max(400, Math.min(800, newWidth)));
    }

    function handleMouseUp() {
      setIsResizing(false);
    }

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  if (!item) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Resize Handle */}
      <div
        onMouseDown={handleMouseDown}
        className={`fixed top-0 bottom-0 w-2 cursor-ew-resize hover:bg-blue-200 transition-colors z-50 group ${
          isResizing ? 'bg-blue-300' : ''
        }`}
        style={{ right: panelWidth }}
      >
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-12 bg-gray-300 rounded-full group-hover:bg-blue-400 transition-colors" />
      </div>

      {/* Slide-in Panel */}
      <div
        className="fixed right-0 top-0 bottom-0 bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right"
        style={{
          width: panelWidth,
          animation: "slideInRight 300ms ease-out",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate" title={item.name}>
              {item.name}
            </h2>
            <p className="text-sm text-gray-500 truncate" title={item.class_name}>
              {item.class_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 rounded-lg hover:bg-gray-200 transition-colors"
            title="Close panel"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b bg-white">
          <TabButton
            icon={<Settings className="h-4 w-4" />}
            label="Config"
            active={activeTab === "config"}
            onClick={() => setActiveTab("config")}
          />
          <TabButton
            icon={<Activity className="h-4 w-4" />}
            label="Events"
            active={activeTab === "events"}
            onClick={() => setActiveTab("events")}
          />
          <TabButton
            icon={<MessageSquare className="h-4 w-4" />}
            label="Messages"
            active={activeTab === "messages"}
            onClick={() => setActiveTab("messages")}
          />
          <TabButton
            icon={<BarChart3 className="h-4 w-4" />}
            label="Metrics"
            active={activeTab === "metrics"}
            onClick={() => setActiveTab("metrics")}
          />
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "config" && <ConfigurationTab item={item} onSwitchTab={setActiveTab} />}
          {activeTab === "events" && <EventsTab item={item} onSwitchTab={setActiveTab} />}
          {activeTab === "messages" && <MessagesTab item={item} />}
          {activeTab === "metrics" && <MetricsTab item={item} onSwitchTab={setActiveTab} panelWidth={panelWidth} />}
        </div>
      </div>

      <style jsx>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
      `}</style>
    </>
  );
}

interface TabButtonProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}

function TabButton({ icon, label, active, onClick }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
        ${
          active
            ? "border-nhs-blue text-nhs-blue bg-blue-50"
            : "border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50"
        }
      `}
    >
      {icon}
      {label}
    </button>
  );
}

// Placeholder tab components
function ConfigurationTab({ item, onSwitchTab }: { item: ProjectItem; onSwitchTab: (tab: TabType) => void }) {
  return (
    <div className="p-6 space-y-6">
      {/* Quick Actions Card */}
      <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Message Tracing Available
        </h3>
        <p className="text-xs text-blue-700 mb-3">
          Track messages flowing through <strong>{item.name}</strong> with end-to-end swimlane visualization.
        </p>
        <button
          onClick={() => onSwitchTab("messages")}
          className="w-full px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          <MessageSquare className="h-4 w-4" />
          View Messages & Traces
        </button>
      </div>

      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-3">Basic Settings</h3>
        <div className="space-y-3">
          <SettingRow label="Type" value={item.item_type} />
          <SettingRow label="Enabled" value={item.enabled ? "Yes" : "No"} />
          <SettingRow label="Pool Size" value={item.pool_size.toString()} />
          <SettingRow label="Category" value={item.category || "-"} />
        </div>
      </div>

      {Object.keys(item.adapter_settings).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Adapter Settings</h3>
          <div className="space-y-2">
            {Object.entries(item.adapter_settings).map(([key, value]) => (
              <SettingRow key={key} label={key} value={String(value)} />
            ))}
          </div>
        </div>
      )}

      {Object.keys(item.host_settings).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Host Settings</h3>
          <div className="space-y-2">
            {Object.entries(item.host_settings).map(([key, value]) => (
              <SettingRow key={key} label={key} value={String(value)} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Event log types
type LogLevel = "ERROR" | "WARN" | "INFO" | "DEBUG" | "TRACE";

interface LogEvent {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
  details?: string;
}

function EventsTab({ item, onSwitchTab }: { item: ProjectItem; onSwitchTab: (tab: TabType) => void }) {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | "ALL">("ALL");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Fetch events from API
  const fetchEvents = useCallback(async () => {
    try {
      setError(null);
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch(`/api/projects/${projectId}/items/${item.id}/logs`);
      // const data = await response.json();
      // setEvents(data.events);

      // Mock data for now - simulating real-time events
      const mockEvents: LogEvent[] = generateMockEvents(item);
      setEvents(mockEvents);
      setLastRefresh(new Date());
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch events");
      setIsLoading(false);
    }
  }, [item]);

  // Initial load
  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchEvents();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, fetchEvents]);

  // Filter events by level
  const filteredEvents = selectedLevel === "ALL"
    ? events
    : events.filter(e => e.level === selectedLevel);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="px-4 py-3 border-b bg-gray-50 space-y-3">
        {/* Level Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-gray-500" />
          <span className="text-xs font-medium text-gray-600">Filter:</span>
          {(["ALL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE"] as const).map((level) => (
            <button
              key={level}
              onClick={() => setSelectedLevel(level)}
              className={`
                px-2 py-1 text-xs font-medium rounded transition-colors
                ${selectedLevel === level
                  ? getLevelButtonStyle(level, true)
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }
              `}
            >
              {level}
            </button>
          ))}
        </div>

        {/* Auto-refresh & Manual Refresh */}
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh (5s)
          </label>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">
              Last: {lastRefresh.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchEvents}
              className="p-1 rounded hover:bg-gray-200 transition-colors"
              title="Refresh now"
            >
              <RefreshCw className={`h-4 w-4 text-gray-600 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Cross-reference to Messages */}
        <div className="pt-2 border-t">
          <button
            onClick={() => onSwitchTab("messages")}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <span className="flex items-center gap-2">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              View Message Traces
            </span>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="m-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-900">Error loading events</p>
              <p className="text-xs text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {isLoading && events.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 text-gray-300 animate-spin" />
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Activity className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">No {selectedLevel !== "ALL" ? selectedLevel : ""} events</p>
            <p className="text-xs text-gray-400 mt-1">
              {selectedLevel !== "ALL" ? "Try changing the filter" : "Events will appear here when available"}
            </p>
          </div>
        ) : (
          <div className="divide-y">
            {filteredEvents.map((event) => (
              <EventLogRow key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EventLogRow({ event }: { event: LogEvent }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`
        p-3 hover:bg-gray-50 transition-colors cursor-pointer
        ${getLevelBgClass(event.level)}
      `}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-3">
        {/* Level Icon */}
        <div className="flex-shrink-0 mt-0.5">
          {getLevelIcon(event.level)}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className={`text-sm font-medium ${getLevelTextClass(event.level)}`}>
              {event.message}
            </p>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {new Date(event.timestamp).toLocaleTimeString()}
            </span>
          </div>

          {event.source && (
            <p className="text-xs text-gray-500 mt-1">
              Source: <code className="bg-gray-100 px-1 rounded">{event.source}</code>
            </p>
          )}

          {expanded && event.details && (
            <div className="mt-2 p-2 bg-gray-100 rounded text-xs font-mono text-gray-700 whitespace-pre-wrap">
              {event.details}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function getLevelIcon(level: LogLevel) {
  switch (level) {
    case "ERROR":
      return <AlertCircle className="h-5 w-5 text-red-500" />;
    case "WARN":
      return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
    case "INFO":
      return <Info className="h-5 w-5 text-blue-500" />;
    case "DEBUG":
    case "TRACE":
      return <CheckCircle className="h-5 w-5 text-gray-400" />;
  }
}

function getLevelBgClass(level: LogLevel): string {
  switch (level) {
    case "ERROR":
      return "border-l-4 border-red-500";
    case "WARN":
      return "border-l-4 border-yellow-500";
    case "INFO":
      return "border-l-4 border-blue-500";
    default:
      return "border-l-4 border-gray-300";
  }
}

function getLevelTextClass(level: LogLevel): string {
  switch (level) {
    case "ERROR":
      return "text-red-900";
    case "WARN":
      return "text-yellow-900";
    case "INFO":
      return "text-blue-900";
    default:
      return "text-gray-900";
  }
}

function getLevelButtonStyle(level: string, active: boolean): string {
  if (!active) return "";

  switch (level) {
    case "ERROR":
      return "bg-red-500 text-white";
    case "WARN":
      return "bg-yellow-500 text-white";
    case "INFO":
      return "bg-blue-500 text-white";
    case "ALL":
      return "bg-nhs-blue text-white";
    default:
      return "bg-gray-500 text-white";
  }
}

// Mock event generator (will be replaced with real API)
function generateMockEvents(item: ProjectItem): LogEvent[] {
  const now = new Date();
  const events: LogEvent[] = [];

  // Generate sample events based on item state
  if (item.enabled) {
    events.push({
      id: `evt-${Date.now()}-1`,
      timestamp: new Date(now.getTime() - 30000).toISOString(),
      level: "INFO",
      message: `${item.name} started successfully`,
      source: item.class_name,
    });

    events.push({
      id: `evt-${Date.now()}-2`,
      timestamp: new Date(now.getTime() - 25000).toISOString(),
      level: "INFO",
      message: `Listening on port ${(item.adapter_settings as any)?.Port || "N/A"}`,
      source: item.class_name,
    });

    if (item.metrics && (item.metrics as any).messages_received > 0) {
      events.push({
        id: `evt-${Date.now()}-3`,
        timestamp: new Date(now.getTime() - 10000).toISOString(),
        level: "INFO",
        message: `Processed message batch: ${(item.metrics as any).messages_received} messages`,
        source: item.class_name,
      });
    }
  } else {
    events.push({
      id: `evt-${Date.now()}-4`,
      timestamp: new Date(now.getTime() - 60000).toISOString(),
      level: "WARN",
      message: `${item.name} is disabled`,
      source: item.class_name,
    });
  }

  // Add some sample warnings/errors occasionally
  if (Math.random() > 0.7) {
    events.push({
      id: `evt-${Date.now()}-5`,
      timestamp: new Date(now.getTime() - 5000).toISOString(),
      level: "WARN",
      message: "Connection pool nearing capacity",
      source: item.class_name,
      details: `Current pool size: ${item.pool_size}\nActive connections: ${Math.floor(item.pool_size * 0.8)}`,
    });
  }

  return events.sort((a, b) =>
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
}

// Message types
interface MessageItem {
  id: string;
  timestamp: string;
  direction: "inbound" | "outbound";
  messageType: string;
  status: "success" | "error" | "pending";
  size: number;
  sessionId?: string;
}

function MessagesTab({ item }: { item: ProjectItem }) {
  const [view, setView] = useState<"list" | "sessions">("list");
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<"all" | "success" | "error">("all");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [showDemoTrace, setShowDemoTrace] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  // Fetch messages from API
  const fetchMessages = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);

      const response = await listMessages(item.project_id, {
        item: item.name,
        limit: 50,
        offset: 0,
      });

      // Map PortalMessage to MessageItem
      const mappedMessages: MessageItem[] = response.messages.map((msg) => ({
        id: msg.id,
        timestamp: msg.received_at,
        direction: (msg.direction || "inbound") as "inbound" | "outbound",
        messageType: msg.message_type || "Unknown",
        status: mapMessageStatus(msg.status),
        size: msg.content_size || 0,
        sessionId: msg.correlation_id || undefined,
      }));

      setMessages(mappedMessages);
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch messages");
      setIsLoading(false);
    }
  }, [item]);

  // Initial load
  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  // Auto-refresh every 10 seconds (only for list view)
  useEffect(() => {
    if (!autoRefresh || view !== "list") return;

    const interval = setInterval(() => {
      fetchMessages();
    }, 10000);

    return () => clearInterval(interval);
  }, [autoRefresh, view, fetchMessages]);

  // Filter messages
  const filteredMessages = filterStatus === "all"
    ? messages
    : messages.filter(m => m.status === filterStatus);

  return (
    <div className="flex flex-col h-full">
      {/* Sub-Tab Navigation */}
      <div className="flex border-b bg-white">
        <button
          onClick={() => setView("list")}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            view === "list"
              ? "border-b-2 border-nhs-blue text-nhs-blue bg-blue-50"
              : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <MessageSquare className="h-4 w-4" />
            All Messages
          </div>
        </button>
        <button
          onClick={() => setView("sessions")}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            view === "sessions"
              ? "border-b-2 border-nhs-blue text-nhs-blue bg-blue-50"
              : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Message Sessions
          </div>
        </button>
      </div>

      {/* Content */}
      {view === "list" ? (
        <div className="flex flex-col flex-1">
          {/* 🚀 E2E MESSAGE TRACING FEATURE BANNER */}
          <div className="px-4 py-3 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-blue-200">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-blue-900 mb-1">
                  End-to-End Message Tracing
                </h3>
                <p className="text-xs text-blue-700 leading-relaxed">
                  Track messages through the entire integration pipeline with interactive swimlane visualization.
                  Click <strong>"View Trace →"</strong> on any message to see its complete journey across services, processes, and operations.
                </p>
              </div>
              <button
                onClick={() => setShowDemoTrace(true)}
                className="flex-shrink-0 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              >
                🎯 Demo Trace
              </button>
            </div>
          </div>

          {/* Toolbar */}
          <div className="px-4 py-3 border-b bg-gray-50 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-600">Filter by Status:</span>
                {(["all", "success", "error"] as const).map((status) => (
                  <button
                    key={status}
                    onClick={() => setFilterStatus(status)}
                    className={`
                      px-2 py-1 text-xs font-medium rounded transition-colors
                      ${filterStatus === status
                        ? status === "error" ? "bg-red-500 text-white" :
                          status === "success" ? "bg-green-500 text-white" :
                          "bg-nhs-blue text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }
                    `}
                  >
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </button>
                ))}
              </div>

              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                Auto-refresh (10s)
              </label>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">
                {filteredMessages.length} message{filteredMessages.length !== 1 ? "s" : ""}
              </span>
              {messages.length > 0 && (
                <span className="text-blue-600 font-medium">
                  ✨ Click any message to view its end-to-end trace
                </span>
              )}
            </div>
          </div>

          {/* Messages List */}
          <div className="flex-1 overflow-y-auto">
            {error && (
              <div className="m-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-900">{error}</p>
              </div>
            )}

            {isLoading && messages.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="h-8 w-8 text-gray-300 animate-spin" />
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="text-center py-12 px-4">
                <MessageSquare className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                <p className="text-sm font-medium text-gray-700 mb-2">
                  No {filterStatus !== "all" ? filterStatus : ""} messages found
                </p>
                <p className="text-xs text-gray-500 mb-4 max-w-md mx-auto">
                  {filterStatus !== "all"
                    ? "Try changing the status filter above to see other messages."
                    : "Messages will appear here as they are processed through the integration engine."}
                </p>
                <button
                  onClick={() => setShowDemoTrace(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-nhs-blue rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  View Sample Message Trace
                </button>
              </div>
            ) : (
              <div className="divide-y">
                {filteredMessages.map((message) => (
                  <MessageRow
                    key={message.id}
                    message={message}
                    itemName={item.name}
                    onViewTrace={() => setSelectedMessageId(message.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <SessionListView
          itemId={item.id}
          projectId={item.project_id}
          onSessionClick={setSelectedSessionId}
        />
      )}

      {/* Message Sequence Diagram Modal (IRIS-style) */}
      {(selectedSessionId || selectedMessageId || showDemoTrace) && (
        <MessageSequenceDiagram
          sessionId={selectedSessionId || selectedMessageId || "DEMO-SESSION-001"}
          projectId={item.project_id}
          onClose={() => {
            setSelectedSessionId(null);
            setSelectedMessageId(null);
            setShowDemoTrace(false);
          }}
        />
      )}
    </div>
  );
}

function MessageRow({ message, itemName, onViewTrace }: {
  message: MessageItem;
  itemName: string;
  onViewTrace: () => void;
}) {

  return (
    <div className="p-3 hover:bg-blue-50 transition-colors border-l-4 border-transparent hover:border-blue-500">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`
                inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium
                ${message.direction === "inbound"
                  ? "bg-green-100 text-green-700"
                  : "bg-blue-100 text-blue-700"
                }
              `}
            >
              {message.direction === "inbound" ? "↓" : "↑"}
              {message.direction}
            </span>
            <span
              className={`
                inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium
                ${message.status === "success"
                  ? "bg-green-100 text-green-700"
                  : message.status === "error"
                  ? "bg-red-100 text-red-700"
                  : "bg-yellow-100 text-yellow-700"
                }
              `}
            >
              {message.status === "success" ? "✓" : message.status === "error" ? "✗" : "⏳"}
              {message.status}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              E2E Traced
            </span>
          </div>

          {/* Details */}
          <div className="text-sm space-y-1">
            <p className="font-semibold text-gray-900">{message.messageType}</p>
            <p className="text-xs text-gray-500">
              <span className="text-gray-600 font-medium">Message ID:</span>{" "}
              <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono">{message.id}</code>
            </p>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {new Date(message.timestamp).toLocaleString()}
              </span>
              <span>Size: {formatBytes(message.size)}</span>
            </div>
          </div>
        </div>

        {/* 🎯 PROMINENT TRACE BUTTON */}
        <button
          onClick={onViewTrace}
          className="flex-shrink-0 group relative px-4 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-sm hover:shadow-md"
        >
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            View Trace
            <svg className="h-4 w-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </span>
          {/* Tooltip */}
          <span className="absolute -top-10 left-1/2 -translate-x-1/2 px-3 py-1 text-xs font-medium text-white bg-gray-900 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
            Track end-to-end message flow
          </span>
        </button>
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Map API status to MessageItem status
 */
function mapMessageStatus(apiStatus: string): "success" | "error" | "pending" {
  const status = apiStatus.toLowerCase();
  if (status === "sent" || status === "completed" || status === "success") {
    return "success";
  } else if (status === "failed" || status === "error") {
    return "error";
  } else {
    return "pending";
  }
}

function MetricsTab({ item, onSwitchTab, panelWidth }: { item: ProjectItem; onSwitchTab: (tab: TabType) => void; panelWidth: number }) {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Auto-refresh metrics every 10 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      setLastRefresh(new Date());
      // TODO: Fetch fresh metrics from API
    }, 10000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (!item.metrics) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm">No metrics available</p>
          <p className="text-xs text-gray-400 mt-1">
            {item.enabled
              ? "Metrics will appear shortly after item starts processing"
              : "Start the item to see metrics"}
          </p>
        </div>
      </div>
    );
  }

  const metrics = item.metrics as any;

  // Calculate derived metrics
  const messagesReceived = metrics.messages_received || 0;
  const messagesSent = metrics.messages_sent || 0;
  const errors = metrics.errors || 0;
  const avgLatency = metrics.avg_latency_ms || 0;
  const successRate = messagesReceived > 0
    ? ((messagesReceived - errors) / messagesReceived * 100).toFixed(1)
    : "0";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">Runtime Metrics</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            Updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh
          </label>
        </div>
      </div>

      {/* Metrics Content */}
      <div className="flex-1 overflow-y-auto overflow-x-auto p-6 space-y-6">
        {/* Message Trace Cross-Reference */}
        {messagesReceived > 0 && (
          <div className="rounded-lg border-2 border-purple-200 bg-purple-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-purple-900 mb-1 flex items-center gap-2">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  {messagesReceived.toLocaleString()} Messages Processed
                </h4>
                <p className="text-xs text-purple-700">
                  View individual message traces with swimlane visualization
                </p>
              </div>
              <button
                onClick={() => onSwitchTab("messages")}
                className="flex-shrink-0 px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors"
              >
                View Traces
              </button>
            </div>
          </div>
        )}

        {/* Key Performance Indicators */}
        <div className={`grid gap-4 ${panelWidth >= 600 ? 'grid-cols-3' : 'grid-cols-2'}`}>
          <MetricCard
            label="Success Rate"
            value={`${successRate}%`}
            color="green"
            icon="✓"
          />
          <MetricCard
            label="Avg Latency"
            value={`${avgLatency}ms`}
            color={avgLatency > 1000 ? "yellow" : "blue"}
            icon="⏱"
          />
          <MetricCard
            label="Messages Received"
            value={messagesReceived.toLocaleString()}
            color="blue"
            icon="↓"
          />
          <MetricCard
            label="Messages Sent"
            value={messagesSent.toLocaleString()}
            color="purple"
            icon="↑"
          />
        </div>

        {/* Throughput Chart */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Message Throughput</h4>
          <div className="space-y-3">
            <MetricBar
              label="Received"
              value={messagesReceived}
              max={Math.max(messagesReceived, messagesSent, 1)}
              color="blue"
            />
            <MetricBar
              label="Sent"
              value={messagesSent}
              max={Math.max(messagesReceived, messagesSent, 1)}
              color="purple"
            />
            <MetricBar
              label="Errors"
              value={errors}
              max={Math.max(messagesReceived, messagesSent, 1)}
              color="red"
            />
          </div>
        </div>

        {/* Pool Status */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Connection Pool</h4>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Pool Size</span>
              <span className="font-medium text-gray-900">{item.pool_size}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-nhs-blue h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.min((item.pool_size / 10) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-500">
              Configured capacity: {item.pool_size} connections
            </p>
          </div>
        </div>

        {/* Additional Metrics */}
        {Object.entries(metrics).length > 4 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Additional Metrics</h4>
            <div className="space-y-2">
              {Object.entries(metrics)
                .filter(([key]) => !["messages_received", "messages_sent", "errors", "avg_latency_ms"].includes(key))
                .map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm py-2 border-b border-gray-100">
                    <span className="text-gray-600">{key.replace(/_/g, " ")}</span>
                    <span className="font-medium text-gray-900">{String(value)}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  color: "green" | "blue" | "purple" | "yellow" | "red";
  icon: string;
}

function MetricCard({ label, value, color, icon }: MetricCardProps) {
  const colorClasses = {
    green: "bg-green-50 text-green-700 border-green-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
    yellow: "bg-yellow-50 text-yellow-700 border-yellow-200",
    red: "bg-red-50 text-red-700 border-red-200",
  };

  return (
    <div className={`rounded-lg p-4 border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium uppercase">{label}</p>
        <span className="text-lg">{icon}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

interface MetricBarProps {
  label: string;
  value: number;
  max: number;
  color: "blue" | "purple" | "red" | "green";
}

function MetricBar({ label, value, max, color }: MetricBarProps) {
  const percentage = max > 0 ? (value / max) * 100 : 0;

  const colorClasses = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    red: "bg-red-500",
    green: "bg-green-500",
  };

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{value.toLocaleString()}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`h-3 rounded-full transition-all duration-500 ${colorClasses[color]}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-start py-2 border-b border-gray-100">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900 text-right max-w-[200px] truncate" title={value}>
        {value}
      </span>
    </div>
  );
}
