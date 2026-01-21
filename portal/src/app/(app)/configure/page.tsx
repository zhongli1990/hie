"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ChevronRight,
  Edit,
  FileCode,
  GitBranch,
  Plus,
  Save,
  Server,
  Settings,
  Trash2,
} from "lucide-react";

interface RouteConfig {
  id: string;
  name: string;
  description: string;
  source: string;
  destination: string;
  transformers: string[];
  enabled: boolean;
  productionName: string;
}

interface ItemConfig {
  id: string;
  name: string;
  type: "receiver" | "sender" | "transformer";
  className: string;
  enabled: boolean;
  config: Record<string, string | number | boolean>;
}

export default function ConfigurePage() {
  const [routes, setRoutes] = useState<RouteConfig[]>([]);
  const [items, setItems] = useState<ItemConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"routes" | "items">("routes");
  const [selectedRoute, setSelectedRoute] = useState<RouteConfig | null>(null);

  useEffect(() => {
    const mockRoutes: RouteConfig[] = [
      {
        id: "http_to_mllp",
        name: "HTTP to MLLP",
        description: "Route HL7 messages from HTTP receiver to MLLP sender",
        source: "HTTP_ADT_Receiver",
        destination: "PAS_MLLP_Sender",
        transformers: ["HL7_Validator", "Message_Logger"],
        enabled: true,
        productionName: "NHS-ADT-Integration",
      },
      {
        id: "file_to_http",
        name: "File to HTTP",
        description: "Process lab results from file system to HTTP endpoint",
        source: "Lab_File_Receiver",
        destination: "EMR_HTTP_Sender",
        transformers: ["HL7_Parser", "Result_Transformer"],
        enabled: true,
        productionName: "Lab-Results-Feed",
      },
      {
        id: "mllp_to_fhir",
        name: "MLLP to FHIR",
        description: "Convert HL7v2 to FHIR and send to FHIR server",
        source: "MLLP_Receiver",
        destination: "FHIR_HTTP_Sender",
        transformers: ["HL7_to_FHIR_Transformer"],
        enabled: false,
        productionName: "FHIR-Integration",
      },
    ];

    const mockItems: ItemConfig[] = [
      { id: "http_adt_receiver", name: "HTTP_ADT_Receiver", type: "receiver", className: "hie.items.receivers.HTTPReceiver", enabled: true, config: { host: "0.0.0.0", port: 8080, path: "/hl7" } },
      { id: "pas_mllp_sender", name: "PAS_MLLP_Sender", type: "sender", className: "hie.items.senders.MLLPSender", enabled: true, config: { host: "mllp-echo", port: 2575, timeout: 30000 } },
      { id: "hl7_validator", name: "HL7_Validator", type: "transformer", className: "hie.items.transformers.HL7Validator", enabled: true, config: { strict: true, version: "2.5" } },
      { id: "message_logger", name: "Message_Logger", type: "transformer", className: "hie.items.transformers.MessageLogger", enabled: true, config: { logLevel: "INFO", includePayload: false } },
      { id: "lab_file_receiver", name: "Lab_File_Receiver", type: "receiver", className: "hie.items.receivers.FileReceiver", enabled: true, config: { path: "/data/inbound", pattern: "*.hl7" } },
      { id: "emr_http_sender", name: "EMR_HTTP_Sender", type: "sender", className: "hie.items.senders.HTTPSender", enabled: true, config: { url: "https://emr.nhs.uk/api/results", method: "POST" } },
    ];

    setTimeout(() => {
      setRoutes(mockRoutes);
      setItems(mockItems);
      setLoading(false);
    }, 500);
  }, []);

  const getTypeColor = (type: string) => {
    switch (type) {
      case "receiver": return "bg-green-100 text-green-700";
      case "sender": return "bg-blue-100 text-blue-700";
      case "transformer": return "bg-purple-100 text-purple-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Configure</h1>
          <p className="mt-1 text-sm text-gray-500">Manage routes, items, and production configuration</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            <FileCode className="h-4 w-4" />
            View YAML
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue">
            <Plus className="h-4 w-4" />
            New Route
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          <button
            onClick={() => setActiveTab("routes")}
            className={`border-b-2 pb-3 text-sm font-medium transition-colors ${
              activeTab === "routes"
                ? "border-nhs-blue text-nhs-blue"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4" />
              Routes ({routes.length})
            </div>
          </button>
          <button
            onClick={() => setActiveTab("items")}
            className={`border-b-2 pb-3 text-sm font-medium transition-colors ${
              activeTab === "items"
                ? "border-nhs-blue text-nhs-blue"
                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
            }`}
          >
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4" />
              Items ({items.length})
            </div>
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === "routes" && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Routes List */}
          <div className="space-y-4">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="h-5 w-40 animate-pulse rounded bg-gray-200" />
                  <div className="mt-3 h-4 w-full animate-pulse rounded bg-gray-200" />
                </div>
              ))
            ) : (
              routes.map((route) => (
                <div
                  key={route.id}
                  onClick={() => setSelectedRoute(route)}
                  className={`cursor-pointer rounded-xl border bg-white p-5 shadow-sm transition-all hover:shadow-md ${
                    selectedRoute?.id === route.id ? "border-nhs-blue ring-1 ring-nhs-blue" : "border-gray-200"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-900">{route.name}</h3>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${route.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                          {route.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">{route.description}</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-xs">
                    <span className="rounded bg-green-50 px-2 py-1 text-green-700">{route.source}</span>
                    <ArrowRight className="h-3 w-3 text-gray-400" />
                    {route.transformers.length > 0 && (
                      <>
                        <span className="rounded bg-purple-50 px-2 py-1 text-purple-700">
                          {route.transformers.length} transformer{route.transformers.length > 1 ? "s" : ""}
                        </span>
                        <ArrowRight className="h-3 w-3 text-gray-400" />
                      </>
                    )}
                    <span className="rounded bg-blue-50 px-2 py-1 text-blue-700">{route.destination}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Route Details */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            {selectedRoute ? (
              <div>
                <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                  <h2 className="text-lg font-semibold text-gray-900">{selectedRoute.name}</h2>
                  <div className="flex items-center gap-2">
                    <button className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                      <Edit className="h-4 w-4" />
                    </button>
                    <button className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="space-y-6 p-6">
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">Description</h3>
                    <p className="mt-1 text-sm text-gray-900">{selectedRoute.description}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">Production</h3>
                    <p className="mt-1 text-sm text-gray-900">{selectedRoute.productionName}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">Route ID</h3>
                    <p className="mt-1 font-mono text-sm text-gray-900">{selectedRoute.id}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">Flow</h3>
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
                          <span className="text-xs font-bold text-green-700">1</span>
                        </div>
                        <div className="flex-1 rounded-lg border border-gray-200 px-3 py-2">
                          <p className="text-xs text-gray-500">Source</p>
                          <p className="text-sm font-medium text-gray-900">{selectedRoute.source}</p>
                        </div>
                      </div>
                      {selectedRoute.transformers.map((t, i) => (
                        <div key={t} className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-purple-100">
                            <span className="text-xs font-bold text-purple-700">{i + 2}</span>
                          </div>
                          <div className="flex-1 rounded-lg border border-gray-200 px-3 py-2">
                            <p className="text-xs text-gray-500">Transformer</p>
                            <p className="text-sm font-medium text-gray-900">{t}</p>
                          </div>
                        </div>
                      ))}
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
                          <span className="text-xs font-bold text-blue-700">{selectedRoute.transformers.length + 2}</span>
                        </div>
                        <div className="flex-1 rounded-lg border border-gray-200 px-3 py-2">
                          <p className="text-xs text-gray-500">Destination</p>
                          <p className="text-sm font-medium text-gray-900">{selectedRoute.destination}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 pt-4">
                    <button className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue">
                      <Save className="h-4 w-4" />
                      Save Changes
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex h-96 flex-col items-center justify-center text-center">
                <GitBranch className="h-12 w-12 text-gray-300" />
                <p className="mt-4 text-sm font-medium text-gray-900">Select a route</p>
                <p className="mt-1 text-xs text-gray-500">Click on a route to view and edit its configuration</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "items" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                Receivers ({items.filter((i) => i.type === "receiver").length})
              </span>
              <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
                Senders ({items.filter((i) => i.type === "sender").length})
              </span>
              <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-700">
                Transformers ({items.filter((i) => i.type === "transformer").length})
              </span>
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue">
              <Plus className="h-4 w-4" />
              New Item
            </button>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Class</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3"><div className="h-4 w-32 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-5 w-20 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-4 w-48 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-5 w-16 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-4 w-16 animate-pulse rounded bg-gray-200" /></td>
                    </tr>
                  ))
                ) : (
                  items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-gray-900">{item.name}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${getTypeColor(item.type)}`}>
                          {item.type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <code className="text-xs text-gray-600">{item.className}</code>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${item.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                          {item.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                            <Settings className="h-4 w-4" />
                          </button>
                          <button className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                            <Edit className="h-4 w-4" />
                          </button>
                          <button className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
