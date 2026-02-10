"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface PromptTemplate {
  id: string;
  tenant_id: string | null;
  owner_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  category: string;
  tags: string[] | null;
  template_body: string;
  variables: Record<string, { type?: string; default?: string | number | boolean; description?: string }> | null;
  version: number;
  is_latest: boolean;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

const CATEGORIES = [
  { value: "", label: "All Categories" },
  { value: "hl7", label: "HL7" },
  { value: "fhir", label: "FHIR" },
  { value: "clinical", label: "Clinical" },
  { value: "compliance", label: "Compliance" },
  { value: "integration", label: "Integration" },
  { value: "development", label: "Development" },
  { value: "architecture", label: "Architecture" },
  { value: "support", label: "Support" },
  { value: "general", label: "General" },
];

export default function PromptsPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");

  // Use Template Modal
  const [useModal, setUseModal] = useState<PromptTemplate | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [renderedPrompt, setRenderedPrompt] = useState("");

  // New Template Modal
  const [showNewModal, setShowNewModal] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: "",
    description: "",
    category: "general",
    template_body: "",
  });
  const [creating, setCreating] = useState(false);

  // Edit Template Modal
  const [editModal, setEditModal] = useState<PromptTemplate | null>(null);
  const [editFields, setEditFields] = useState({ template_body: "", description: "" });
  const [saving, setSaving] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (search) params.set("search", search);

      const res = await fetch(`/api/prompt-manager/templates?${params.toString()}`);
      if (!res.ok) throw new Error(`Failed to fetch templates: ${res.statusText}`);
      const data = await res.json();
      setTemplates(data.templates || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch templates");
    } finally {
      setLoading(false);
    }
  }, [category, search]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const getVariableKeys = (tpl: PromptTemplate): string[] => {
    if (tpl.variables && typeof tpl.variables === "object") {
      return Object.keys(tpl.variables);
    }
    // Fallback: extract {{var}} from template body
    const matches = tpl.template_body.match(/\{\{(\w+)\}\}/g);
    if (!matches) return [];
    return [...new Set(matches.map((m) => m.replace(/\{\{|\}\}/g, "")))];
  };

  const handleUseTemplate = (t: PromptTemplate) => {
    const keys = getVariableKeys(t);
    const initial: Record<string, string> = {};
    for (const key of keys) {
      const varDef = t.variables?.[key];
      initial[key] = varDef?.default != null ? String(varDef.default) : "";
    }
    setVariableValues(initial);
    setUseModal(t);
    let rendered = t.template_body;
    for (const [k, val] of Object.entries(initial)) {
      rendered = rendered.replaceAll(`{{${k}}}`, val);
    }
    setRenderedPrompt(rendered);
  };

  const updateVariable = (name: string, value: string) => {
    const updated = { ...variableValues, [name]: value };
    setVariableValues(updated);
    if (useModal) {
      let rendered = useModal.template_body;
      for (const [k, val] of Object.entries(updated)) {
        rendered = rendered.replaceAll(`{{${k}}}`, val);
      }
      setRenderedPrompt(rendered);
    }
  };

  const handleSendToAgent = () => {
    sessionStorage.setItem("prefill-prompt", renderedPrompt);
    router.push("/agents");
  };

  const handleCopyToClipboard = async () => {
    await navigator.clipboard.writeText(renderedPrompt);
  };

  const handleCreateTemplate = async () => {
    setCreating(true);
    try {
      const res = await fetch("/api/prompt-manager/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTemplate),
      });
      if (!res.ok) throw new Error("Failed to create template");
      setShowNewModal(false);
      setNewTemplate({ name: "", description: "", category: "general", template_body: "" });
      fetchTemplates();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create template");
    } finally {
      setCreating(false);
    }
  };

  const handleEditTemplate = (t: PromptTemplate) => {
    setEditFields({ template_body: t.template_body, description: t.description || "" });
    setEditModal(t);
  };

  const handleSaveEdit = async () => {
    if (!editModal) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/prompt-manager/templates/${editModal.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editFields),
      });
      if (!res.ok) throw new Error("Failed to update template");
      setEditModal(null);
      fetchTemplates();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update template");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    if (!confirm("Delete this template and all its versions?")) return;
    try {
      await fetch(`/api/prompt-manager/templates/${id}`, { method: "DELETE" });
      fetchTemplates();
    } catch {
      alert("Failed to delete template");
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await fetch(`/api/prompt-manager/templates/${id}/publish`, { method: "POST" });
      fetchTemplates();
    } catch {
      alert("Failed to publish template");
    }
  };

  const statusBadge = (published: boolean) => {
    if (published) {
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          Published
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
        Draft
      </span>
    );
  };

  const categoryBadgeColor = (cat: string): string => {
    const colors: Record<string, string> = {
      hl7: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
      fhir: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
      clinical: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
      compliance: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
      integration: "bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-300",
      development: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300",
      architecture: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300",
    };
    return colors[cat] || "bg-zinc-100 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">Prompt Templates</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Create, manage, and share parameterised prompt templates for healthcare integration
          </p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + New Template
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm text-zinc-900 dark:text-white"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search templates..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[200px] rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm text-zinc-900 dark:text-white placeholder-zinc-400"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-sm text-zinc-500 dark:text-zinc-400">Loading templates...</div>
        </div>
      )}

      {/* Empty State */}
      {!loading && templates.length === 0 && (
        <div className="rounded-lg border border-dashed border-zinc-300 dark:border-zinc-600 p-12 text-center">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No templates found. Create your first prompt template to get started.
          </p>
        </div>
      )}

      {/* Template Cards */}
      {!loading && templates.length > 0 && (
        <div className="space-y-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-zinc-900 dark:text-white truncate">{t.name}</h3>
                    <span className="text-xs text-zinc-400">v{t.version}</span>
                    {statusBadge(t.is_published)}
                  </div>
                  {t.description && (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-2 line-clamp-2">{t.description}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
                    <span className={`inline-flex items-center rounded px-2 py-0.5 font-medium ${categoryBadgeColor(t.category)}`}>
                      {t.category}
                    </span>
                    {t.tags?.map((tag) => (
                      <span key={tag} className="text-zinc-400">#{tag}</span>
                    ))}
                    {getVariableKeys(t).length > 0 && (
                      <span>{getVariableKeys(t).length} variable{getVariableKeys(t).length !== 1 ? "s" : ""}</span>
                    )}
                    <span>{new Date(t.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                  <button
                    onClick={() => handleUseTemplate(t)}
                    className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                  >
                    Use
                  </button>
                  <button
                    onClick={() => handleEditTemplate(t)}
                    className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                  >
                    Edit
                  </button>
                  {!t.is_published && (
                    <button
                      onClick={() => handlePublish(t.id)}
                      className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
                    >
                      Publish
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteTemplate(t.id)}
                    className="rounded-md border border-zinc-300 dark:border-zinc-600 px-3 py-1.5 text-xs text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          <div className="text-xs text-zinc-400 dark:text-zinc-500 text-right">
            Showing {templates.length} of {total} templates
          </div>
        </div>
      )}

      {/* Use Template Modal */}
      {useModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg bg-white dark:bg-zinc-800 shadow-xl">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-700 px-6 py-4">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">
                Use: {useModal.name}
              </h2>
              <button onClick={() => setUseModal(null)} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xl">&times;</button>
            </div>
            <div className="p-6 space-y-4">
              {/* Variable Inputs */}
              {getVariableKeys(useModal).length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Fill in variables:</h3>
                  {getVariableKeys(useModal).map((key) => {
                    const varDef = useModal.variables?.[key];
                    const varType = varDef?.type || "string";
                    return (
                      <div key={key}>
                        <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                          {`{{${key}}}`}
                          {varDef?.description && <span className="font-normal text-zinc-400"> &mdash; {varDef.description}</span>}
                        </label>
                        {varType === "text" ? (
                          <textarea
                            value={variableValues[key] || ""}
                            onChange={(e) => updateVariable(key, e.target.value)}
                            rows={3}
                            className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white"
                          />
                        ) : (
                          <input
                            type={varType === "number" ? "number" : "text"}
                            value={variableValues[key] || ""}
                            onChange={(e) => updateVariable(key, e.target.value)}
                            className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Preview */}
              <div>
                <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">Preview:</h3>
                <div className="rounded-md border border-zinc-200 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-900 p-4 text-sm text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap max-h-60 overflow-y-auto font-mono text-xs">
                  {renderedPrompt}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-zinc-200 dark:border-zinc-700 px-6 py-4">
              <button
                onClick={handleCopyToClipboard}
                className="rounded-md border border-zinc-300 dark:border-zinc-600 px-4 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700"
              >
                Copy
              </button>
              <button
                onClick={handleSendToAgent}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Send to Agent Console
              </button>
              <button
                onClick={() => setUseModal(null)}
                className="rounded-md border border-zinc-300 dark:border-zinc-600 px-4 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Template Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg bg-white dark:bg-zinc-800 shadow-xl">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-700 px-6 py-4">
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">New Prompt Template</h2>
              <button onClick={() => setShowNewModal(false)} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xl">&times;</button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">Name *</label>
                <input
                  type="text"
                  value={newTemplate.name}
                  onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  placeholder="e.g. HL7 ADT Route Configuration"
                  className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">Description</label>
                <input
                  type="text"
                  value={newTemplate.description}
                  onChange={(e) => setNewTemplate({ ...newTemplate, description: e.target.value })}
                  placeholder="Brief description of what this template does"
                  className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">Category *</label>
                <select
                  value={newTemplate.category}
                  onChange={(e) => setNewTemplate({ ...newTemplate, category: e.target.value })}
                  className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white"
                >
                  {CATEGORIES.filter((c) => c.value).map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                  Template Body * <span className="font-normal text-zinc-400">&mdash; Use {"{{variable_name}}"} for parameters</span>
                </label>
                <textarea
                  value={newTemplate.template_body}
                  onChange={(e) => setNewTemplate({ ...newTemplate, template_body: e.target.value })}
                  rows={10}
                  placeholder={"Configure an HL7 {{message_type}} route for {{facility_name}}.\n\nInbound port: {{inbound_port}}\nTarget system: {{target_system}}"}
                  className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white font-mono"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-zinc-200 dark:border-zinc-700 px-6 py-4">
              <button
                onClick={() => setShowNewModal(false)}
                className="rounded-md border border-zinc-300 dark:border-zinc-600 px-4 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateTemplate}
                disabled={creating || !newTemplate.name || !newTemplate.template_body}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creating ? "Creating..." : "Create Template"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Template Modal */}
      {editModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg bg-white dark:bg-zinc-800 shadow-xl">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-700 px-6 py-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">Edit: {editModal.name}</h2>
                <p className="text-xs text-zinc-400 dark:text-zinc-500">Current version: v{editModal.version} &mdash; Saving creates a new version</p>
              </div>
              <button onClick={() => setEditModal(null)} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xl">&times;</button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">Description</label>
                <input
                  type="text"
                  value={editFields.description}
                  onChange={(e) => setEditFields({ ...editFields, description: e.target.value })}
                  className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
                  Template Body <span className="font-normal text-zinc-400">&mdash; Use {"{{variable_name}}"} for parameters</span>
                </label>
                <textarea
                  value={editFields.template_body}
                  onChange={(e) => setEditFields({ ...editFields, template_body: e.target.value })}
                  rows={12}
                  className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-zinc-900 dark:text-white font-mono"
                />
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-zinc-200 dark:border-zinc-700 px-6 py-4">
              <p className="text-xs text-zinc-400">This will create version v{editModal.version + 1}</p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setEditModal(null)}
                  className="rounded-md border border-zinc-300 dark:border-zinc-600 px-4 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={saving}
                  className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : `Save as v${editModal.version + 1}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
