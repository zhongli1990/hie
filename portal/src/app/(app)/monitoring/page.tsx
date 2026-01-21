"use client";

import { useEffect, useState } from "react";
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
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [productions, setProductions] = useState<ProductionMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [throughputHistory, setThroughputHistory] = useState<number[]>([]);

  useEffect(() => {
    const loadMetrics = () => {
      // Mock data - will be replaced with API calls
      const mockMetrics: SystemMetrics = {
        messagesPerSecond: { current: 127, previous: 121, unit: "msg/s", trend: "up" },
        avgLatency: { current: 45, previous: 52, unit: "ms", trend: "down" },
        errorRate: { current: 0.02, previous: 0.03, unit: "%", trend: "down" },
        activeConnections: { current: 24, previous: 22, unit: "", trend: "up" },
        queueDepth: { current: 156, previous: 189, unit: "msgs", trend: "down" },
        cpuUsage: { current: 34, previous: 31, unit: "%", trend: "up" },
        memoryUsage: { current: 62, previous: 58, unit: "%", trend: "up" },
        diskUsage: { current: 45, previous: 44, unit: "%", trend: "stable" },
      };

      const mockProductions: ProductionMetric[] = [
        { name: "NHS-ADT-Integration", messagesProcessed: 45892, messagesPerSecond: 85, avgLatency: 42, errorRate: 0.01, status: "healthy" },
        { name: "Lab-Results-Feed", messagesProcessed: 12456, messagesPerSecond: 32, avgLatency: 67, errorRate: 0.05, status: "warning" },
        { name: "Radiology-Orders", messagesProcessed: 8234, messagesPerSecond: 10, avgLatency: 89, errorRate: 0.02, status: "healthy" },
      ];

      // Generate random throughput history
      const history = Array.from({ length: 30 }, () => Math.floor(Math.random() * 50) + 100);

      setMetrics(mockMetrics);
      setProductions(mockProductions);
      setThroughputHistory(history);
      setLoading(false);
    };

    loadMetrics();

    if (autoRefresh) {
      const interval = setInterval(loadMetrics, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

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
          value={metrics?.messagesPerSecond.current ?? 0}
          unit="msg/s"
          trend={metrics?.messagesPerSecond.trend ?? "stable"}
          icon={Zap}
          color="blue"
        />
        <MetricCard
          title="Avg Latency"
          value={metrics?.avgLatency.current ?? 0}
          unit="ms"
          trend={metrics?.avgLatency.trend ?? "stable"}
          icon={Clock}
          color="green"
        />
        <MetricCard
          title="Error Rate"
          value={metrics?.errorRate.current ?? 0}
          unit="%"
          trend={metrics?.errorRate.trend ?? "stable"}
          icon={Activity}
          color={metrics?.errorRate.current && metrics.errorRate.current > 1 ? "red" : "green"}
        />
        <MetricCard
          title="Queue Depth"
          value={metrics?.queueDepth.current ?? 0}
          unit="msgs"
          trend={metrics?.queueDepth.trend ?? "stable"}
          icon={Database}
          color={metrics?.queueDepth.current && metrics.queueDepth.current > 500 ? "yellow" : "blue"}
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
          <SimpleChart data={throughputHistory} height={80} />
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
                      <p className="text-lg font-semibold text-gray-900">{prod.messagesPerSecond}</p>
                      <p className="text-xs text-gray-500">msg/s</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{prod.avgLatency}</p>
                      <p className="text-xs text-gray-500">ms avg</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{prod.errorRate}%</p>
                      <p className="text-xs text-gray-500">errors</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">{(prod.messagesProcessed / 1000).toFixed(1)}k</p>
                      <p className="text-xs text-gray-500">total</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* System Resources */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-900">System Resources</h2>
          </div>
          <div className="space-y-5 p-5">
            {/* CPU */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">CPU Usage</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.cpuUsage.current ?? 0}%</span>
              </div>
              <div className="mt-2">
                <ProgressBar
                  value={metrics?.cpuUsage.current ?? 0}
                  max={100}
                  color={metrics?.cpuUsage.current && metrics.cpuUsage.current > 80 ? "red" : metrics?.cpuUsage.current && metrics.cpuUsage.current > 60 ? "yellow" : "green"}
                />
              </div>
            </div>

            {/* Memory */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">Memory Usage</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.memoryUsage.current ?? 0}%</span>
              </div>
              <div className="mt-2">
                <ProgressBar
                  value={metrics?.memoryUsage.current ?? 0}
                  max={100}
                  color={metrics?.memoryUsage.current && metrics.memoryUsage.current > 80 ? "red" : metrics?.memoryUsage.current && metrics.memoryUsage.current > 60 ? "yellow" : "green"}
                />
              </div>
            </div>

            {/* Disk */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <HardDrive className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">Disk Usage</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.diskUsage.current ?? 0}%</span>
              </div>
              <div className="mt-2">
                <ProgressBar
                  value={metrics?.diskUsage.current ?? 0}
                  max={100}
                  color={metrics?.diskUsage.current && metrics.diskUsage.current > 80 ? "red" : metrics?.diskUsage.current && metrics.diskUsage.current > 60 ? "yellow" : "blue"}
                />
              </div>
            </div>

            {/* Connections */}
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wifi className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">Active Connections</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{metrics?.activeConnections.current ?? 0}</span>
              </div>
              <div className="mt-2">
                <ProgressBar value={metrics?.activeConnections.current ?? 0} max={100} color="blue" />
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
