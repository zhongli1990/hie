"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  Clock,
  Cpu,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  Wifi,
  Zap,
} from "lucide-react";
import {
  getMonitoringMetrics,
  getMonitoringThroughput,
  getMonitoringProjects,
  MonitoringMetrics,
  MonitoringThroughputPoint,
  MonitoringProject,
} from "@/lib/api-v2";

interface MetricData {
  current: number;
  previous: number;
  unit: string;
  trend: "up" | "down" | "stable";
}

interface SystemMetrics {
  messagesPerSecond: MetricData;
  avgLatency: MetricData;
  errorRate: MetricData;
  activeConnections: MetricData;
  queueDepth: MetricData;
  cpuUsage: MetricData;
  memoryUsage: MetricData;
  diskUsage: MetricData;
}

interface ProductionMetric {
  name: string;
  messagesProcessed: number;
  messagesPerSecond: number;
  avgLatency: number;
  errorRate: number;
  status: "healthy" | "warning" | "critical";
}

function MetricCard({
  title,
  value,
  unit,
  trend,
  icon: Icon,
  color = "blue",
}: {
  title: string;
  value: number;
  unit: string;
  trend: "up" | "down" | "stable";
  icon: React.ComponentType<{ className?: string }>;
  color?: "blue" | "green" | "yellow" | "red";
}) {
  const colorStyles = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    yellow: "bg-yellow-50 text-yellow-600",
    red: "bg-red-50 text-red-600",
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-gray-900">{value.toLocaleString()}</span>
            <span className="text-sm text-gray-500">{unit}</span>
          </div>
          <div className="mt-1 flex items-center gap-1">
            {trend === "up" ? (
              <ArrowUp className="h-3 w-3 text-green-500" />
            ) : trend === "down" ? (
              <ArrowDown className="h-3 w-3 text-red-500" />
            ) : (
              <span className="h-3 w-3 text-gray-400">—</span>
            )}
            <span className={`text-xs ${trend === "up" ? "text-green-600" : trend === "down" ? "text-red-600" : "text-gray-500"}`}>
              {trend === "stable" ? "No change" : `${trend === "up" ? "+" : "-"}5% from last hour`}
            </span>
          </div>
        </div>
        <div className={`rounded-lg p-2 ${colorStyles[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ value, max, color = "blue" }: { value: number; max: number; color?: string }) {
  const percentage = Math.min((value / max) * 100, 100);
  const colorClass = color === "green" ? "bg-green-500" : color === "yellow" ? "bg-yellow-500" : color === "red" ? "bg-red-500" : "bg-blue-500";
  
  return (
    <div className="h-2 w-full rounded-full bg-gray-200">
      <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${percentage}%` }} />
    </div>
  );
}

