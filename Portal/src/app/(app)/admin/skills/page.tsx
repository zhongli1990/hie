/**
 * OpenLI HIE - Healthcare Integration Engine
 * Copyright (c) 2026 Lightweight Integration Ltd
 * 
 * This file is part of OpenLI HIE.
 * Licensed under AGPL-3.0 (community) or Commercial license.
 * See LICENSE file for details.
 * 
 * Contact: zhong@li-ai.co.uk
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Plus, RefreshCw, Search, Edit3, Trash2, Save, X, ChevronRight } from "lucide-react";

interface Skill {
  name: string;
  description: string;
  scope: "platform" | "tenant" | "project";
  category: "protocol" | "routing" | "transform" | "monitoring" | "deployment" | "general";
  version: string;
  last_modified: string | null;
}

interface SkillDetail extends Skill {
  content: string;
  files: { path: string; content: string }[];
}

// Pre-built HIE integration skills
const DEFAULT_SKILLS: Skill[] = [
  {
    name: "hl7-route-builder",
    description: "Build HL7v2 message routes with receivers, routers, and senders. Supports ADT, ORM, ORU, and custom message types.",
    scope: "platform",
    category: "protocol",
    version: "1.0.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
  {
    name: "fhir-integration",
    description: "Configure FHIR R4 resources, REST endpoints, and HL7-to-FHIR transformations for NHS Spine integration.",
    scope: "platform",
    category: "protocol",
    version: "0.1.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
  {
    name: "mllp-connectivity",
    description: "Set up MLLP TCP connections for HL7 messaging. Includes ACK handling, connection pooling, and retry logic.",
    scope: "platform",
    category: "protocol",
    version: "1.0.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
  {
    name: "content-based-routing",
    description: "Configure content-based routing rules using HL7 field conditions (MSH.9, PID.3, etc.) with AND/OR logic.",
    scope: "platform",
    category: "routing",
    version: "1.0.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
  {
    name: "nhs-trust-deployment",
    description: "Deploy HIE configurations for NHS acute trust environments. Includes security policies, audit logging, and compliance checks.",
    scope: "platform",
    category: "deployment",
    version: "1.0.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
  {
    name: "message-transform",
    description: "Transform messages between protocols (HL7v2 ↔ FHIR, HL7v2 ↔ JSON, CSV → HL7v2). Supports field mapping and enrichment.",
    scope: "platform",
    category: "transform",
    version: "0.2.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
  {
    name: "production-monitoring",
    description: "Monitor HIE production health, throughput metrics, error rates, and queue depths. Configure alerts and thresholds.",
    scope: "platform",
    category: "monitoring",
    version: "1.0.0",
    last_modified: "2026-02-10T00:00:00Z",
  },
];

const SKILL_CONTENT: Record<string, string> = {
  "hl7-route-builder": `# HL7 Route Builder Skill

## Purpose
Guide the agent to build HL7v2 message routes in HIE using the Workspace → Project → Route → Items hierarchy.

## Workflow

1. **Identify Requirements**
   - What HL7 message types? (ADT, ORM, ORU, MDM, etc.)
   - What trigger events? (A01, A02, A03, A08, etc.)
   - Source and destination systems?

2. **Create Items**
   - **Service (Receiver):** HL7TCPService on specified port
   - **Process (Router):** RoutingEngine with field-based rules
   - **Operation (Sender):** HL7TCPOperation to target host:port

3. **Configure Connections**
   - Service → Process → Operation flow
   - Error handling routes

4. **Deploy & Test**
   - Deploy configuration via Manager API
   - Send test HL7 message
   - Verify ACK response

## Example Configuration
\`\`\`json
{
  "items": [
    {
      "name": "ADT_Receiver",
      "type": "service",
      "class_name": "Engine.li.hosts.hl7.HL7TCPService",
      "settings": { "port": 10001, "ackMode": "auto" }
    },
    {
      "name": "ADT_Router",
      "type": "process",
      "class_name": "Engine.li.hosts.routing.RoutingEngine"
    },
    {
      "name": "PAS_Sender",
      "type": "operation",
      "class_name": "Engine.li.hosts.hl7.HL7TCPOperation",
      "settings": { "host": "pas.nhs.local", "port": 2575 }
    }
  ]
}
\`\`\``,
  "content-based-routing": `# Content-Based Routing Skill

## Purpose
Configure intelligent message routing based on HL7 field values.

## Supported Operators
- \`equals\` - Exact match
- \`contains\` - Substring match
- \`regex\` - Regular expression
- \`in\` - Value in list
- \`not_equals\` - Negation

## Common Routing Fields
| Field | Description | Example |
|-------|-------------|---------|
| MSH.9.1 | Message Type | ADT, ORM, ORU |
| MSH.9.2 | Trigger Event | A01, A02, A08 |
| MSH.3 | Sending Application | PAS, EPR |
| MSH.4 | Sending Facility | TRUST01 |
| PID.3 | Patient ID | NHS Number |
| PV1.2 | Patient Class | I, O, E |

## Example Rules
\`\`\`json
{
  "routingRules": [
    {
      "name": "Route ADT A01 to EPR",
      "conditions": [
        { "field": "MSH.9.2", "operator": "equals", "value": "A01" }
      ],
      "target": "EPR_Sender"
    },
    {
      "name": "Route Emergency to Priority Queue",
      "conditions": [
        { "field": "PV1.2", "operator": "equals", "value": "E" }
      ],
      "target": "Emergency_Queue"
    }
  ]
}
\`\`\``,
};

const CATEGORY_COLORS: Record<string, string> = {
  protocol: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  routing: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  transform: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  monitoring: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  deployment: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  general: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

export default function SkillsManagementPage() {
  const [skills, setSkills] = useState<Skill[]>(DEFAULT_SKILLS);
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scopeFilter, setScopeFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [showNewSkillModal, setShowNewSkillModal] = useState(false);
  const [newSkill, setNewSkill] = useState({
    name: "",
    description: "",
    scope: "platform" as const,
    category: "general" as const,
    content: "# New Skill\n\n## Purpose\n\n[Describe the skill purpose]\n\n## Workflow\n\n[Add workflow steps]\n\n## Example\n\n[Add examples]",
  });

  const fetchSkillDetail = useCallback((skill: Skill) => {
    const detail: SkillDetail = {
      ...skill,
      content: SKILL_CONTENT[skill.name] || `# ${skill.name}\n\n${skill.description}\n\n## Configuration\n\nThis skill helps configure ${skill.category} components in HIE.`,
      files: [],
    };
    setSelectedSkill(detail);
    setEditContent(detail.content);
    setEditDescription(detail.description);
  }, []);

  const handleSaveSkill = async () => {
    if (!selectedSkill) return;
    setSaving(true);
    // Simulate save
    await new Promise(resolve => setTimeout(resolve, 500));
    setSelectedSkill({ ...selectedSkill, content: editContent, description: editDescription });
    setIsEditing(false);
    setSaving(false);
  };

  const handleCreateSkill = async () => {
    if (!newSkill.name || !newSkill.description) {
      setError("Name and description are required");
      return;
    }
    setSaving(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    const created: Skill = {
      name: newSkill.name,
      description: newSkill.description,
      scope: newSkill.scope,
      category: newSkill.category,
      version: "1.0.0",
      last_modified: new Date().toISOString(),
    };
    setSkills(prev => [...prev, created]);
    setShowNewSkillModal(false);
    setNewSkill({
      name: "",
      description: "",
      scope: "platform",
      category: "general",
      content: "# New Skill\n\n## Purpose\n\n[Describe the skill purpose]\n\n## Workflow\n\n[Add workflow steps]\n\n## Example\n\n[Add examples]",
    });
    setSaving(false);
  };

  const handleDeleteSkill = (name: string) => {
    if (!confirm(`Delete skill "${name}"?`)) return;
    setSkills(prev => prev.filter(s => s.name !== name));
    if (selectedSkill?.name === name) setSelectedSkill(null);
  };

  const filteredSkills = skills.filter((skill) => {
    if (scopeFilter !== "all" && skill.scope !== scopeFilter) return false;
    if (categoryFilter !== "all" && skill.category !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return skill.name.toLowerCase().includes(q) || skill.description.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <BookOpen className="h-6 w-6" />
            Integration Skills
          </h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage agent skills for HIE route building, protocol configuration, and deployment automation.
          </p>
        </div>
        <button
          onClick={() => setShowNewSkillModal(true)}
          className="flex items-center gap-2 rounded-md bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue transition-colors"
        >
          <Plus className="h-4 w-4" /> New Skill
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700"><X className="h-4 w-4" /></button>
          </div>
        </div>
      )}

      <div className="flex gap-6 h-[calc(100vh-260px)] min-h-[500px]">
        {/* Skills List */}
        <div className="w-80 flex-shrink-0 flex flex-col">
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm flex-1 flex flex-col">
            <div className="p-4 border-b border-gray-200 dark:border-zinc-700 space-y-3">
              <div className="flex gap-2">
                <select
                  value={scopeFilter}
                  onChange={(e) => setScopeFilter(e.target.value)}
                  className="flex-1 rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white"
                >
                  <option value="all">All Scopes</option>
                  <option value="platform">Platform</option>
                  <option value="tenant">Tenant</option>
                  <option value="project">Project</option>
                </select>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="flex-1 rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white"
                >
                  <option value="all">All Categories</option>
                  <option value="protocol">Protocol</option>
                  <option value="routing">Routing</option>
                  <option value="transform">Transform</option>
                  <option value="monitoring">Monitoring</option>
                  <option value="deployment">Deployment</option>
                </select>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search skills..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 pl-10 pr-3 py-1.5 text-sm text-gray-900 dark:text-white"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {filteredSkills.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">No skills found</div>
              ) : (
                <div className="space-y-2">
                  {filteredSkills.map((skill) => (
                    <div
                      key={skill.name}
                      onClick={() => fetchSkillDetail(skill)}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        selectedSkill?.name === skill.name
                          ? "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800"
                          : "bg-gray-50 dark:bg-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-600 border border-transparent"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm text-gray-900 dark:text-white">{skill.name}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${CATEGORY_COLORS[skill.category] || CATEGORY_COLORS.general}`}>
                          {skill.category}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">{skill.description}</p>
                      <div className="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
                        <span>v{skill.version}</span>
                        <span className="capitalize">{skill.scope}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Skill Detail */}
        <div className="flex-1 flex flex-col min-w-0">
          {selectedSkill ? (
            <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm flex-1 flex flex-col">
              <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{selectedSkill.name}</h2>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${CATEGORY_COLORS[selectedSkill.category] || CATEGORY_COLORS.general}`}>
                        {selectedSkill.category}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">v{selectedSkill.version}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">{selectedSkill.scope}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <button onClick={() => { setIsEditing(false); setEditContent(selectedSkill.content); setEditDescription(selectedSkill.description); }}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-zinc-600 rounded-md hover:bg-gray-50 dark:hover:bg-zinc-700">
                          <X className="h-3 w-3" /> Cancel
                        </button>
                        <button onClick={handleSaveSkill} disabled={saving}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-nhs-blue rounded-md hover:bg-nhs-dark-blue disabled:opacity-50">
                          <Save className="h-3 w-3" /> {saving ? "Saving..." : "Save"}
                        </button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => setIsEditing(true)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-nhs-blue border border-nhs-blue/30 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20">
                          <Edit3 className="h-3 w-3" /> Edit
                        </button>
                        <button onClick={() => handleDeleteSkill(selectedSkill.name)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-300 dark:border-red-800 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20">
                          <Trash2 className="h-3 w-3" /> Delete
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {isEditing ? (
                <div className="flex-1 flex flex-col p-4 gap-4 overflow-hidden">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                    <input type="text" value={editDescription} onChange={(e) => setEditDescription(e.target.value)}
                      className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white" />
                  </div>
                  <div className="flex-1 flex flex-col min-h-0">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Skill Content (Markdown)</label>
                    <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)}
                      className="flex-1 w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm font-mono text-gray-900 dark:text-white resize-none"
                      spellCheck={false} />
                  </div>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto p-4">
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{selectedSkill.description}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Skill Content</h3>
                    <pre className="bg-gray-50 dark:bg-zinc-700 border border-gray-200 dark:border-zinc-600 rounded-md p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                      {selectedSkill.content}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500 dark:text-gray-400">
                <BookOpen className="h-12 w-12 mx-auto mb-3 text-gray-300 dark:text-zinc-600" />
                <p className="font-medium">Select a skill to view details</p>
                <p className="text-xs mt-1">Skills guide agents in configuring HIE integrations</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* New Skill Modal */}
      {showNewSkillModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-zinc-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto border border-gray-200 dark:border-zinc-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create New Integration Skill</h3>
              <button onClick={() => setShowNewSkillModal(false)} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name <span className="text-red-500">*</span></label>
                <input type="text" value={newSkill.name}
                  onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })}
                  placeholder="my-skill-name"
                  className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description <span className="text-red-500">*</span></label>
                <textarea value={newSkill.description} onChange={(e) => setNewSkill({ ...newSkill, description: e.target.value })}
                  placeholder="Describe what this skill helps agents do..." rows={3}
                  className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Scope</label>
                  <select value={newSkill.scope} onChange={(e) => setNewSkill({ ...newSkill, scope: e.target.value as any })}
                    className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white">
                    <option value="platform">Platform</option>
                    <option value="tenant">Tenant</option>
                    <option value="project">Project</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Category</label>
                  <select value={newSkill.category} onChange={(e) => setNewSkill({ ...newSkill, category: e.target.value as any })}
                    className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white">
                    <option value="protocol">Protocol</option>
                    <option value="routing">Routing</option>
                    <option value="transform">Transform</option>
                    <option value="monitoring">Monitoring</option>
                    <option value="deployment">Deployment</option>
                    <option value="general">General</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Initial Content</label>
                <textarea value={newSkill.content} onChange={(e) => setNewSkill({ ...newSkill, content: e.target.value })}
                  rows={8} className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm font-mono text-gray-900 dark:text-white" spellCheck={false} />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-zinc-700">
              <button onClick={() => setShowNewSkillModal(false)} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white">Cancel</button>
              <button onClick={handleCreateSkill} disabled={saving || !newSkill.name || !newSkill.description}
                className="px-4 py-2 text-sm font-medium text-white bg-nhs-blue rounded-md hover:bg-nhs-dark-blue disabled:opacity-50">
                {saving ? "Creating..." : "Create Skill"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
