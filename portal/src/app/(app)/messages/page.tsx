"use client";

import { useEffect, useState } from "react";
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
} from "lucide-react";

interface Message {
  id: string;
  messageType: string;
  source: string;
  destination: string;
  status: "completed" | "failed" | "processing" | "queued";
  size: number;
  createdAt: string;
  completedAt?: string;
  latencyMs?: number;
  productionName: string;
  routeId: string;
  correlationId: string;
  retryCount: number;
}

const statusStyles: Record<string, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
  completed: { bg: "bg-green-100", text: "text-green-700", icon: CheckCircle },
  failed: { bg: "bg-red-100", text: "text-red-700", icon: XCircle },
  processing: { bg: "bg-blue-100", text: "text-blue-700", icon: RefreshCw },
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

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    // Mock data - will be replaced with API calls
    const mockMessages: Message[] = [
      {
        id: "msg-001",
        messageType: "ADT^A01",
        source: "HTTP_ADT_Receiver",
        destination: "PAS_MLLP_Sender",
        status: "completed",
        size: 1245,
        createdAt: new Date(Date.now() - 60000).toISOString(),
        completedAt: new Date(Date.now() - 59500).toISOString(),
        latencyMs: 500,
        productionName: "NHS-ADT-Integration",
        routeId: "http_to_mllp",
        correlationId: "corr-abc-123",
        retryCount: 0,
      },
      {
        id: "msg-002",
        messageType: "ADT^A08",
        source: "HTTP_ADT_Receiver",
        destination: "PAS_MLLP_Sender",
        status: "failed",
        size: 892,
        createdAt: new Date(Date.now() - 120000).toISOString(),
        latencyMs: 5000,
        productionName: "NHS-ADT-Integration",
        routeId: "http_to_mllp",
        correlationId: "corr-def-456",
        retryCount: 3,
      },
      {
        id: "msg-003",
        messageType: "ORU^R01",
        source: "Lab_File_Receiver",
        destination: "EMR_HTTP_Sender",
        status: "processing",
        size: 3456,
        createdAt: new Date(Date.now() - 5000).toISOString(),
        productionName: "Lab-Results-Feed",
        routeId: "lab_to_emr",
        correlationId: "corr-ghi-789",
        retryCount: 0,
      },
      {
        id: "msg-004",
        messageType: "ADT^A04",
        source: "HTTP_ADT_Receiver",
        destination: "PAS_MLLP_Sender",
        status: "queued",
        size: 1100,
        createdAt: new Date(Date.now() - 2000).toISOString(),
        productionName: "NHS-ADT-Integration",
        routeId: "http_to_mllp",
        correlationId: "corr-jkl-012",
        retryCount: 0,
      },
      {
        id: "msg-005",
        messageType: "ADT^A01",
        source: "HTTP_ADT_Receiver",
        destination: "PAS_MLLP_Sender",
        status: "completed",
        size: 1567,
        createdAt: new Date(Date.now() - 180000).toISOString(),
        completedAt: new Date(Date.now() - 179200).toISOString(),
        latencyMs: 800,
        productionName: "NHS-ADT-Integration",
        routeId: "http_to_mllp",
        correlationId: "corr-mno-345",
        retryCount: 0,
      },
    ];

    setTimeout(() => {
      setMessages(mockMessages);
      setLoading(false);
    }, 500);
  }, []);

  const filteredMessages = messages.filter((msg) => {
    const matchesSearch =
      searchQuery === "" ||
      msg.messageType.toLowerCase().includes(searchQuery.toLowerCase()) ||
      msg.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      msg.correlationId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || msg.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

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
          onClick={() => setLoading(true)}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Search and Filters */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by message ID, type, or correlation ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
            />
          </div>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="processing">Processing</option>
              <option value="queued">Queued</option>
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
              <label className="block text-xs font-medium text-gray-700">Production</label>
              <select className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">All Productions</option>
                <option value="NHS-ADT-Integration">NHS-ADT-Integration</option>
                <option value="Lab-Results-Feed">Lab-Results-Feed</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700">Date Range</label>
              <select className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="1h">Last 1 hour</option>
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="custom">Custom range</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700">Message Type</label>
              <input
                type="text"
                placeholder="e.g., ADT^A01"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
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
              ) : filteredMessages.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center">
                    <MessageSquare className="mx-auto h-12 w-12 text-gray-300" />
                    <p className="mt-2 text-sm text-gray-500">No messages found</p>
                    <p className="text-xs text-gray-400">Try adjusting your search or filters</p>
                  </td>
                </tr>
              ) : (
                filteredMessages.map((msg) => (
                  <tr
                    key={msg.id}
                    className="cursor-pointer transition-colors hover:bg-gray-50"
                    onClick={() => setSelectedMessage(msg)}
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{msg.messageType}</p>
                        <p className="text-xs text-gray-500 font-mono">{msg.id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm text-gray-900">{msg.source}</p>
                        <p className="text-xs text-gray-500">→ {msg.destination}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={msg.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatBytes(msg.size)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {msg.latencyMs ? `${msg.latencyMs}ms` : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(msg.createdAt)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {msg.status === "failed" && (
                          <button
                            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                            title="Retry"
                          >
                            <RotateCcw className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
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
            Showing <span className="font-medium">{filteredMessages.length}</span> messages
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 1}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <button className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
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
                <div className="space-y-6">
                  {/* Status */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Status</h3>
                    <div className="mt-2">
                      <StatusBadge status={selectedMessage.status} />
                    </div>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Message Type</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.messageType}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Size</h3>
                      <p className="mt-1 text-sm text-gray-900">{formatBytes(selectedMessage.size)}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Source</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.source}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Destination</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.destination}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Production</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.productionName}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Route</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.routeId}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Latency</h3>
                      <p className="mt-1 text-sm text-gray-900">
                        {selectedMessage.latencyMs ? `${selectedMessage.latencyMs}ms` : "-"}
                      </p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Retry Count</h3>
                      <p className="mt-1 text-sm text-gray-900">{selectedMessage.retryCount}</p>
                    </div>
                  </div>

                  {/* Timestamps */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Timeline</h3>
                    <div className="mt-2 space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-2 rounded-full bg-blue-500" />
                        <span className="text-sm text-gray-600">Created: {formatDate(selectedMessage.createdAt)}</span>
                      </div>
                      {selectedMessage.completedAt && (
                        <div className="flex items-center gap-3">
                          <div className="h-2 w-2 rounded-full bg-green-500" />
                          <span className="text-sm text-gray-600">
                            Completed: {formatDate(selectedMessage.completedAt)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Correlation ID */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Correlation ID</h3>
                    <p className="mt-1 font-mono text-sm text-gray-900">{selectedMessage.correlationId}</p>
                  </div>

                  {/* Message Content Preview */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Content Preview</h3>
                    <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-gray-900 p-4 text-xs text-gray-100">
{`MSH|^~\\&|SENDING|FACILITY|RECEIVING|FACILITY|20260121120000||${selectedMessage.messageType}|123|P|2.5
PID|1||12345^^^NHS^NH||DOE^JOHN||19800101|M
PV1|1|I|WARD1^ROOM1^BED1`}
                    </pre>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
                {selectedMessage.status === "failed" && (
                  <button className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue">
                    <RotateCcw className="h-4 w-4" />
                    Retry Message
                  </button>
                )}
                <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                  <Download className="h-4 w-4" />
                  Download
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