function SimpleChart({ data, height = 60 }: { data: number[]; height?: number }) {
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((value, i) => (
        <div
          key={i}
          className="flex-1 rounded-t bg-nhs-blue/70 transition-all hover:bg-nhs-blue"
          style={{ height: `${((value - min) / range) * 100}%`, minHeight: 2 }}
          title={`${value}`}
        />
      ))}
    </div>
  );
}

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null);
  const [productions, setProductions] = useState<MonitoringProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [throughputData, setThroughputData] = useState<MonitoringThroughputPoint[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const loadMetrics = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    
    try {
      const [metricsData, throughputResult, projectsData] = await Promise.all([
        getMonitoringMetrics(),
        getMonitoringThroughput(30),
        getMonitoringProjects(),
      ]);
      
      setMetrics(metricsData);
      setThroughputData(throughputResult.data || []);
      setProductions(projectsData.projects || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to load monitoring data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadMetrics();
    
    if (autoRefresh) {
      const interval = setInterval(() => loadMetrics(true), 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, loadMetrics]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy": return "bg-green-100 text-green-700";
      case "warning": return "bg-yellow-100 text-yellow-700";
      case "critical": return "bg-red-100 text-red-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Monitoring</h1>
          <p className="mt-1 text-sm text-gray-500">
            Real-time metrics and system performance
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-nhs-blue focus:ring-nhs-blue"
            />
            Auto-refresh
          </label>
          <button
            onClick={() => setLoading(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Throughput"
          value={metrics?.messages_per_second ?? 0}
          unit="msg/s"
          trend="stable"
          icon={Zap}
          color="blue"
        />
        <MetricCard
          title="Avg Latency"
          value={metrics?.avg_latency_ms ?? 0}
          unit="ms"
          trend="stable"
          icon={Clock}
          color="green"
        />
        <MetricCard
          title="Error Rate"
          value={metrics?.error_rate ?? 0}
          unit="%"
          trend="stable"
          icon={Activity}
          color={metrics?.error_rate && metrics.error_rate > 1 ? "red" : "green"}
        />
        <MetricCard
          title="Queue Depth"
          value={metrics?.queue_depth ?? 0}
          unit="msgs"
          trend="stable"
          icon={Database}
          color={metrics?.queue_depth && metrics.queue_depth > 500 ? "yellow" : "blue"}
        />
      </div>

      {/* Throughput Chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Message Throughput (Last 30 minutes)</h2>
          <span className="text-xs text-gray-500">Updated every 5 seconds</span>
        </div>
        {loading ? (
          <div className="h-16 animate-pulse rounded bg-gray-200" />
        ) : (
          <SimpleChart data={throughputData.map(d => d.total)} height={80} />
        )}
        <div className="mt-2 flex justify-between text-xs text-gray-400">
          <span>30 min ago</span>
          <span>Now</span>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Production Metrics */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-900">Production Performance</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="p-5">
                  <div className="h-4 w-32 animate-pulse rounded bg-gray-200" />
                  <div className="mt-3 h-2 w-full animate-pulse rounded bg-gray-200" />
                </div>
              ))
            ) : (
              productions.map((prod) => (
                <div key={prod.name} className="p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Server className="h-4 w-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">{prod.name}</span>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${getStatusColor(prod.status)}`}>
                      {prod.status}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-4 gap-4 text-center">
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{prod.messages_per_second}</p>
                      <p className="text-xs text-gray-500">msg/s</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{prod.avg_latency_ms}</p>
                      <p className="text-xs text-gray-500">ms avg</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{prod.error_rate}%</p>
                      <p className="text-xs text-gray-500">errors</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{(prod.messages_processed / 1000).toFixed(1)}k</p>
                      <p className="text-xs text-gray-500">total</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Message Statistics */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-900">Message Statistics (Last Hour)</h2>
          </div>
          <div className="space-y-5 p-5">
            {/* Messages Processed */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">Messages Processed</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.messages_last_hour ?? 0}</span>
              </div>
            </div>

            {/* Errors */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">Errors</span>
                </div>
                <span className="text-sm font-medium text-red-600">{metrics?.errors_last_hour ?? 0}</span>
              </div>
            </div>

            {/* P99 Latency */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">P99 Latency</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.p99_latency_ms ?? 0} ms</span>
              </div>
            </div>

            {/* Queue Depth */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">Queue Depth</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.queue_depth ?? 0}</span>
              </div>
            </div>

            {/* Last Updated */}
            <div className="pt-2 border-t border-gray-100">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Last updated</span>
                <span className="text-xs text-gray-500">{lastUpdate.toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Connection Status */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-5 py-4">
          <h2 className="text-sm font-semibold text-gray-900">External Connections</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Endpoint</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Latency</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Last Check</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              <tr>
                <td className="px-4 py-3 text-sm text-gray-900">PAS MLLP Server</td>
                <td className="px-4 py-3 text-sm text-gray-600">MLLP</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    Connected
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">12ms</td>
                <td className="px-4 py-3 text-sm text-gray-500">Just now</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-sm text-gray-900">Lab System API</td>
                <td className="px-4 py-3 text-sm text-gray-600">HTTP</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    Connected
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">45ms</td>
                <td className="px-4 py-3 text-sm text-gray-500">5 sec ago</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-sm text-gray-900">Radiology DICOM</td>
                <td className="px-4 py-3 text-sm text-gray-600">DICOM</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                    Degraded
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">234ms</td>
                <td className="px-4 py-3 text-sm text-gray-500">10 sec ago</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-sm text-gray-900">EMR FHIR Server</td>
                <td className="px-4 py-3 text-sm text-gray-600">FHIR</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    Connected
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">67ms</td>
                <td className="px-4 py-3 text-sm text-gray-500">3 sec ago</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
