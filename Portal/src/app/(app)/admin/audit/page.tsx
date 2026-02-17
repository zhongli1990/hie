"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ClipboardList,
  Search,
  RefreshCw,
  Download,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";

interface AuditEntry {
  id: string;
  tenant_id: string | null;
  user_id: string;
  user_role: string;
  session_id: string | null;
  run_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  input_summary: string | null;
  result_status: string;
  result_summary: string | null;
  created_at: string;
}

interface AuditListResponse {
  entries: AuditEntry[];
  total: number;
}

interface AuditStats {
  total: number;
  success: number;
  denied: number;
  errors: number;
}

const statusConfig: Record<string, { color: string; icon: typeof CheckCircle; label: string }> = {
  success: { color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400", icon: CheckCircle, label: "Success" },
  denied: { color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", icon: AlertTriangle, label: "Denied" },
  error: { color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", icon: XCircle, label: "Error" },
};

const PAGE_SIZE = 50;

export default function AuditLogPage() {
  const { isAdmin } = useAuth();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(0);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      const params = new URLSearchParams();
      if (statusFilter !== "all") params.set("result_status", statusFilter);
      if (actionFilter) params.set("action", actionFilter);
      params.set("offset", String(page * PAGE_SIZE));
      params.set("limit", String(PAGE_SIZE));

      const res = await fetch(`/api/prompt-manager/audit?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to fetch audit log");
      }

      const data: AuditListResponse = await res.json();
      setEntries(data.entries);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit log");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, actionFilter, page]);

  const loadStats = useCallback(async () => {
    try {
      const token = getToken();
      if (!token) return;

      const res = await fetch("/api/prompt-manager/audit/stats", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        setStats(await res.json());
      }
    } catch {
      // Stats are non-critical
    }
  }, []);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const filteredEntries = entries.filter((entry) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      entry.action.toLowerCase().includes(term) ||
      entry.user_id.toLowerCase().includes(term) ||
      entry.user_role.toLowerCase().includes(term) ||
      (entry.target_type || "").toLowerCase().includes(term) ||
      (entry.target_id || "").toLowerCase().includes(term)
    );
  });

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleExportCSV = () => {
    const headers = ["Time", "User", "Role", "Action", "Status", "Target", "Input Summary"];
    const rows = filteredEntries.map((e) => [
      new Date(e.created_at).toISOString(),
      e.user_id,
      e.user_role,
      e.action,
      e.result_status,
      [e.target_type, e.target_id].filter(Boolean).join(":"),
      (e.input_summary || "").replace(/"/g, '""'),
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.map((c) => `"${c}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500 dark:text-gray-400">You do not have permission to view audit logs.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Audit Log</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            NHS DCB0129/DCB0160 compliant audit trail for all AI agent actions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={filteredEntries.length === 0}
            className="flex items-center gap-2 rounded-lg border border-gray-300 dark:border-zinc-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
          <button
            onClick={() => { loadEntries(); loadStats(); }}
            className="flex items-center gap-2 rounded-lg bg-nhs-blue px-3 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total Actions", value: stats.total, color: "text-nhs-blue", bg: "bg-blue-50 dark:bg-blue-900/20" },
            { label: "Successful", value: stats.success, color: "text-green-700 dark:text-green-400", bg: "bg-green-50 dark:bg-green-900/20" },
            { label: "Denied", value: stats.denied, color: "text-amber-700 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-900/20" },
            { label: "Errors", value: stats.errors, color: "text-red-700 dark:text-red-400", bg: "bg-red-50 dark:bg-red-900/20" },
          ].map((stat) => (
            <div key={stat.label} className={`rounded-xl ${stat.bg} border border-gray-200 dark:border-zinc-700 p-4`}>
              <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
              <p className={`text-2xl font-semibold ${stat.color}`}>{stat.value.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          {["all", "success", "denied", "error"].map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(0); }}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                statusFilter === s
                  ? "bg-nhs-blue text-white"
                  : "bg-gray-100 dark:bg-zinc-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-zinc-600"
              }`}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Filter by action..."
              value={actionFilter}
              onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
              className="rounded-lg border border-gray-300 dark:border-zinc-600 py-2 pl-10 pr-4 text-sm bg-white dark:bg-zinc-800 text-gray-900 dark:text-white focus:border-nhs-blue focus:outline-none focus:ring-2 focus:ring-nhs-blue/20 w-48"
            />
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search entries..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="rounded-lg border border-gray-300 dark:border-zinc-600 py-2 pl-10 pr-4 text-sm bg-white dark:bg-zinc-800 text-gray-900 dark:text-white focus:border-nhs-blue focus:outline-none focus:ring-2 focus:ring-nhs-blue/20 w-64"
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <RefreshCw className="mx-auto h-8 w-8 animate-spin text-nhs-blue mb-2" />
            Loading audit entries...
          </div>
        ) : filteredEntries.length === 0 ? (
          <div className="p-8 text-center">
            <ClipboardList className="mx-auto h-12 w-12 text-gray-300 dark:text-zinc-600" />
            <p className="mt-4 text-sm font-medium text-gray-900 dark:text-white">No audit entries found</p>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Try adjusting your filters or check back later</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Time</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">User</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Action</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Target</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-zinc-700">
              {filteredEntries.map((entry) => {
                const sc = statusConfig[entry.result_status] || statusConfig.success;
                const StatusIcon = sc.icon;
                const isExpanded = expandedRow === entry.id;
                return (
                  <>
                    <tr
                      key={entry.id}
                      onClick={() => setExpandedRow(isExpanded ? null : entry.id)}
                      className="hover:bg-gray-50 dark:hover:bg-zinc-700/50 cursor-pointer"
                    >
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5" />
                          {new Date(entry.created_at).toLocaleString()}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white truncate max-w-[140px]" title={entry.user_id}>
                        {entry.user_id}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-full bg-gray-100 dark:bg-zinc-700 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                          {entry.user_role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-white">
                        {entry.action}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 truncate max-w-[160px]">
                        {entry.target_type && entry.target_id
                          ? `${entry.target_type}:${entry.target_id}`
                          : entry.target_type || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${sc.color}`}>
                          <StatusIcon className="h-3.5 w-3.5" />
                          {sc.label}
                        </span>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${entry.id}-detail`}>
                        <td colSpan={6} className="px-4 py-4 bg-gray-50 dark:bg-zinc-900">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Input Summary</p>
                              <pre className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 bg-white dark:bg-zinc-800 rounded-lg p-3 border border-gray-200 dark:border-zinc-700 text-xs max-h-40 overflow-auto">
                                {entry.input_summary || "No input recorded"}
                              </pre>
                            </div>
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Result Summary</p>
                              <pre className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 bg-white dark:bg-zinc-800 rounded-lg p-3 border border-gray-200 dark:border-zinc-700 text-xs max-h-40 overflow-auto">
                                {entry.result_summary || "No result recorded"}
                              </pre>
                            </div>
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Session</p>
                              <p className="text-gray-700 dark:text-gray-300 font-mono text-xs">{entry.session_id || "-"}</p>
                            </div>
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Run ID</p>
                              <p className="text-gray-700 dark:text-gray-300 font-mono text-xs">{entry.run_id || "-"}</p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {!isLoading && total > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()} entries
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="flex items-center gap-1 rounded-lg border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 disabled:opacity-50 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="flex items-center gap-1 rounded-lg border border-gray-300 dark:border-zinc-600 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 disabled:opacity-50 transition-colors"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Footer info */}
      {!isLoading && filteredEntries.length > 0 && total <= PAGE_SIZE && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Showing {filteredEntries.length} of {total} entries
        </p>
      )}
    </div>
  );
}
