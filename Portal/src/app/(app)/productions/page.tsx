"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Play,
  Pause,
  Square,
  MoreVertical,
  Plus,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
} from "lucide-react";
import type { Production, ProductionState } from "@/types";
import { formatRelativeTime, formatNumber } from "@/lib/utils";

function StatusBadge({ status }: { status: ProductionState }) {
  const config: Record<ProductionState, { bg: string; text: string; icon: React.ReactNode }> = {
    running: {
      bg: "bg-green-100",
      text: "text-green-700",
      icon: <CheckCircle className="h-3 w-3" />,
    },
    stopped: {
      bg: "bg-gray-100",
      text: "text-gray-600",
      icon: <Square className="h-3 w-3" />,
    },
    paused: {
      bg: "bg-yellow-100",
      text: "text-yellow-700",
      icon: <Pause className="h-3 w-3" />,
    },
    error: {
      bg: "bg-red-100",
      text: "text-red-700",
      icon: <XCircle className="h-3 w-3" />,
    },
    starting: {
      bg: "bg-blue-100",
      text: "text-blue-700",
      icon: <Clock className="h-3 w-3" />,
    },
    stopping: {
      bg: "bg-orange-100",
      text: "text-orange-700",
      icon: <Clock className="h-3 w-3" />,
    },
  };

  const { bg, text, icon } = config[status] || config.stopped;

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${bg} ${text}`}>
      {icon}
      {status}
    </span>
  );
}

function ProductionCard({ production }: { production: Production }) {
  const itemCounts = {
    services: production.items.filter((i) => i.category === "service").length,
    processes: production.items.filter((i) => i.category === "process").length,
    operations: production.items.filter((i) => i.category === "operation").length,
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <Link
              href={`/productions/${encodeURIComponent(production.name)}`}
              className="text-lg font-semibold text-gray-900 hover:text-nhs-blue"
            >
              {production.name}
            </Link>
            <StatusBadge status={production.state || "stopped"} />
          </div>
          <p className="mt-1 text-sm text-gray-500 line-clamp-2">
            {production.description || "No description"}
          </p>
        </div>
        <button className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
          <MoreVertical className="h-5 w-5" />
        </button>
      </div>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-3 gap-4 border-t border-gray-100 pt-4">
        <div>
          <p className="text-xs text-gray-500">Services</p>
          <p className="text-lg font-semibold text-gray-900">{itemCounts.services}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Processes</p>
          <p className="text-lg font-semibold text-gray-900">{itemCounts.processes}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Operations</p>
          <p className="text-lg font-semibold text-gray-900">{itemCounts.operations}</p>
        </div>
      </div>

      {/* Metrics */}
      {production.metrics && (
        <div className="mt-4 flex items-center gap-4 border-t border-gray-100 pt-4 text-xs text-gray-500">
          <span>{formatNumber(production.metrics.totalMessagesProcessed)} messages</span>
          <span>•</span>
          <span>{production.metrics.itemsRunning} items running</span>
          {production.metrics.itemsError > 0 && (
            <>
              <span>•</span>
              <span className="text-red-600">{production.metrics.itemsError} errors</span>
            </>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-2 border-t border-gray-100 pt-4">
        {production.state === "running" ? (
          <>
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
              <Pause className="h-3.5 w-3.5" />
              Pause
            </button>
            <button className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
              <Square className="h-3.5 w-3.5" />
              Stop
            </button>
          </>
        ) : (
          <button className="inline-flex items-center gap-1.5 rounded-lg bg-nhs-blue px-3 py-1.5 text-xs font-medium text-white hover:bg-nhs-dark-blue">
            <Play className="h-3.5 w-3.5" />
            Start
          </button>
        )}
        <Link
          href={`/productions/${encodeURIComponent(production.name)}/edit`}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          Configure
        </Link>
      </div>
    </div>
  );
}

export default function ProductionsPage() {
  const [productions, setProductions] = useState<Production[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    // Mock data - will be replaced with API call
    const mockProductions: Production[] = [
      {
        name: "NHS-ADT-Integration",
        description: "ADT message integration for NHS acute trust - receives HL7v2 ADT messages via HTTP and MLLP, routes based on message type",
        enabled: true,
        settings: {
          actorPoolSize: 4,
          gracefulShutdownTimeout: 60,
          healthCheckInterval: 10,
          autoStart: true,
          testingEnabled: false,
        },
        items: [
          { id: "HTTP_ADT_Receiver", name: "HTTP ADT Receiver", type: "receiver.http", category: "service", enabled: true, settings: {} },
          { id: "File_ADT_Receiver", name: "File ADT Receiver", type: "receiver.file", category: "service", enabled: true, settings: {} },
          { id: "ADT_Router", name: "ADT Router", type: "processor.router", category: "process", enabled: true, settings: {} },
          { id: "ADT_Transformer", name: "ADT Transformer", type: "processor.transform", category: "process", enabled: true, settings: {} },
          { id: "PAS_MLLP_Sender", name: "PAS MLLP Sender", type: "sender.mllp", category: "operation", enabled: true, settings: {} },
          { id: "LIMS_MLLP_Sender", name: "LIMS MLLP Sender", type: "sender.mllp", category: "operation", enabled: true, settings: {} },
          { id: "ADT_Archive", name: "ADT Archive", type: "sender.file", category: "operation", enabled: true, settings: {} },
        ],
        connections: [],
        routingRules: [],
        version: 1,
        state: "running",
        metrics: {
          totalMessagesReceived: 125000,
          totalMessagesProcessed: 124850,
          totalMessagesFailed: 150,
          itemsRunning: 7,
          itemsError: 0,
          uptimeSeconds: 86400,
        },
      },
      {
        name: "Lab-Results-Feed",
        description: "Laboratory results integration - receives ORU messages from LIMS and distributes to EPR and GP systems",
        enabled: true,
        settings: {
          actorPoolSize: 2,
          gracefulShutdownTimeout: 30,
          healthCheckInterval: 10,
          autoStart: true,
          testingEnabled: false,
        },
        items: [
          { id: "LIMS_Receiver", name: "LIMS Receiver", type: "receiver.mllp", category: "service", enabled: true, settings: {} },
          { id: "Results_Router", name: "Results Router", type: "processor.router", category: "process", enabled: true, settings: {} },
          { id: "EPR_Sender", name: "EPR Sender", type: "sender.mllp", category: "operation", enabled: true, settings: {} },
          { id: "GP_Sender", name: "GP Sender", type: "sender.http", category: "operation", enabled: true, settings: {} },
        ],
        connections: [],
        routingRules: [],
        version: 1,
        state: "running",
        metrics: {
          totalMessagesReceived: 45000,
          totalMessagesProcessed: 44980,
          totalMessagesFailed: 20,
          itemsRunning: 4,
          itemsError: 0,
          uptimeSeconds: 72000,
        },
      },
      {
        name: "Radiology-Orders",
        description: "Radiology order management - receives ORM messages and routes to RIS",
        enabled: false,
        settings: {
          actorPoolSize: 2,
          gracefulShutdownTimeout: 30,
          healthCheckInterval: 10,
          autoStart: false,
          testingEnabled: true,
        },
        items: [
          { id: "Order_Receiver", name: "Order Receiver", type: "receiver.http", category: "service", enabled: true, settings: {} },
          { id: "Order_Validator", name: "Order Validator", type: "processor.transform", category: "process", enabled: true, settings: {} },
          { id: "RIS_Sender", name: "RIS Sender", type: "sender.mllp", category: "operation", enabled: true, settings: {} },
        ],
        connections: [],
        routingRules: [],
        version: 1,
        state: "stopped",
      },
    ];

    setTimeout(() => {
      setProductions(mockProductions);
      setLoading(false);
    }, 300);
  }, []);

  const filteredProductions = productions.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Productions</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your integration productions
          </p>
        </div>
        <Link
          href="/productions/new"
          className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue"
        >
          <Plus className="h-4 w-4" />
          New Production
        </Link>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search productions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10 w-full rounded-lg border border-gray-200 bg-white pl-10 pr-4 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
          />
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          <Filter className="h-4 w-4" />
          Filter
        </button>
      </div>

      {/* Productions Grid */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="animate-pulse space-y-4">
                <div className="h-6 w-3/4 rounded bg-gray-200" />
                <div className="h-4 w-full rounded bg-gray-200" />
                <div className="grid grid-cols-3 gap-4 pt-4">
                  <div className="h-12 rounded bg-gray-200" />
                  <div className="h-12 rounded bg-gray-200" />
                  <div className="h-12 rounded bg-gray-200" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : filteredProductions.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredProductions.map((production) => (
            <ProductionCard key={production.name} production={production} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No productions found</h3>
          <p className="mt-2 text-sm text-gray-500">
            {searchQuery
              ? "Try adjusting your search query"
              : "Get started by creating your first production"}
          </p>
          {!searchQuery && (
            <Link
              href="/productions/new"
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue"
            >
              <Plus className="h-4 w-4" />
              Create Production
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
