/**
 * OpenLI HIE - Healthcare Integration Engine
 * Copyright (c) 2026 Lightweight Integration Ltd
 *
 * QuickStartPanel - Natural Language workflow templates for the Agent Console.
 * Displays role-appropriate, clickable NL prompt cards that pre-fill the
 * agent prompt input, making it effortless for NHS Trust developers to
 * describe integrations in plain English.
 */

"use client";

import {
  ArrowRightLeft,
  Cable,
  FlaskConical,
  HeartPulse,
  Layers,
  MessageSquareText,
  MonitorCheck,
  Network,
  RefreshCw,
  Shield,
  Stethoscope,
  Wrench,
} from "lucide-react";
import type { ComponentType } from "react";

// ── Agent-runner role identifiers ────────────────────────────────────────────
// These mirror the roles defined in agent-runner/app/roles.py
export type AgentRole =
  | "platform_admin"
  | "tenant_admin"
  | "developer"
  | "clinical_safety_officer"
  | "viewer";

/** Map Portal role_name (from auth DB) to agent-runner role key. */
export function mapPortalRoleToAgentRole(portalRoleName: string | null | undefined): AgentRole {
  if (!portalRoleName) return "viewer";
  const lower = portalRoleName.toLowerCase();
  if (lower.includes("super admin") || lower === "super administrator") return "platform_admin";
  if (lower.includes("tenant admin") || lower === "tenant administrator") return "tenant_admin";
  if (lower.includes("clinical safety") || lower === "clinical safety officer") return "clinical_safety_officer";
  if (lower.includes("developer") || lower.includes("integration developer")) return "developer";
  // Default authenticated user → developer
  if (lower === "user" || lower === "member") return "developer";
  return "viewer";
}

export const ROLE_DISPLAY: Record<AgentRole, { label: string; color: string; bg: string }> = {
  platform_admin:         { label: "Platform Admin",          color: "text-purple-700 dark:text-purple-300",  bg: "bg-purple-100 dark:bg-purple-900/40" },
  tenant_admin:           { label: "Tenant Admin",            color: "text-blue-700 dark:text-blue-300",      bg: "bg-blue-100 dark:bg-blue-900/40" },
  developer:              { label: "Integration Developer",   color: "text-green-700 dark:text-green-300",    bg: "bg-green-100 dark:bg-green-900/40" },
  clinical_safety_officer:{ label: "Clinical Safety Officer", color: "text-amber-700 dark:text-amber-300",    bg: "bg-amber-100 dark:bg-amber-900/40" },
  viewer:                 { label: "Viewer",                  color: "text-gray-600 dark:text-gray-400",      bg: "bg-gray-100 dark:bg-gray-800" },
};

// ── Workflow template definitions ────────────────────────────────────────────

interface WorkflowTemplate {
  id: string;
  title: string;
  description: string;
  prompt: string;
  icon: ComponentType<{ className?: string }>;
  /** Which roles can see this card */
  roles: AgentRole[];
  /** Category for grouping */
  category: "build" | "test" | "review" | "monitor" | "manage";
}

