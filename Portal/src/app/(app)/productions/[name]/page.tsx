"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Play,
  Pause,
  Square,
  Settings,
  RefreshCw,
  Download,
  Upload,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
} from "lucide-react";
import type { Production, Item, ItemState } from "@/types";
import { formatNumber, formatDuration } from "@/lib/utils";

function ItemStatusIcon({ state }: { state?: ItemState }) {
  if (state === "running") return <CheckCircle className="h-4 w-4 text-green-500" />;
  if (state === "error") return <XCircle className="h-4 w-4 text-red-500" />;
  if (state === "paused") return <Pause className="h-4 w-4 text-yellow-500" />;
  return <Square className="h-4 w-4 text-gray-400" />;
}

function ItemCard({ item }: { item: Item }) {
  const categoryColors = {
    service: "border-l-green-500 bg-green-50",
    process: "border-l-blue-500 bg-blue-50",
    operation: "border-l-purple-500 bg-purple-50",
  };

  return (
    <div
      className={`rounded-lg border border-gray-200 border-l-4 p-4 ${categoryColors[item.category]}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <ItemStatusIcon state={item.state} />
          <div>
            <h4 className="font-medium text-gray-900">{item.name || item.id}</h4>
            <p className="text-xs text-gray-500">{item.type}</p>
          </div>
        </div>
        <button className="rounded p-1 text-gray-400 hover:bg-white hover:text-gray-600">
          <Settings className="h-4 w-4" />
        </button>
      </div>
      {item.metrics && (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-gray-500">Processed:</span>{" "}
            <span className="font-medium">{formatNumber(item.metrics.messagesProcessed)}</span>
          </div>
          <div>
            <span className="text-gray-500">Queue:</span>{" "}
            <span className="font-medium">{item.metrics.messagesInQueue}</span>
          </div>
          <div>
            <span className="text-gray-500">Latency:</span>{" "}
            <span className="font-medium">{item.metrics.avgLatencyMs.toFixed(1)}ms</span>
          </div>
          <div>
            <span className="text-gray-500">Errors:</span>{" "}
            <span className={`font-medium ${item.metrics.messagesFailed > 0 ? "text-red-600" : ""}`}>
              {item.metrics.messagesFailed}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProductionDetailPage() {
  const params = useParams();
  const productionName = decodeURIComponent(params.name as string);
  const [production, setProduction] = useState<Production | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data - will be replaced with API call
    const mockProduction: Production = {
      name: productionName,
      description: "ADT message integration for NHS acute trust",
      enabled: true,
      settings: {
        actorPoolSize: 4,
        gracefulShutdownTimeout: 60,
        healthCheckInterval: 10,
        autoStart: true,
        testingEnabled: false,
      },
      items: [
        {
          id: "HTTP_ADT_Receiver",
          name: "HTTP ADT Receiver",
          type: "receiver.http",
          category: "service",
          enabled: true,
          settings: { port: 8080, path: "/api/hl7/adt" },
          state: "running",
          metrics: {
            messagesReceived: 45000,
            messagesProcessed: 45000,
            messagesFailed: 0,
            messagesInQueue: 12,
            avgLatencyMs: 2.3,
          },
        },
        {
          id: "File_ADT_Receiver",
          name: "File ADT Receiver",
          type: "receiver.file",
          category: "service",
          enabled: true,
          settings: { directory: "/data/inbound/adt" },
          state: "running",
          metrics: {
            messagesReceived: 5000,
            messagesProcessed: 5000,
            messagesFailed: 0,
            messagesInQueue: 0,
            avgLatencyMs: 15.2,
          },
        },
        {
          id: "ADT_Router",
          name: "ADT Message Router",
          type: "processor.router",
          category: "process",
          enabled: true,
          settings: {},
          state: "running",
          metrics: {
            messagesReceived: 50000,
            messagesProcessed: 50000,
            messagesFailed: 0,
            messagesInQueue: 5,
            avgLatencyMs: 0.8,
          },
        },
        {
          id: "ADT_Transformer",
          name: "ADT Transformer",
          type: "processor.transform",
          category: "process",
          enabled: true,
          settings: {},
          state: "running",
          metrics: {
            messagesReceived: 35000,
            messagesProcessed: 34950,
            messagesFailed: 50,
            messagesInQueue: 8,
            avgLatencyMs: 5.2,
          },
        },
        {
          id: "PAS_MLLP_Sender",
          name: "PAS MLLP Sender",
          type: "sender.mllp",
          category: "operation",
          enabled: true,
          settings: { host: "pas.nhs.local", port: 2575 },
          state: "running",
          metrics: {
            messagesReceived: 34950,
            messagesProcessed: 34900,
            messagesFailed: 50,
            messagesInQueue: 15,
            avgLatencyMs: 45.3,
          },
        },
        {
          id: "LIMS_MLLP_Sender",
          name: "LIMS MLLP Sender",
          type: "sender.mllp",
          category: "operation",
          enabled: true,
          settings: { host: "lims.nhs.local", port: 2576 },
          state: "running",
          metrics: {
            messagesReceived: 15000,
            messagesProcessed: 14980,
            messagesFailed: 20,
            messagesInQueue: 3,
            avgLatencyMs: 38.7,
          },
        },
        {
          id: "ADT_Archive",
          name: "ADT Archive",
          type: "sender.file",
          category: "operation",
          enabled: true,
          settings: { directory: "/data/archive/adt" },
          state: "running",
          metrics: {
            messagesReceived: 50000,
            messagesProcessed: 50000,
            messagesFailed: 0,
            messagesInQueue: 2,
            avgLatencyMs: 8.1,
          },
        },
      ],
      connections: [],
      routingRules: [],
      version: 1,
      state: "running",
      metrics: {
        totalMessagesReceived: 50000,
        totalMessagesProcessed: 49850,
        totalMessagesFailed: 150,
        itemsRunning: 7,
        itemsError: 0,
        uptimeSeconds: 86400,
      },
    };

    setTimeout(() => {
      setProduction(mockProduction);
      setLoading(false);
    }, 300);
  }, [productionName]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 animate-pulse rounded bg-gray-200" />
        <div className="h-32 animate-pulse rounded-xl bg-gray-200" />
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg bg-gray-200" />
          ))}
        </div>
      </div>
    );
  }

  if (!production) {
    return (
      <div className="text-center">
        <AlertTriangle className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900">Production not found</h3>
        <Link href="/productions" className="mt-2 text-nhs-blue hover:underline">
          Back to productions
        </Link>
      </div>
    );
  }

  const services = production.items.filter((i) => i.category === "service");
  const processes = production.items.filter((i) => i.category === "process");
  const operations = production.items.filter((i) => i.category === "operation");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/productions"
          className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-gray-900">{production.name}</h1>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                production.state === "running"
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {production.state === "running" ? (
                <CheckCircle className="h-3 w-3" />
              ) : (
                <Square className="h-3 w-3" />
              )}
              {production.state}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">{production.description}</p>
        </div>
        <div className="flex items-center gap-2">
          {production.state === "running" ? (
            <>
              <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                <Pause className="h-4 w-4" />
                Pause
              </button>
              <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                <Square className="h-4 w-4" />
                Stop
              </button>
            </>
          ) : (
            <button className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue">
              <Play className="h-4 w-4" />
              Start
            </button>
          )}
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <Link
            href={`/productions/${encodeURIComponent(production.name)}/edit`}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Settings className="h-4 w-4" />
            Configure
          </Link>
        </div>
      </div>

      {/* Metrics Overview */}
      {production.metrics && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Messages Received</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {formatNumber(production.metrics.totalMessagesReceived)}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Messages Processed</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {formatNumber(production.metrics.totalMessagesProcessed)}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Messages Failed</p>
            <p className={`mt-1 text-2xl font-bold ${production.metrics.totalMessagesFailed > 0 ? "text-red-600" : "text-gray-900"}`}>
              {formatNumber(production.metrics.totalMessagesFailed)}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Items Running</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {production.metrics.itemsRunning} / {production.items.length}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">Uptime</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {formatDuration(production.metrics.uptimeSeconds)}
            </p>
          </div>
        </div>
      )}

      {/* Items by Category */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Services */}
        <div>
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <span className="h-3 w-3 rounded-full bg-green-500" />
            Services ({services.length})
          </h3>
          <div className="space-y-3">
            {services.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Processes */}
        <div>
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <span className="h-3 w-3 rounded-full bg-blue-500" />
            Processes ({processes.length})
          </h3>
          <div className="space-y-3">
            {processes.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Operations */}
        <div>
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <span className="h-3 w-3 rounded-full bg-purple-500" />
            Operations ({operations.length})
          </h3>
          <div className="space-y-3">
            {operations.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4 border-t border-gray-200 pt-6">
        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          <Download className="h-4 w-4" />
          Export Configuration
        </button>
        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          <Upload className="h-4 w-4" />
          Import Configuration
        </button>
      </div>
    </div>
  );
}
