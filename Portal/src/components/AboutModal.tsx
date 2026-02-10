"use client";

import { useState } from "react";

interface VersionHistory {
  version: string;
  date: string;
  features: string[];
}

const VERSION = "1.6.0";
const BUILD_DATE = "Feb 11, 2026";
const PLATFORM_NAME = "OpenLI HIE";
const PRODUCT_NAME = "OpenLI Healthcare Integration Engine";

const versionHistory: VersionHistory[] = [
  {
    version: "1.6.0",
    date: "Feb 11, 2026",
    features: [
      "Rebranded to OpenLI HIE - OpenLI Healthcare Integration Engine",
      "GenAI Agent Console for natural language route configuration",
      "Chat interface for conversational HIE integration building",
      "Integration Skills management (HL7, FHIR, routing, transforms)",
      "Hooks configuration (security, audit, NHS compliance, clinical safety)",
      "Dual license (AGPL-3.0 community + Commercial) by Lightweight Integration Ltd",
      "Favicon and metadata with OpenLI branding",
      "Sidebar with GenAI and Admin sections",
    ],
  },
  {
    version: "1.5.1",
    date: "Feb 10, 2026",
    features: [
      "Portal UI uplift with About modal and version history",
      "Theme mode switcher (light/dark/system)",
      "Collapsible sidebar with persistent state",
      "Improved mobile responsiveness",
      "Settings menu with theme controls",
    ],
  },
  {
    version: "1.5.0",
    date: "Feb 10, 2026",
    features: [
      "Phase 4 Meta-Instantiation: ANY Python class from configuration",
      "Protocol-Agnostic Message Envelope (HL7, FHIR, JSON, XML, custom)",
      "Enhanced ClassRegistry with automatic import fallback",
      "NHS Trust Demo with 8-item production configuration",
      "Security boundaries with ImportPolicy (whitelist/blacklist)",
      "Schema-aware messaging with dynamic parsing",
      "Validation state tracking with error lists",
      "100% backward compatible with Phase 3",
    ],
  },
  {
    version: "1.4.0",
    date: "Feb 9, 2026",
    features: [
      "Multiprocess execution (true OS processes, GIL bypass)",
      "Thread pool execution for blocking I/O",
      "Priority queues (FIFO, Priority, LIFO, Unordered)",
      "Auto-restart policies (Never, On Failure, Always)",
      "Messaging patterns (Async/Sync Reliable, Concurrent)",
      "Message-level hooks (before/after/error)",
      "Portal UI configuration for all Phase 2 settings",
      "Hot reload configuration without restart",
    ],
  },
  {
    version: "1.3.0",
    date: "Feb 9, 2026",
    features: [
      "Production configuration management (JSON/YAML)",
      "Manager API deployment endpoints",
      "Portal UI for production deployment",
      "Workspace and Project management",
      "Item CRUD operations via API",
      "Health checks and metrics",
    ],
  },
  {
    version: "1.2.0",
    date: "Feb 9, 2026",
    features: [
      "HL7 v2.x message processing",
      "TCP/HTTP/File protocol support",
      "Basic routing engine",
      "Message persistence (WAL)",
      "Initial Portal UI",
    ],
  },
  {
    version: "1.1.0",
    date: "Feb 8, 2026",
    features: [
      "Core message model (envelope/payload separation)",
      "Business Service/Process/Operation hierarchy",
      "Adapter framework (Inbound/Outbound)",
      "Configuration system (ItemConfig)",
    ],
  },
  {
    version: "1.0.0",
    date: "Feb 7, 2026",
    features: [
      "Initial release",
      "IRIS-compatible LI Engine architecture",
      "ClassRegistry for dynamic class loading",
      "Basic host lifecycle management",
      "Docker deployment support",
    ],
  },
];

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  const [activeTab, setActiveTab] = useState<"about" | "history">("about");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-zinc-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-200 bg-gradient-to-r from-blue-500 via-cyan-500 to-teal-500 px-6 py-4 dark:border-zinc-700">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20 backdrop-blur">
              <svg className="h-6 w-6 text-white" viewBox="0 0 100 100" fill="none">
                <path d="M50 20 L70 35 L70 65 L50 80 L30 65 L30 35 Z" stroke="currentColor" strokeWidth="4" fill="none"/>
                <circle cx="50" cy="50" r="12" stroke="currentColor" strokeWidth="3" fill="currentColor"/>
                <line x1="50" y1="20" x2="50" y2="38" stroke="currentColor" strokeWidth="3"/>
                <line x1="50" y1="62" x2="50" y2="80" stroke="currentColor" strokeWidth="3"/>
                <line x1="30" y1="35" x2="41" y2="44" stroke="currentColor" strokeWidth="3"/>
                <line x1="59" y1="56" x2="70" y2="65" stroke="currentColor" strokeWidth="3"/>
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">{PRODUCT_NAME}</h2>
              <p className="text-sm text-white/80">GenAI-Powered NHS Healthcare Integration Platform</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-white/80 hover:bg-white/20 hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-200 dark:border-zinc-700">
          <button
            onClick={() => setActiveTab("about")}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === "about"
                ? "border-b-2 border-cyan-500 text-cyan-600 dark:text-cyan-400"
                : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            About
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === "history"
                ? "border-b-2 border-cyan-500 text-cyan-600 dark:text-cyan-400"
                : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            Version History
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto p-6">
          {activeTab === "about" ? (
            <div className="space-y-6">
              {/* Version Info */}
              <div className="rounded-lg bg-gradient-to-r from-blue-50 to-cyan-50 p-4 dark:from-blue-900/20 dark:to-cyan-900/20">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Current Version</p>
                    <p className="text-2xl font-bold text-zinc-900 dark:text-white">v{VERSION}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">Build Date</p>
                    <p className="text-lg font-semibold text-zinc-700 dark:text-zinc-300">{BUILD_DATE}</p>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div>
                <h3 className="mb-2 font-semibold text-zinc-900 dark:text-white">Description</h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  OpenLI HIE (Healthcare Integration Engine) is a production-ready NHS healthcare integration platform
                  designed to replace InterSystems IRIS, Orion Rhapsody, and Mirth Connect. Built with enterprise-grade
                  architecture, it provides universal meta-instantiation, protocol-agnostic messaging, GenAI-powered
                  route configuration, and mission-critical reliability for NHS acute trusts.
                </p>
              </div>

              {/* Key Features */}
              <div>
                <h3 className="mb-2 font-semibold text-zinc-900 dark:text-white">Key Features</h3>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    "GenAI Agent Console",
                    "Natural Language Routes",
                    "Universal Meta-Instantiation",
                    "Protocol-Agnostic Messaging",
                    "HL7 v2.x Processing",
                    "FHIR R4 Support",
                    "Multiprocess Execution",
                    "Integration Skills",
                    "NHS Compliance Hooks",
                    "10K-50K msg/sec",
                  ].map((feature) => (
                    <div
                      key={feature}
                      className="flex items-center gap-2 rounded-md bg-zinc-100 px-3 py-2 text-sm dark:bg-zinc-700"
                    >
                      <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-zinc-700 dark:text-zinc-300">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tech Stack */}
              <div>
                <h3 className="mb-2 font-semibold text-zinc-900 dark:text-white">Technology Stack</h3>
                <div className="flex flex-wrap gap-2">
                  {[
                    "Python 3.11+",
                    "Next.js 14",
                    "React 18",
                    "FastAPI",
                    "PostgreSQL",
                    "Docker",
                    "Redis",
                    "etcd",
                    "TailwindCSS",
                  ].map((tech) => (
                    <span
                      key={tech}
                      className="rounded-full bg-cyan-100 px-3 py-1 text-xs font-medium text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>

              {/* Capabilities */}
              <div>
                <h3 className="mb-2 font-semibold text-zinc-900 dark:text-white">Production Capabilities</h3>
                <div className="space-y-2">
                  <div className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500" />
                    <span><strong className="text-zinc-900 dark:text-white">Current (Phase 4):</strong> 10,000-50,000 msg/sec (single-node), NHS Trust deployments</span>
                  </div>
                  <div className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
                    <span><strong className="text-zinc-900 dark:text-white">Phase 5 (Q1-Q2 2027):</strong> 100K msg/sec, NHS Spine, FHIR R4, distributed tracing</span>
                  </div>
                  <div className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-purple-500" />
                    <span><strong className="text-zinc-900 dark:text-white">Phase 6 (Q3-Q4 2027):</strong> 1M+ msg/sec, 1B+ msg/day, Kafka sharding, multi-region</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {versionHistory.map((release) => (
                <div
                  key={release.version}
                  className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="rounded-md bg-cyan-100 px-2 py-1 text-sm font-bold text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300">
                      v{release.version}
                    </span>
                    <span className="text-sm text-zinc-500 dark:text-zinc-400">{release.date}</span>
                  </div>
                  <ul className="space-y-1">
                    {release.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                        <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-cyan-400" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-zinc-200 bg-zinc-50 px-6 py-3 dark:border-zinc-700 dark:bg-zinc-800/50">
          <p className="text-center text-xs text-zinc-500 dark:text-zinc-400">
            © 2026 Lightweight Integration Ltd. OpenLI HIE - Enterprise NHS Integration Platform. Licensed under AGPL-3.0 or Commercial.
          </p>
        </div>
      </div>
    </div>
  );
}

export { VERSION, BUILD_DATE };
