"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Clock,
  MessageSquare,
  Network,
  Play,
  XCircle,
} from "lucide-react";
import type { DashboardStats, SystemHealth } from "@/types";
import { formatNumber, formatRelativeTime } from "@/lib/utils";

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  loading,
}: {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: { value: number; positive: boolean };
  loading?: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            {loading ? (
              <span className="inline-block h-8 w-16 animate-pulse rounded bg-gray-200" />
            ) : (
              typeof value === "number" ? formatNumber(value) : value
            )}
          </p>
          {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
          {trend && (
            <p className={`mt-1 text-xs ${trend.positive ? "text-green-600" : "text-red-600"}`}>
              {trend.positive ? "↑" : "↓"} {trend.value}% from yesterday
            </p>
          )}
        </div>
        <div className="rounded-lg bg-nhs-blue/10 p-2">
          <Icon className="h-5 w-5 text-nhs-blue" />
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: "bg-green-100 text-green-700",
    healthy: "bg-green-100 text-green-700",
    stopped: "bg-gray-100 text-gray-600",
    paused: "bg-yellow-100 text-yellow-700",
    error: "bg-red-100 text-red-700",
    unhealthy: "bg-red-100 text-red-700",
  };

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] || "bg-gray-100 text-gray-600"}`}>
      {status === "running" || status === "healthy" ? (
        <CheckCircle className="h-3 w-3" />
      ) : status === "error" || status === "unhealthy" ? (
        <XCircle className="h-3 w-3" />
      ) : (
        <Clock className="h-3 w-3" />
      )}
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulated data for now - will be replaced with API calls
    const mockStats: DashboardStats = {
      productionsCount: 3,
      itemsCount: 24,
      messagesProcessedToday: 45892,
      messagesProcessedTotal: 1284567,
      errorRate: 0.02,
      recentActivity: [
        {
          type: "message",
          description: "ADT^A01 processed successfully",
          productionName: "NHS-ADT-Integration",
          itemName: "HTTP_ADT_Receiver",
          timestamp: new Date(Date.now() - 60000).toISOString(),
        },
        {
          type: "error",
          description: "Connection timeout to PAS system",
          productionName: "NHS-ADT-Integration",
          itemName: "PAS_MLLP_Sender",
          timestamp: new Date(Date.now() - 300000).toISOString(),
        },
        {
          type: "state_change",
          description: "Production started",
          productionName: "Lab-Results-Feed",
          timestamp: new Date(Date.now() - 600000).toISOString(),
        },
      ],
    };

    const mockHealth: SystemHealth = {
      services: [
        { service: "PostgreSQL", status: "healthy", latencyMs: 2 },
        { service: "Redis", status: "healthy", latencyMs: 1 },
        { service: "HIE Engine", status: "healthy", latencyMs: 5 },
        { service: "Management API", status: "healthy", latencyMs: 3 },
      ],
    };

    setTimeout(() => {
      setStats(mockStats);
      setHealth(mockHealth);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Healthcare Integration Engine overview
          </p>
        </div>
        <Link
          href="/productions/new"
          className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue"
        >
          <Play className="h-4 w-4" />
          New Production
        </Link>
      </div>

      {/* Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Active Productions"
          value={stats?.productionsCount ?? 0}
          subtitle="3 running, 0 stopped"
          icon={Network}
          loading={loading}
        />
        <MetricCard
          title="Total Items"
          value={stats?.itemsCount ?? 0}
          subtitle="8 services, 6 processes, 10 operations"
          icon={Activity}
          loading={loading}
        />
        <MetricCard
          title="Messages Today"
          value={stats?.messagesProcessedToday ?? 0}
          trend={{ value: 12, positive: true }}
          icon={MessageSquare}
          loading={loading}
        />
        <MetricCard
          title="Error Rate"
          value={stats ? `${(stats.errorRate * 100).toFixed(2)}%` : "0%"}
          subtitle="Last 24 hours"
          icon={AlertTriangle}
          loading={loading}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-900">Recent Activity</h2>
            <Link href="/logs" className="text-xs text-nhs-blue hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {loading ? (
              <div className="space-y-3 p-5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-8 w-8 animate-pulse rounded-full bg-gray-200" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
                      <div className="h-3 w-1/2 animate-pulse rounded bg-gray-200" />
                    </div>
                  </div>
                ))}
              </div>
            ) : stats?.recentActivity.length ? (
              stats.recentActivity.map((activity, idx) => (
                <div key={idx} className="px-5 py-3 transition-colors hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div
                        className={`mt-0.5 h-2 w-2 rounded-full ${
                          activity.type === "error"
                            ? "bg-red-500"
                            : activity.type === "message"
                            ? "bg-green-500"
                            : "bg-blue-500"
                        }`}
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {activity.description}
                        </p>
                        <p className="mt-0.5 text-xs text-gray-500">
                          {activity.productionName}
                          {activity.itemName && ` → ${activity.itemName}`}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-gray-400">
                      {formatRelativeTime(activity.timestamp)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-5 text-center text-sm text-gray-500">
                No recent activity
              </div>
            )}
          </div>
        </div>

        {/* System Health & Quick Actions */}
        <div className="space-y-6">
          {/* System Health */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-200 px-5 py-4">
              <h2 className="text-sm font-semibold text-gray-900">System Health</h2>
            </div>
            <div className="p-5">
              {loading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
                      <div className="h-5 w-16 animate-pulse rounded bg-gray-200" />
                    </div>
                  ))}
                </div>
              ) : health?.services ? (
                <div className="space-y-3">
                  {health.services.map((service) => (
                    <div key={service.service} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{service.service}</span>
                      <div className="flex items-center gap-2">
                        {service.latencyMs !== null && (
                          <span className="text-xs text-gray-400">{service.latencyMs}ms</span>
                        )}
                        <StatusBadge status={service.status} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Unable to fetch system status</p>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-200 px-5 py-4">
              <h2 className="text-sm font-semibold text-gray-900">Quick Actions</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 p-5">
              <Link
                href="/productions"
                className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 transition-colors hover:border-gray-300 hover:bg-gray-50"
              >
                <Network className="h-5 w-5 text-nhs-blue" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Productions</p>
                  <p className="text-xs text-gray-500">Manage integrations</p>
                </div>
              </Link>
              <Link
                href="/messages"
                className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 transition-colors hover:border-gray-300 hover:bg-gray-50"
              >
                <MessageSquare className="h-5 w-5 text-nhs-blue" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Messages</p>
                  <p className="text-xs text-gray-500">Search & trace</p>
                </div>
              </Link>
              <Link
                href="/errors"
                className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 transition-colors hover:border-gray-300 hover:bg-gray-50"
              >
                <AlertTriangle className="h-5 w-5 text-nhs-blue" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Errors</p>
                  <p className="text-xs text-gray-500">View failures</p>
                </div>
              </Link>
              <Link
                href="/monitoring"
                className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 transition-colors hover:border-gray-300 hover:bg-gray-50"
              >
                <Activity className="h-5 w-5 text-nhs-blue" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Monitoring</p>
                  <p className="text-xs text-gray-500">Real-time metrics</p>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