const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  // ── Build ──────────────────────────────────────────────────────────────────
  {
    id: "adt-integration",
    title: "Build ADT Integration",
    description: "Create an ADT A01/A02/A03/A08 patient administration route between clinical systems.",
    prompt:
      "Build an ADT integration that receives ADT^A01 (admit), ADT^A02 (transfer), ADT^A03 (discharge), and ADT^A08 (update) messages from our PAS system and routes them to the EPR and RIS. Use the custom.* namespace for all new classes.",
    icon: ArrowRightLeft,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "build",
  },
  {
    id: "orm-route",
    title: "Build ORM Order Route",
    description: "Create an HL7 ORM order message route for lab or radiology orders.",
    prompt:
      "Build an ORM^O01 order route that accepts orders from the EPR, validates the order structure, and forwards to the target departmental system. Include an ORR acknowledgement flow. Use the custom.* namespace.",
    icon: Cable,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "build",
  },
  {
    id: "outbound-operation",
    title: "Add New Outbound",
    description: "Add a new HL7v2 TCP outbound operation to send messages to an external system.",
    prompt:
      "Add a new HL7v2 TCP outbound operation to send messages to [SYSTEM_NAME] at [HOST:PORT]. Configure retry logic, acknowledgement handling, and connection pooling. Use the custom.* namespace for all classes.",
    icon: Network,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "build",
  },
  {
    id: "custom-process",
    title: "Create Custom Process",
    description: "Build a custom business process with message transformation and routing logic.",
    prompt:
      "Create a custom business process in the custom.* namespace that receives HL7 messages, transforms selected fields, applies routing rules based on message type and sending facility, and forwards to the appropriate target systems.",
    icon: Layers,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "build",
  },
  {
    id: "fhir-mapping",
    title: "Map HL7v2 to FHIR",
    description: "Create a transformation that converts HL7v2 messages to FHIR R4 resources.",
    prompt:
      "Create a mapping from HL7v2 ADT messages to FHIR R4 Patient and Encounter resources. Map PID segment fields to Patient resource, PV1 to Encounter, and NK1 to RelatedPerson. Use the custom.* namespace.",
    icon: RefreshCw,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "build",
  },

  // ── Test ───────────────────────────────────────────────────────────────────
  {
    id: "test-integration",
    title: "Run Integration Tests",
    description: "Execute integration tests against a project using standard HL7 test messages.",
    prompt:
      "Run integration tests for the current project. Send standard ADT test messages (A01, A02, A03, A08) through the route and verify that acknowledgements are received and messages are correctly transformed and routed.",
    icon: FlaskConical,
    roles: ["platform_admin", "tenant_admin", "developer", "clinical_safety_officer"],
    category: "test",
  },

  // ── Review / Compliance ────────────────────────────────────────────────────
  {
    id: "safety-review",
    title: "Run Safety Review",
    description: "Execute a DCB0129 clinical safety review of the project configuration.",
    prompt:
      "Run a DCB0129 clinical safety review of the current project. Check for hazards in message routing, data transformation accuracy, error handling completeness, and audit trail coverage. Produce a Clinical Safety Case Report summary.",
    icon: Stethoscope,
    roles: ["platform_admin", "tenant_admin", "clinical_safety_officer"],
    category: "review",
  },
  {
    id: "compliance-check",
    title: "Check NHS Compliance",
    description: "Verify the project meets NHS Data Security and Protection Toolkit requirements.",
    prompt:
      "Run an NHS compliance check on the current project. Verify compliance with the Data Security and Protection Toolkit (DSPT), check for PII exposure in logs, validate TLS configuration, verify audit logging coverage, and check data retention policies.",
    icon: Shield,
    roles: ["platform_admin", "tenant_admin", "developer", "clinical_safety_officer"],
    category: "review",
  },

  // ── Monitor / Debug ────────────────────────────────────────────────────────
  {
    id: "project-status",
    title: "View Project Status",
    description: "Get a comprehensive overview of project health, message throughput, and errors.",
    prompt:
      "Show me the current status of this project including: running state, message queue depths, recent error counts, connection health for all inbound and outbound operations, and any configuration warnings.",
    icon: MonitorCheck,
    roles: ["platform_admin", "tenant_admin", "developer", "clinical_safety_officer", "viewer"],
    category: "monitor",
  },
  {
    id: "diagnose-issues",
    title: "Diagnose Issues",
    description: "Investigate and diagnose message processing errors or connection failures.",
    prompt:
      "Diagnose the current issues with this project. Check for: failed messages in the error queue, connection timeouts, acknowledgement failures, transformation errors, and routing misconfigurations. Suggest fixes for any issues found.",
    icon: Wrench,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "monitor",
  },

  // ── Manage ─────────────────────────────────────────────────────────────────
  {
    id: "describe-integration",
    title: "Describe in Plain English",
    description: "Tell the agent what you need and let it build the entire integration for you.",
    prompt: "",
    icon: MessageSquareText,
    roles: ["platform_admin", "tenant_admin", "developer"],
    category: "manage",
  },
];

const CATEGORY_LABELS: Record<string, string> = {
  build: "Build Integrations",
  test: "Test",
  review: "Review & Compliance",
  monitor: "Monitor & Debug",
  manage: "Get Started",
};

const CATEGORY_ORDER = ["manage", "build", "test", "review", "monitor"];

// ── Component ────────────────────────────────────────────────────────────────

interface QuickStartPanelProps {
  agentRole: AgentRole;
  onSelectTemplate: (prompt: string) => void;
}

export default function QuickStartPanel({ agentRole, onSelectTemplate }: QuickStartPanelProps) {
  const visibleTemplates = WORKFLOW_TEMPLATES.filter((t) => t.roles.includes(agentRole));

  // Group by category
  const grouped = CATEGORY_ORDER.reduce<Record<string, WorkflowTemplate[]>>((acc, cat) => {
    const items = visibleTemplates.filter((t) => t.category === cat);
    if (items.length > 0) acc[cat] = items;
    return acc;
  }, {});

  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] py-4 px-2">
      {/* Hero heading */}
      <div className="text-center mb-6 max-w-2xl">
        <HeartPulse className="h-10 w-10 mx-auto text-nhs-blue dark:text-nhs-light-blue mb-3" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          What would you like to build?
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Describe your integration needs in plain English. Choose a template below or type your own instructions.
        </p>
      </div>

      {/* Template cards grouped by category */}
      <div className="w-full max-w-3xl space-y-5">
        {Object.entries(grouped).map(([category, templates]) => (
          <div key={category}>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2 px-1">
              {CATEGORY_LABELS[category] || category}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {templates.map((tmpl) => {
                const Icon = tmpl.icon;
                const isFreeForm = tmpl.id === "describe-integration";
                return (
                  <button
                    key={tmpl.id}
                    onClick={() => {
                      if (isFreeForm) {
                        // Focus the prompt input instead of prefilling
                        onSelectTemplate("");
                      } else {
                        onSelectTemplate(tmpl.prompt);
                      }
                    }}
                    className={`group text-left w-full rounded-lg border px-4 py-3 transition-all hover:shadow-md ${
                      isFreeForm
                        ? "border-nhs-blue/40 bg-nhs-blue/5 dark:bg-nhs-blue/10 hover:border-nhs-blue"
                        : "border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 hover:border-nhs-light-blue dark:hover:border-nhs-light-blue"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 rounded-md p-1.5 ${
                        isFreeForm
                          ? "bg-nhs-blue/10 text-nhs-blue dark:text-nhs-light-blue"
                          : "bg-gray-100 dark:bg-zinc-700 text-gray-500 dark:text-gray-400 group-hover:text-nhs-blue dark:group-hover:text-nhs-light-blue"
                      }`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm font-medium ${
                          isFreeForm
                            ? "text-nhs-blue dark:text-nhs-light-blue"
                            : "text-gray-900 dark:text-white"
                        }`}>
                          {tmpl.title}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                          {tmpl.description}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
