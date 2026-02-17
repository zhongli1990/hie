"use client";

import { Fragment, useState, useEffect, useCallback } from "react";
import {
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Shield,
  AlertTriangle,
  MessageSquare,
} from "lucide-react";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";

// ── Types matching prompt-manager ApprovalResponse schema ─────────────────

interface Approval {
  id: string;
  tenant_id: string | null;
  requested_by: string;
  requested_role: string;
  workspace_id: string | null;
  project_id: string | null;
  project_name: string | null;
  environment: string;
  status: string;
  reviewed_by: string | null;
  review_notes: string | null;
  safety_report: Record<string, unknown> | null;
  config_snapshot: Record<string, unknown> | null;
  created_at: string;
  reviewed_at: string | null;
}

interface ApprovalListResponse {
  approvals: Approval[];
  total: number;
}

// ── Status display config ─────────────────────────────────────────────────

const statusConfig: Record<string, { color: string; icon: typeof CheckCircle; label: string }> = {
  pending:  { color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", icon: Clock, label: "Pending" },
  approved: { color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400", icon: CheckCircle, label: "Approved" },
  rejected: { color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", icon: XCircle, label: "Rejected" },
};

const PAGE_SIZE = 50;

// ── Component ─────────────────────────────────────────────────────────────

export default function ApprovalsPage() {
  const { isAdmin, user } = useAuth();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(0);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // Review modal state
  const [reviewTarget, setReviewTarget] = useState<{ id: string; action: "approve" | "reject" } | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ── Data Loading ──────────────────────────────────────────────────────────

  const loadApprovals = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      const params = new URLSearchParams();
      if (statusFilter !== "all") params.set("status", statusFilter);
      params.set("offset", String(page * PAGE_SIZE));
      params.set("limit", String(PAGE_SIZE));

      const res = await fetch(`/api/prompt-manager/approvals?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to fetch approvals");
      }

      const data: ApprovalListResponse = await res.json();
      setApprovals(data.approvals);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  // ── Approve / Reject ──────────────────────────────────────────────────────

  const handleReviewSubmit = async () => {
    if (!reviewTarget) return;
    setIsSubmitting(true);
    setError("");

    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");

      const endpoint = reviewTarget.action === "approve"
        ? `/api/prompt-manager/approvals/${reviewTarget.id}/approve`
        : `/api/prompt-manager/approvals/${reviewTarget.id}/reject`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          review_notes: reviewNotes || null,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to ${reviewTarget.action} deployment`);
      }

      // Close modal and refresh
      setReviewTarget(null);
      setReviewNotes("");
      await loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Client-side search filter ─────────────────────────────────────────────

  const filteredApprovals = approvals.filter((a) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (a.project_name || "").toLowerCase().includes(term) ||
      a.requested_by.toLowerCase().includes(term) ||
      a.requested_role.toLowerCase().includes(term) ||
      a.environment.toLowerCase().includes(term) ||
      (a.reviewed_by || "").toLowerCase().includes(term)
    );
  });

  // ── Compute stats from the current page data (client-side) ────────────────

  const pendingCount = approvals.filter((a) => a.status === "pending").length;
  const approvedCount = approvals.filter((a) => a.status === "approved").length;
  const rejectedCount = approvals.filter((a) => a.status === "rejected").length;

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // ── Determine if current user can approve/reject ──────────────────────────

  const userRoleName = (user?.role_name || "").toLowerCase();
  const canReview =
    isAdmin ||
    userRoleName === "super administrator" ||
    userRoleName === "tenant administrator" ||
    userRoleName === "clinical safety officer";

  // ── Permission gate ───────────────────────────────────────────────────────

  if (!isAdmin && !canReview) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500 dark:text-gray-400">You do not have permission to view deployment approvals.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Deployment Approvals</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Review and approve production deployments. Developers cannot deploy without CSO or Admin approval.
          </p>
        </div>
        <button
          onClick={loadApprovals}
          className="flex items-center gap-2 rounded-lg bg-nhs-blue px-3 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Pending Review", value: statusFilter === "all" ? pendingCount : (statusFilter === "pending" ? total : 0), color: "text-amber-700 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-900/20", icon: Clock },
          { label: "Approved", value: statusFilter === "all" ? approvedCount : (statusFilter === "approved" ? total : 0), color: "text-green-700 dark:text-green-400", bg: "bg-green-50 dark:bg-green-900/20", icon: CheckCircle },
          { label: "Rejected", value: statusFilter === "all" ? rejectedCount : (statusFilter === "rejected" ? total : 0), color: "text-red-700 dark:text-red-400", bg: "bg-red-50 dark:bg-red-900/20", icon: XCircle },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`rounded-xl ${stat.bg} border border-gray-200 dark:border-zinc-700 p-4`}>
              <div className="flex items-center gap-2">
                <Icon className={`h-5 w-5 ${stat.color}`} />
                <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
              </div>
              <p className={`text-2xl font-semibold mt-1 ${stat.color}`}>{stat.value}</p>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          {["all", "pending", "approved", "rejected"].map((s) => (
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

        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by project, user, role..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="rounded-lg border border-gray-300 dark:border-zinc-600 py-2 pl-10 pr-4 text-sm bg-white dark:bg-zinc-800 text-gray-900 dark:text-white focus:border-nhs-blue focus:outline-none focus:ring-2 focus:ring-nhs-blue/20 w-72"
          />
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
            Loading approvals...
          </div>
        ) : filteredApprovals.length === 0 ? (
          <div className="p-8 text-center">
            <Shield className="mx-auto h-12 w-12 text-gray-300 dark:text-zinc-600" />
            <p className="mt-4 text-sm font-medium text-gray-900 dark:text-white">No approval requests found</p>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Approval requests appear here when developers attempt to deploy to production.
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Requested</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Requester</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Project</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Environment</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-zinc-700">
              {filteredApprovals.map((approval) => {
                const sc = statusConfig[approval.status] || statusConfig.pending;
                const StatusIcon = sc.icon;
                const isExpanded = expandedRow === approval.id;
                const isPending = approval.status === "pending";
                return (
                  <Fragment key={approval.id}>
                    <tr
                      onClick={() => setExpandedRow(isExpanded ? null : approval.id)}
                      className="hover:bg-gray-50 dark:hover:bg-zinc-700/50 cursor-pointer"
                    >
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5" />
                          {new Date(approval.created_at).toLocaleString()}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white truncate max-w-[140px]" title={approval.requested_by}>
                        {approval.requested_by}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-full bg-gray-100 dark:bg-zinc-700 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                          {approval.requested_role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                        {approval.project_name || approval.project_id || "-"}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/30 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-400">
                          {approval.environment}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${sc.color}`}>
                          <StatusIcon className="h-3.5 w-3.5" />
                          {sc.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {isPending && canReview ? (
                          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => { setReviewTarget({ id: approval.id, action: "approve" }); setReviewNotes(""); }}
                              className="rounded-md bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700 transition-colors"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => { setReviewTarget({ id: approval.id, action: "reject" }); setReviewNotes(""); }}
                              className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-700 transition-colors"
                            >
                              Reject
                            </button>
                          </div>
                        ) : isPending ? (
                          <span className="text-xs text-gray-400 dark:text-gray-500">Awaiting review</span>
                        ) : (
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            {approval.reviewed_by ? `by ${approval.reviewed_by}` : "-"}
                          </span>
                        )}
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={7} className="px-4 py-4 bg-gray-50 dark:bg-zinc-900">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            {/* Review Info */}
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Review Details</p>
                              <div className="bg-white dark:bg-zinc-800 rounded-lg p-3 border border-gray-200 dark:border-zinc-700 space-y-2">
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Reviewer:</span>
                                  <span className="text-gray-900 dark:text-white font-medium">{approval.reviewed_by || "Pending"}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Reviewed at:</span>
                                  <span className="text-gray-900 dark:text-white">{approval.reviewed_at ? new Date(approval.reviewed_at).toLocaleString() : "-"}</span>
                                </div>
                                {approval.review_notes && (
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 block mb-1">Notes:</span>
                                    <p className="text-gray-700 dark:text-gray-300 text-xs bg-gray-50 dark:bg-zinc-900 rounded p-2">{approval.review_notes}</p>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* IDs and Metadata */}
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Request Metadata</p>
                              <div className="bg-white dark:bg-zinc-800 rounded-lg p-3 border border-gray-200 dark:border-zinc-700 space-y-2">
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Approval ID:</span>
                                  <span className="text-gray-900 dark:text-white font-mono text-xs">{approval.id}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Workspace:</span>
                                  <span className="text-gray-900 dark:text-white font-mono text-xs">{approval.workspace_id || "-"}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Project ID:</span>
                                  <span className="text-gray-900 dark:text-white font-mono text-xs">{approval.project_id || "-"}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500 dark:text-gray-400">Tenant:</span>
                                  <span className="text-gray-900 dark:text-white font-mono text-xs">{approval.tenant_id || "Platform"}</span>
                                </div>
                              </div>
                            </div>

                            {/* Config Snapshot */}
                            {approval.config_snapshot && (
                              <div className="col-span-2">
                                <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Configuration Snapshot</p>
                                <pre className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 bg-white dark:bg-zinc-800 rounded-lg p-3 border border-gray-200 dark:border-zinc-700 text-xs max-h-48 overflow-auto">
                                  {JSON.stringify(approval.config_snapshot, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Safety Report */}
                            {approval.safety_report && (
                              <div className="col-span-2">
                                <p className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">Safety Report (DCB0129)</p>
                                <pre className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 bg-white dark:bg-zinc-800 rounded-lg p-3 border border-gray-200 dark:border-zinc-700 text-xs max-h-48 overflow-auto">
                                  {JSON.stringify(approval.safety_report, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
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
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()} requests
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

      {!isLoading && filteredApprovals.length > 0 && total <= PAGE_SIZE && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Showing {filteredApprovals.length} of {total} requests
        </p>
      )}

      {/* Review Modal */}
      {reviewTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 p-6 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              {reviewTarget.action === "approve" ? (
                <div className="flex items-center justify-center h-10 w-10 rounded-full bg-green-100 dark:bg-green-900/30">
                  <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
              ) : (
                <div className="flex items-center justify-center h-10 w-10 rounded-full bg-red-100 dark:bg-red-900/30">
                  <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
              )}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {reviewTarget.action === "approve" ? "Approve Deployment" : "Reject Deployment"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {reviewTarget.action === "approve"
                    ? "This will allow the deployment to proceed to production."
                    : "The requester will be notified that their deployment was rejected."}
                </p>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                <div className="flex items-center gap-1.5">
                  <MessageSquare className="h-4 w-4" />
                  Review Notes {reviewTarget.action === "reject" && <span className="text-red-500">*</span>}
                </div>
              </label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                rows={3}
                placeholder={
                  reviewTarget.action === "approve"
                    ? "Optional: Add approval notes..."
                    : "Required: Explain why this deployment is rejected..."
                }
                className="w-full rounded-lg border border-gray-300 dark:border-zinc-600 p-3 text-sm bg-white dark:bg-zinc-900 text-gray-900 dark:text-white focus:border-nhs-blue focus:outline-none focus:ring-2 focus:ring-nhs-blue/20 resize-none"
              />
            </div>

            {reviewTarget.action === "reject" && !reviewNotes.trim() && (
              <div className="mb-4 flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5" />
                Review notes are required when rejecting a deployment.
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => { setReviewTarget(null); setReviewNotes(""); }}
                disabled={isSubmitting}
                className="rounded-lg border border-gray-300 dark:border-zinc-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReviewSubmit}
                disabled={isSubmitting || (reviewTarget.action === "reject" && !reviewNotes.trim())}
                className={`rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50 ${
                  reviewTarget.action === "approve"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {isSubmitting
                  ? "Submitting..."
                  : reviewTarget.action === "approve"
                    ? "Confirm Approval"
                    : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
