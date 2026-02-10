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
  id: string;
  name: string;
  slug: string;
  description: string | null;
  scope: string;
  category: string;
  skill_content: string;
  allowed_tools: string | null;
  is_user_invocable: boolean;
  version: number;
  is_latest: boolean;
  is_published: boolean;
  is_enabled: boolean;
  source: string;
  file_path: string | null;
  created_at: string;
  updated_at: string;
}


const CATEGORY_COLORS: Record<string, string> = {
  protocol: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  routing: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  transform: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  monitoring: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  deployment: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  general: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

export default function SkillsManagementPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [loading, setLoading] = useState(true);
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
    scope: "platform",
    category: "general",
    skill_content: "# New Skill\n\n## Purpose\n\n[Describe the skill purpose]\n\n## Workflow\n\n[Add workflow steps]\n\n## Example\n\n[Add examples]",
  });

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (scopeFilter !== "all") params.set("scope", scopeFilter);
      if (categoryFilter !== "all") params.set("category", categoryFilter);
      if (searchQuery) params.set("search", searchQuery);
      const res = await fetch(`/api/prompt-manager/skills?${params.toString()}`);
      if (!res.ok) throw new Error(`Failed to fetch skills: ${res.statusText}`);
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch skills");
    } finally {
      setLoading(false);
    }
  }, [scopeFilter, categoryFilter, searchQuery]);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const fetchSkillDetail = useCallback(async (skill: Skill) => {
    try {
      const res = await fetch(`/api/prompt-manager/skills/${skill.id}`);
      if (!res.ok) throw new Error("Failed to fetch skill detail");
      const data = await res.json();
      setSelectedSkill(data);
      setEditContent(data.skill_content || "");
      setEditDescription(data.description || "");
    } catch {
      setSelectedSkill(skill);
      setEditContent(skill.skill_content || "");
      setEditDescription(skill.description || "");
    }
  }, []);

  const handleSaveSkill = async () => {
    if (!selectedSkill) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/prompt-manager/skills/${selectedSkill.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_content: editContent, description: editDescription }),
      });
      if (!res.ok) throw new Error("Failed to update skill");
      const updated = await res.json();
      setSelectedSkill(updated);
      setIsEditing(false);
      fetchSkills();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to save skill");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateSkill = async () => {
    if (!newSkill.name || !newSkill.description) {
      setError("Name and description are required");
      return;
    }
    setSaving(true);
    try {
      const res = await fetch("/api/prompt-manager/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newSkill),
      });
      if (!res.ok) throw new Error("Failed to create skill");
      setShowNewSkillModal(false);
      setNewSkill({
        name: "",
        description: "",
        scope: "platform",
        category: "general",
        skill_content: "# New Skill\n\n## Purpose\n\n[Describe the skill purpose]\n\n## Workflow\n\n[Add workflow steps]\n\n## Example\n\n[Add examples]",
      });
      fetchSkills();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create skill");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSkill = async (id: string) => {
    if (!confirm("Delete this skill and all its versions?")) return;
    try {
      await fetch(`/api/prompt-manager/skills/${id}`, { method: "DELETE" });
      if (selectedSkill?.id === id) setSelectedSkill(null);
      fetchSkills();
    } catch {
      alert("Failed to delete skill");
    }
  };

  const handleSyncFromFiles = async () => {
    try {
      const res = await fetch("/api/prompt-manager/skills/sync-from-files", { method: "POST" });
      if (!res.ok) throw new Error("Sync failed");
      const data = await res.json();
      alert(`Synced ${data.total} skills from agent-runner files`);
      fetchSkills();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Sync failed");
    }
  };

  const filteredSkills = skills;

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
        <div className="flex gap-2">
          <button
            onClick={handleSyncFromFiles}
            className="flex items-center gap-2 rounded-md border border-gray-300 dark:border-zinc-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
          >
            <RefreshCw className="h-4 w-4" /> Sync from Files
          </button>
          <button
            onClick={() => setShowNewSkillModal(true)}
            className="flex items-center gap-2 rounded-md bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue transition-colors"
          >
            <Plus className="h-4 w-4" /> New Skill
          </button>
        </div>
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
                      key={skill.id}
                      onClick={() => fetchSkillDetail(skill)}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        selectedSkill?.id === skill.id
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
                        <span>v{skill.version}{skill.source === "file" ? " (file)" : ""}</span>
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
                      {selectedSkill.is_published && <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">Published</span>}
                      {!selectedSkill.is_enabled && <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">Disabled</span>}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <button onClick={() => { setIsEditing(false); setEditContent(selectedSkill.skill_content); setEditDescription(selectedSkill.description || ""); }}
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
                        <button onClick={() => handleDeleteSkill(selectedSkill.id)}
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
                      {selectedSkill.skill_content}
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
                <textarea value={newSkill.skill_content} onChange={(e) => setNewSkill({ ...newSkill, skill_content: e.target.value })}
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
