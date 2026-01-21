"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  RefreshCw,
  RotateCcw,
  Search,
  XCircle,
} from "lucide-react";

interface ErrorEntry {
  id: string;
  timestamp: string;
  severity: "error" | "warning" | "critical";
  message: string;
  source: string;
  productionName: string;
  itemName: string;
  messageId?: string;
  stackTrace?: string;
  resolved: boolean;
  resolvedAt?: string;
  resolvedBy?: string;
  retryCount: number;
}

const severityStyles = {
  critical: { bg: "bg-red-100", text: "text-red-700", border: "border-red-200" },
  error: { bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-200" },
  warning: { bg: "bg-yellow-100", text: "text-yellow-700", border: "border-yellow-200" },
};

export default function ErrorsPage() {
  const [errors, setErrors] = useState<ErrorEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [showResolved, setShowResolved] = useState(false);
  const [expandedError, setExpandedError] = useState<string | null>(null);

  useEffect(() => {
    const mockErrors: ErrorEntry[] = [
      {
        id: "err-001",
        timestamp: new Date(Date.now() - 300000).toISOString(),
        severity: "critical",
        message: "Connection refused: Unable to connect to PAS MLLP server at 192.168.1.100:2575",
        source: "PAS_MLLP_Sender",
        productionName: "NHS-ADT-Integration",
        itemName: "PAS_MLLP_Sender",
        messageId: "msg-002",
        stackTrace: `ConnectionError: Connection refused
  at MLLPSender.connect (mllp_sender.py:45)
  at MLLPSender.send (mllp_sender.py:78)
  at Route.forward (route.py:156)
  at Production.process (production.py:234)`,
        resolved: false,
        retryCount: 3,
      },
      {
        id: "err-002",
        timestamp: new Date(Date.now() - 600000).toISOString(),
        severity: "error",
        message: "Message validation failed: Missing required PID segment",
        source: "HL7_Validator",
        productionName: "NHS-ADT-Integration",
        itemName: "HL7_Validator",
        messageId: "msg-005",
        resolved: false,
        retryCount: 0,
      },
      {
        id: "err-003",
        timestamp: new Date(Date.now() - 1800000).toISOString(),
        severity: "warning",
        message: "High latency detected: Average response time exceeded 500ms threshold",
        source: "Lab_HTTP_Sender",
        productionName: "Lab-Results-Feed",
        itemName: "Lab_HTTP_Sender",
        resolved: true,
        resolvedAt: new Date(Date.now() - 900000).toISOString(),
        resolvedBy: "System (auto-resolved)",
        retryCount: 0,
      },
      {
        id: "err-004",
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        severity: "error",
        message: "Timeout waiting for ACK response after 30000ms",
        source: "PAS_MLLP_Sender",
        productionName: "NHS-ADT-Integration",
        itemName: "PAS_MLLP_Sender",
        messageId: "msg-010",
        resolved: true,
        resolvedAt: new Date(Date.now() - 3500000).toISOString(),
        resolvedBy: "admin@nhs.uk",
        retryCount: 2,
      },
    ];

    setTimeout(() => {
      setErrors(mockErrors);
      setLoading(false);
    }, 500);
  }, []);

  const filteredErrors = errors.filter((err) => {
    const matchesSearch =
      searchQuery === "" ||
      err.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      err.source.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSeverity = severityFilter === "all" || err.severity === severityFilter;
    const matchesResolved = showResolved || !err.resolved;
    return matchesSearch && matchesSeverity && matchesResolved;
  });

  const unresolvedCount = errors.filter((e) => !e.resolved).length;
  const criticalCount = errors.filter((e) => e.severity === "critical" && !e.resolved).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Errors</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and resolve system errors and warnings
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

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Unresolved Errors</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">{unresolvedCount}</p>
            </div>
            <div className="rounded-lg bg-orange-100 p-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Critical Issues</p>
              <p className="mt-1 text-3xl font-bold text-red-600">{criticalCount}</p>
            </div>
            <div className="rounded-lg bg-red-100 p-2">
              <XCircle className="h-5 w-5 text-red-600" />
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Resolved Today</p>
              <p className="mt-1 text-3xl font-bold text-green-600">
                {errors.filter((e) => e.resolved).length}
              </p>
            </div>
            <div className="rounded-lg bg-green-100 p-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search errors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
            />
          </div>
          <div className="flex items-center gap-3">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none"
            >
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
            </select>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={showResolved}
                onChange={(e) => setShowResolved(e.target.checked)}
                className="rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
              />
              Show resolved
            </label>
          </div>
        </div>
      </div>

      {/* Error List */}
      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="h-10 w-10 animate-pulse rounded-lg bg-gray-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
                  <div className="h-3 w-1/2 animate-pulse rounded bg-gray-200" />
                </div>
              </div>
            </div>
          ))
        ) : filteredErrors.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
            <p className="mt-4 text-sm font-medium text-gray-900">No errors found</p>
            <p className="mt-1 text-xs text-gray-500">All systems are operating normally</p>
          </div>
        ) : (
          filteredErrors.map((error) => {
            const style = severityStyles[error.severity];
            const isExpanded = expandedError === error.id;

            return (
              <div
                key={error.id}
                className={`rounded-xl border bg-white shadow-sm transition-all ${
                  error.resolved ? "border-gray-200 opacity-60" : style.border
                }`}
              >
                <div
                  className="flex cursor-pointer items-start gap-4 p-5"
                  onClick={() => setExpandedError(isExpanded ? null : error.id)}
                >
                  <div className={`rounded-lg p-2 ${style.bg}`}>
                    {error.severity === "critical" ? (
                      <XCircle className={`h-5 w-5 ${style.text}`} />
                    ) : error.severity === "error" ? (
                      <AlertTriangle className={`h-5 w-5 ${style.text}`} />
                    ) : (
                      <Clock className={`h-5 w-5 ${style.text}`} />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>
                            {error.severity}
                          </span>
                          {error.resolved && (
                            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                              Resolved
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-sm font-medium text-gray-900">{error.message}</p>
                        <p className="mt-1 text-xs text-gray-500">
                          {error.productionName} → {error.itemName}
                          {error.messageId && ` • Message: ${error.messageId}`}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">
                          {new Date(error.timestamp).toLocaleString()}
                        </span>
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50 p-5">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <h4 className="text-xs font-medium uppercase text-gray-500">Source</h4>
                        <p className="mt-1 text-sm text-gray-900">{error.source}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-medium uppercase text-gray-500">Retry Count</h4>
                        <p className="mt-1 text-sm text-gray-900">{error.retryCount}</p>
                      </div>
                      {error.resolved && (
                        <>
                          <div>
                            <h4 className="text-xs font-medium uppercase text-gray-500">Resolved At</h4>
                            <p className="mt-1 text-sm text-gray-900">
                              {error.resolvedAt ? new Date(error.resolvedAt).toLocaleString() : "-"}
                            </p>
                          </div>
                          <div>
                            <h4 className="text-xs font-medium uppercase text-gray-500">Resolved By</h4>
                            <p className="mt-1 text-sm text-gray-900">{error.resolvedBy || "-"}</p>
                          </div>
                        </>
                      )}
                    </div>

                    {error.stackTrace && (
                      <div className="mt-4">
                        <h4 className="text-xs font-medium uppercase text-gray-500">Stack Trace</h4>
                        <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100">
                          {error.stackTrace}
                        </pre>
                      </div>
                    )}

                    {!error.resolved && (
                      <div className="mt-4 flex items-center gap-3">
                        <button className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue">
                          <RotateCcw className="h-4 w-4" />
                          Retry
                        </button>
                        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                          <CheckCircle className="h-4 w-4" />
                          Mark Resolved
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
