"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  Filter,
  RefreshCw,
  ChevronRight,
  MessageSquare,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  RotateCcw,
  Download,
  ChevronLeft,
  ChevronDown,
  AlertCircle,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react";
import {
  listMessages,
  getMessage,
  resendMessage,
  listProjects,
  PortalMessage,
  PortalMessageDetail,
} from "@/lib/api-v2";

const statusStyles: Record<string, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
  completed: { bg: "bg-green-100", text: "text-green-700", icon: CheckCircle },
  sent: { bg: "bg-green-100", text: "text-green-700", icon: CheckCircle },
  failed: { bg: "bg-red-100", text: "text-red-700", icon: XCircle },
  error: { bg: "bg-red-100", text: "text-red-700", icon: XCircle },
  processing: { bg: "bg-blue-100", text: "text-blue-700", icon: RefreshCw },
  received: { bg: "bg-yellow-100", text: "text-yellow-700", icon: Clock },
  queued: { bg: "bg-yellow-100", text: "text-yellow-700", icon: Clock },
};

function StatusBadge({ status }: { status: string }) {
  const style = statusStyles[status] || statusStyles.queued;
  const Icon = style.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString();
}

interface Project {
  id: string;
  name: string;
  display_name: string;
}

export default function MessagesPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // Get initial filters from URL params
  const initialProjectId = searchParams.get('project') || '';
  const initialItemName = searchParams.get('item') || '';
  
  const [messages, setMessages] = useState<PortalMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedMessage, setSelectedMessage] = useState<PortalMessageDetail | null>(null);
  const [selectedMessageLoading, setSelectedMessageLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId);
  const [selectedItemName, setSelectedItemName] = useState(initialItemName);
  const [directionFilter, setDirectionFilter] = useState<string>("all");
  const pageSize = 50;

  // Load projects on mount
  useEffect(() => {
    async function loadProjects() {
      try {
        // Get default workspace projects
        const response = await listProjects('00000000-0000-0000-0000-000000000001');
        setProjects(response.projects || []);
        // Auto-select first project if none selected
        if (!selectedProjectId && response.projects?.length > 0) {
          setSelectedProjectId(response.projects[0].id);
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      }
    }
    loadProjects();
  }, []);

  // Load messages when filters change
  const loadMessages = useCallback(async () => {
    if (!selectedProjectId) {
      setMessages([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await listMessages(selectedProjectId, {
        item: selectedItemName || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: searchQuery || undefined,
        direction: directionFilter !== 'all' ? directionFilter : undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });
      
      setMessages(response.messages || []);
      setTotal(response.total || 0);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load messages';
      setError(errorMessage);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId, selectedItemName, statusFilter, searchQuery, directionFilter, page]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  // Load message detail when selected
  const handleSelectMessage = async (msg: PortalMessage) => {
    setSelectedMessageLoading(true);
    try {
      const detail = await getMessage(msg.project_id, msg.id);
      setSelectedMessage(detail);
    } catch (err) {
      console.error('Failed to load message detail:', err);
      // Show basic info anyway
      setSelectedMessage(msg as PortalMessageDetail);
    } finally {
      setSelectedMessageLoading(false);
    }
  };

  // Handle resend
  const handleResend = async (messageId: string) => {
    if (!selectedProjectId) return;
    try {
      await resendMessage(selectedProjectId, messageId);
      loadMessages(); // Refresh
    } catch (err) {
      console.error('Failed to resend message:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Messages</h1>
          <p className="mt-1 text-sm text-gray-500">
            Search, trace, and manage messages across all productions
          </p>
        </div>
        <button
          onClick={() => loadMessages()}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          {/* Project Selector */}
          <select
            value={selectedProjectId}
            onChange={(e) => { setSelectedProjectId(e.target.value); setPage(1); }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
          >
            <option value="">Select Project</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.display_name || p.name}</option>
            ))}
          </select>
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by message type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
            />
          </div>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
            >
              <option value="all">All Status</option>
              <option value="sent">Sent</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="error">Error</option>
              <option value="received">Received</option>
              <option value="processing">Processing</option>
            </select>
            <select
              value={directionFilter}
              onChange={(e) => { setDirectionFilter(e.target.value); setPage(1); }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
            >
              <option value="all">All Directions</option>
              <option value="inbound">Inbound</option>
              <option value="outbound">Outbound</option>
            </select>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                showFilters
                  ? "border-nhs-blue bg-nhs-blue/5 text-nhs-blue"
                  : "border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              <Filter className="h-4 w-4" />
              Filters
              <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`} />
            </button>
          </div>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className="mt-4 grid gap-4 border-t border-gray-200 pt-4 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-gray-700">Item Name</label>
              <input
                type="text"
                placeholder="e.g., hl7sender1"
                value={selectedItemName}
                onChange={(e) => setSelectedItemName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700">Message Type</label>
              <input
                type="text"
                placeholder="e.g., ADT^A01"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={() => { setSelectedItemName(''); setSearchQuery(''); setStatusFilter('all'); setDirectionFilter('all'); setPage(1); }}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Messages Table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Message</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Route</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Size</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Latency</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Time</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3">
                      <div className="h-4 w-32 animate-pulse rounded bg-gray-200" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-5 w-20 animate-pulse rounded bg-gray-200" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-16 animate-pulse rounded bg-gray-200" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-12 animate-pulse rounded bg-gray-200" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-28 animate-pulse rounded bg-gray-200" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="h-4 w-16 animate-pulse rounded bg-gray-200" />
                    </td>
                  </tr>
                ))
              ) : messages.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center">
                    <MessageSquare className="mx-auto h-12 w-12 text-gray-300" />
                    <p className="mt-2 text-sm text-gray-500">No messages found</p>
                    <p className="text-xs text-gray-400">{selectedProjectId ? 'Try adjusting your filters or send a test message' : 'Select a project to view messages'}</p>
                  </td>
                </tr>
              ) : (
                messages.map((msg: PortalMessage) => (
                  <tr
                    key={msg.id}
                    className="cursor-pointer transition-colors hover:bg-gray-50"
                    onClick={() => handleSelectMessage(msg)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {msg.direction === 'inbound' ? (
                          <ArrowDownLeft className="h-4 w-4 text-blue-500" />
                        ) : (
                          <ArrowUpRight className="h-4 w-4 text-green-500" />
                        )}
                        <div>
                          <p className="text-sm font-medium text-gray-900">{msg.message_type || 'Unknown'}</p>
                          <p className="text-xs text-gray-500 font-mono">{msg.id.slice(0, 8)}...</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm text-gray-900">{msg.item_name}</p>
                        <p className="text-xs text-gray-500">
                          {msg.remote_host ? `${msg.remote_host}:${msg.remote_port}` : msg.direction}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={msg.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatBytes(msg.content_size)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {msg.latency_ms ? `${msg.latency_ms}ms` : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(msg.received_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                          title="View details"
                          onClick={(e) => { e.stopPropagation(); handleSelectMessage(msg); }}
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {(msg.status === "failed" || msg.status === "error") && (
                          <button
                            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                            title="Retry"
                            onClick={(e) => { e.stopPropagation(); handleResend(msg.id); }}
                          >
                            <RotateCcw className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
          <p className="text-sm text-gray-500">
            Showing <span className="font-medium">{messages.length}</span> of <span className="font-medium">{total}</span> messages
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <span className="text-sm text-gray-600">Page {page}</span>
            <button
              disabled={page * pageSize >= total}
              onClick={() => setPage(p => p + 1)}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Message Detail Slide-over */}
      {selectedMessage && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSelectedMessage(null)} />
          <div className="absolute inset-y-0 right-0 w-full max-w-xl bg-white shadow-xl">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Message Details</h2>
                  <p className="text-sm text-gray-500 font-mono">{selectedMessage.id}</p>
                </div>
                <button
                  onClick={() => setSelectedMessage(null)}
                  className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                >
                  <XCircle className="h-5 w-5" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-6">
                {selectedMessageLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
                  </div>
                ) : (
                <div className="space-y-6">
                  {/* Status */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Status</h3>
                    <div className="mt-2 flex items-center gap-2">
                      <StatusBadge status={selectedMessage.status} />
                      {selectedMessage.ack_type && (
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          selectedMessage.ack_type === 'AA' || selectedMessage.ack_type === 'CA' 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-red-100 text-red-700'
                        }`}>
                          ACK: {selectedMessage.ack_type}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Error Message */}
                  {selectedMessage.error_message && (
                    <div className="rounded-lg bg-red-50 border border-red-200 p-4">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
                        <div>
                          <h3 className="text-sm font-medium text-red-800">Error</h3>
                          <p className="mt-1 text-sm text-red-700">{selectedMessage.error_message}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Message Type</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.message_type || 'Unknown'}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Size</h3>
                      <p className="mt-1 text-sm text-gray-900">{formatBytes(selectedMessage.content_size)}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Item</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.item_name}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Direction</h3>
                      <p className="mt-1 text-sm text-gray-900 capitalize">{selectedMessage.direction}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Remote Host</h3>
                      <p className="mt-1 text-sm text-gray-900">
                        {selectedMessage.remote_host ? `${selectedMessage.remote_host}:${selectedMessage.remote_port}` : '-'}
                      </p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Item Type</h3>
                      <p className="mt-1 text-sm text-gray-900 capitalize">{selectedMessage.item_type}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Latency</h3>
                      <p className="mt-1 text-sm text-gray-900">
                        {selectedMessage.latency_ms ? `${selectedMessage.latency_ms}ms` : "-"}
                      </p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Retry Count</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.retry_count}</p>
                    </div>
                  </div>

                  {/* Timestamps */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Timeline</h3>
                    <div className="mt-2 space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-2 rounded-full bg-blue-500" />
                        <span className="text-sm text-gray-600">Received: {formatDate(selectedMessage.received_at)}</span>
                      </div>
                      {selectedMessage.completed_at && (
                        <div className="flex items-center gap-3">
                          <div className="h-2 w-2 rounded-full bg-green-500" />
                          <span className="text-sm text-gray-600">
                            Completed: {formatDate(selectedMessage.completed_at)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Correlation ID */}
                  {selectedMessage.correlation_id && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Correlation ID</h3>
                    <p className="mt-1 font-mono text-sm text-gray-900">{selectedMessage.correlation_id}</p>
                  </div>
                  )}

                  {/* Message Content */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Message Content</h3>
                    <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-gray-900 p-4 text-xs text-gray-100 whitespace-pre-wrap">
                      {selectedMessage.raw_content_text 
                        ? selectedMessage.raw_content_text.split('\r').map((segment, i) => (
                            <div key={i} className={`${
                              segment.startsWith('MSH') ? 'text-blue-400' :
                              segment.startsWith('PID') ? 'text-green-400' :
                              segment.startsWith('PV1') ? 'text-yellow-400' :
                              segment.startsWith('EVN') ? 'text-cyan-400' :
                              segment.startsWith('MSA') ? 'text-purple-400' :
                              segment.startsWith('ERR') ? 'text-red-400' :
                              'text-gray-100'
                            }`}>
                              {segment}
                            </div>
                          ))
                        : selectedMessage.content_preview || 'No content available'}
                    </pre>
                  </div>

                  {/* ACK Content */}
                  {selectedMessage.ack_content_text && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">ACK Response</h3>
                    <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-gray-800 p-4 text-xs text-gray-100 whitespace-pre-wrap">
                      {selectedMessage.ack_content_text.split('\r').map((segment, i) => (
                        <div key={i} className={`${
                          segment.startsWith('MSH') ? 'text-blue-400' :
                          segment.startsWith('MSA') ? 'text-purple-400' :
                          segment.startsWith('ERR') ? 'text-red-400' :
                          'text-gray-100'
                        }`}>
                          {segment}
                        </div>
                      ))}
                    </pre>
                  </div>
                  )}
                </div>
                )}
              </div>
              <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
                {(selectedMessage.status === "failed" || selectedMessage.status === "error") && (
                  <button 
                    onClick={() => handleResend(selectedMessage.id)}
                    className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Retry Message
                  </button>
                )}
                <button 
                  onClick={() => setSelectedMessage(null)}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
