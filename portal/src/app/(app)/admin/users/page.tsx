"use client";

import { useState, useEffect, useCallback } from "react";
import {
  User,
  fetchUsers,
  approveUser,
  rejectUser,
  activateUser,
  deactivateUser,
  unlockUser,
} from "@/lib/auth";
import {
  Users,
  Search,
  Check,
  X,
  Lock,
  Unlock,
  UserMinus,
  UserPlus,
  MoreVertical,
  Shield,
  Clock,
  AlertCircle,
} from "lucide-react";

type UserStatus = "pending" | "active" | "inactive" | "locked" | "rejected";

const statusConfig: Record<UserStatus, { color: string; icon: typeof Clock; label: string }> = {
  pending: { color: "bg-amber-100 text-amber-700", icon: Clock, label: "Pending" },
  active: { color: "bg-green-100 text-green-700", icon: Check, label: "Active" },
  inactive: { color: "bg-gray-100 text-gray-600", icon: UserMinus, label: "Inactive" },
  locked: { color: "bg-red-100 text-red-700", icon: Lock, label: "Locked" },
  rejected: { color: "bg-red-100 text-red-700", icon: X, label: "Rejected" },
};

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    setError("");

    try {
      const data = await fetchUsers(statusFilter === "all" ? undefined : statusFilter);
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch users");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleAction = async (
    userId: string,
    action: "approve" | "reject" | "activate" | "deactivate" | "unlock"
  ) => {
    setActionLoading(userId);

    try {
      switch (action) {
        case "approve":
          await approveUser(userId);
          break;
        case "reject":
          await rejectUser(userId);
          break;
        case "activate":
          await activateUser(userId);
          break;
        case "deactivate":
          await deactivateUser(userId);
          break;
        case "unlock":
          await unlockUser(userId);
          break;
      }
      await loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : `Failed to ${action} user`);
    } finally {
      setActionLoading(null);
    }
  };

  const filteredUsers = users.filter((user) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      user.email.toLowerCase().includes(term) ||
      user.display_name.toLowerCase().includes(term) ||
      (user.department?.toLowerCase().includes(term) ?? false)
    );
  });

  const pendingCount = users.filter((u) => u.status === "pending").length;

  const statusCounts = {
    all: users.length,
    pending: users.filter((u) => u.status === "pending").length,
    active: users.filter((u) => u.status === "active").length,
    inactive: users.filter((u) => u.status === "inactive").length,
    locked: users.filter((u) => u.status === "locked").length,
    rejected: users.filter((u) => u.status === "rejected").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">User Management</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage user accounts, approvals, and access control
          </p>
        </div>
        {pendingCount > 0 && (
          <div className="flex items-center gap-2 rounded-full bg-amber-100 px-4 py-2 text-sm font-medium text-amber-800">
            <AlertCircle className="h-4 w-4" />
            {pendingCount} pending approval{pendingCount > 1 ? "s" : ""}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          {(["all", "pending", "active", "inactive", "locked", "rejected"] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                statusFilter === status
                  ? "bg-nhs-blue text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
              <span className="ml-1.5 text-xs opacity-75">({statusCounts[status]})</span>
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-nhs-blue focus:outline-none focus:ring-2 focus:ring-nhs-blue/20 sm:w-64"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading users...</div>
        ) : filteredUsers.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm font-medium text-gray-900">No users found</p>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm ? "Try adjusting your search" : "No users match the current filter"}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  User
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Role
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  Last Login
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredUsers.map((user) => {
                const status = user.status as UserStatus;
                const config = statusConfig[status] || statusConfig.inactive;
                const StatusIcon = config.icon;

                return (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-nhs-blue/10 text-nhs-blue">
                          <span className="text-sm font-medium">
                            {user.display_name
                              .split(" ")
                              .map((n) => n[0])
                              .join("")
                              .slice(0, 2)
                              .toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{user.display_name}</p>
                          <p className="text-sm text-gray-500">{user.email}</p>
                          {user.department && (
                            <p className="text-xs text-gray-400">{user.department}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4 text-gray-400" />
                        <span className="text-sm text-gray-600">
                          {user.role_name || "Unknown"}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${config.color}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {config.label}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-500">
                      {user.last_login_at
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : "Never"}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {user.status === "pending" && (
                          <>
                            <button
                              onClick={() => handleAction(user.id, "approve")}
                              disabled={actionLoading === user.id}
                              className="rounded-lg bg-green-100 p-2 text-green-700 hover:bg-green-200 disabled:opacity-50"
                              title="Approve"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleAction(user.id, "reject")}
                              disabled={actionLoading === user.id}
                              className="rounded-lg bg-red-100 p-2 text-red-700 hover:bg-red-200 disabled:opacity-50"
                              title="Reject"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </>
                        )}
                        {user.status === "active" && (
                          <button
                            onClick={() => handleAction(user.id, "deactivate")}
                            disabled={actionLoading === user.id}
                            className="rounded-lg bg-gray-100 p-2 text-gray-600 hover:bg-gray-200 disabled:opacity-50"
                            title="Deactivate"
                          >
                            <UserMinus className="h-4 w-4" />
                          </button>
                        )}
                        {user.status === "locked" && (
                          <button
                            onClick={() => handleAction(user.id, "unlock")}
                            disabled={actionLoading === user.id}
                            className="rounded-lg bg-amber-100 p-2 text-amber-700 hover:bg-amber-200 disabled:opacity-50"
                            title="Unlock"
                          >
                            <Unlock className="h-4 w-4" />
                          </button>
                        )}
                        {(user.status === "inactive" || user.status === "rejected") && (
                          <button
                            onClick={() => handleAction(user.id, "activate")}
                            disabled={actionLoading === user.id}
                            className="rounded-lg bg-green-100 p-2 text-green-700 hover:bg-green-200 disabled:opacity-50"
                            title="Activate"
                          >
                            <UserPlus className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                          title="More actions"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Summary */}
      {!isLoading && filteredUsers.length > 0 && (
        <div className="text-sm text-gray-500">
          Showing {filteredUsers.length} of {users.length} users
        </div>
      )}
    </div>
  );
}
