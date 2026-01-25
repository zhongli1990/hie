"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  MessageSquare,
  Network,
  RefreshCw,
  XCircle,
} from "lucide-react";
import {
  getDashboardStats,
  getDashboardActivity,
  getDashboardProjects,
  DashboardStats,
  DashboardActivity,
  DashboardProject,
} from "@/lib/api-v2";
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
  const [activities, setActivities] = useState<DashboardActivity[]>([]);
  const [projects, setProjects] = useState<DashboardProject[]>([]);
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadDashboardData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    
    try {
      const [statsData, activityData, projectsData] = await Promise.all([
        getDashboardStats(),
        getDashboardActivity(10),
        getDashboardProjects(),
      ]);
      
      setStats(statsData);
      setActivities(activityData.activities || []);
      setProjects(projectsData.projects || []);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(() => {
      loadDashboardData(true);
    }, 10000);
    
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  const toggleProject = (projectId: string) => {
    setExpandedProjects(prev => {
      const next = new Set(prev);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  };

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
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={() => loadDashboardData(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Projects"
          value={stats?.projects_count ?? 0}
          subtitle={`${stats?.projects_running ?? 0} running`}
          icon={Network}
          loading={loading}
        />
        <MetricCard
          title="Total Items"
          value={stats?.items_count ?? 0}
          subtitle={`${stats?.items_services ?? 0} services, ${stats?.items_processes ?? 0} processes, ${stats?.items_operations ?? 0} operations`}
          icon={Activity}
          loading={loading}
        />
        <MetricCard
          title="Messages Today"
          value={stats?.messages_today ?? 0}
          trend={stats?.message_trend ? { value: Math.abs(stats.message_trend), positive: stats.message_trend >= 0 } : undefined}
          icon={MessageSquare}
          loading={loading}
        />
        <MetricCard
          title="Error Rate"
          value={stats ? `${(stats.error_rate * 100).toFixed(2)}%` : "0%"}
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
            ) : activities.length > 0 ? (
              activities.map((activity) => (
                <div key={activity.id} className="px-5 py-3 transition-colors hover:bg-gray-50">
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
                          {activity.project_name}
                          {activity.item_name && ` → ${activity.item_name}`}
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

        {/* Projects Tree & Quick Actions */}
        <div className="space-y-6">
          {/* Projects Overview */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
              <h2 className="text-sm font-semibold text-gray-900">Projects Overview</h2>
              <Link href="/projects" className="text-xs text-nhs-blue hover:underline">
                View all
              </Link>
            </div>
            <div className="divide-y divide-gray-100">
              {loading ? (
                <div className="space-y-3 p-5">
                  {[1, 2].map((i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="h-4 w-4 animate-pulse rounded bg-gray-200" />
                      <div className="h-4 w-32 animate-pulse rounded bg-gray-200" />
                    </div>
                  ))}
                </div>
              ) : projects.length > 0 ? (
                projects.map((project) => (
                  <div key={project.id}>
                    <div
                      className="flex cursor-pointer items-center justify-between px-5 py-3 hover:bg-gray-50"
                      onClick={() => toggleProject(project.id)}
                    >
                      <div className="flex items-center gap-2">
                        {expandedProjects.has(project.id) ? (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400" />
                        )}
                        <span className={`h-2 w-2 rounded-full ${project.state === 'running' ? 'bg-green-500' : 'bg-gray-400'}`} />
                        <span className="text-sm font-medium text-gray-900">{project.display_name || project.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500">{project.message_count} msg</span>
                        {project.error_count > 0 && (
                          <span className="text-xs text-red-600">{project.error_count} errors</span>
                        )}
                        <StatusBadge status={project.state} />
                      </div>
                    </div>
                    {expandedProjects.has(project.id) && project.items.length > 0 && (
                      <div className="border-t border-gray-100 bg-gray-50 py-2">
                        {project.items.map((item) => (
                          <Link
                            key={item.id}
                            href={`/messages?project=${project.id}&item=${item.name}`}
                            className="flex items-center justify-between px-5 py-2 pl-12 hover:bg-gray-100"
                          >
                            <div className="flex items-center gap-2">
                              <span className={`h-1.5 w-1.5 rounded-full ${item.enabled ? 'bg-green-400' : 'bg-gray-300'}`} />
                              <span className="text-xs text-gray-700">{item.name}</span>
                              <span className="text-xs text-gray-400">({item.type})</span>
                            </div>
                            <span className="text-xs text-gray-500">{item.message_count} msg</span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-5 text-center text-sm text-gray-500">
                  No projects found
                </div>
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
