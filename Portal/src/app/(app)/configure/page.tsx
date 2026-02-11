"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Building2,
  ChevronRight,
  Edit,
  FileCode,
  FolderTree,
  GitBranch,
  Layers,
  Plus,
  RefreshCw,
  Server,
  Settings,
  Trash2,
  X,
  Check,
  AlertCircle,
} from "lucide-react";
import {
  listWorkspaces,
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
  listItemTypes,
  Workspace,
  ItemTypeDefinition,
} from "@/lib/api-v2";

type SubTab = "workspaces" | "items" | "schemas" | "routes";

interface WorkspaceFormData {
  name: string;
  display_name: string;
  description: string;
}

export default function ConfigurePage() {
  const [activeTab, setActiveTab] = useState<SubTab>("workspaces");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Workspaces state
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [showWorkspaceForm, setShowWorkspaceForm] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<Workspace | null>(null);
  const [workspaceForm, setWorkspaceForm] = useState<WorkspaceFormData>({ name: "", display_name: "", description: "" });
  const [saving, setSaving] = useState(false);
  
  // Item Types state
  const [itemTypes, setItemTypes] = useState<ItemTypeDefinition[]>([]);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    
    try {
      if (activeTab === "workspaces") {
        const response = await listWorkspaces();
        setWorkspaces(response.workspaces || []);
      } else if (activeTab === "items") {
        const response = await listItemTypes();
        setItemTypes(response.item_types || []);
      }
    } catch (err) {
      console.error("Failed to load data:", err);
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateWorkspace = async () => {
    if (!workspaceForm.name || !workspaceForm.display_name) return;
    setSaving(true);
    try {
      await createWorkspace({
        name: workspaceForm.name,
        display_name: workspaceForm.display_name,
        description: workspaceForm.description,
      });
      setShowWorkspaceForm(false);
      setWorkspaceForm({ name: "", display_name: "", description: "" });
      loadData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateWorkspace = async () => {
    if (!editingWorkspace || !workspaceForm.display_name) return;
    setSaving(true);
    try {
      await updateWorkspace(editingWorkspace.id, {
        display_name: workspaceForm.display_name,
        description: workspaceForm.description,
      });
      setEditingWorkspace(null);
      setWorkspaceForm({ name: "", display_name: "", description: "" });
      loadData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update workspace");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteWorkspace = async (workspace: Workspace) => {
    if (!confirm(`Delete workspace "${workspace.display_name}"? This cannot be undone.`)) return;
    try {
      await deleteWorkspace(workspace.id);
      setSelectedWorkspace(null);
      loadData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete workspace");
    }
  };

  const startEditWorkspace = (workspace: Workspace) => {
    setEditingWorkspace(workspace);
    setWorkspaceForm({
      name: workspace.name,
      display_name: workspace.display_name,
      description: workspace.description || "",
    });
  };

  const getItemTypeIcon = (category: string) => {
    switch (category) {
      case "service": return "bg-green-100 text-green-700";
      case "operation": return "bg-blue-100 text-blue-700";
      case "process": return "bg-purple-100 text-purple-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  const tabs: { id: SubTab; label: string; icon: React.ReactNode }[] = [
    { id: "workspaces", label: "Workspaces", icon: <Building2 className="h-4 w-4" /> },
    { id: "items", label: "Item Types", icon: <Server className="h-4 w-4" /> },
    { id: "schemas", label: "Schemas", icon: <Layers className="h-4 w-4" /> },
    { id: "routes", label: "Routing Rules", icon: <GitBranch className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Configure</h1>
          <p className="mt-1 text-sm text-gray-500">Manage workspaces, item types, schemas, and routing rules</p>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <p className="text-sm text-red-700">{error}</p>
            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Sub-Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "border-nhs-blue text-nhs-blue"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              <div className="flex items-center gap-2">
                {tab.icon}
                {tab.label}
              </div>
            </button>
          ))}
        </nav>
      </div>

      {/* Workspaces Sub-Tab */}
      {activeTab === "workspaces" && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Workspaces List */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Workspaces ({workspaces.length})</h2>
              <button
                onClick={() => { setShowWorkspaceForm(true); setEditingWorkspace(null); setWorkspaceForm({ name: "", display_name: "", description: "" }); }}
                className="inline-flex items-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue"
              >
                <Plus className="h-4 w-4" />
                New Workspace
              </button>
            </div>

            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="h-5 w-40 animate-pulse rounded bg-gray-200" />
                    <div className="mt-2 h-4 w-64 animate-pulse rounded bg-gray-200" />
                  </div>
                ))}
              </div>
            ) : workspaces.length > 0 ? (
              <div className="space-y-3">
                {workspaces.map((ws) => (
                  <div
                    key={ws.id}
                    onClick={() => setSelectedWorkspace(ws)}
                    className={`cursor-pointer rounded-xl border bg-white p-5 shadow-sm transition-all hover:shadow-md ${
                      selectedWorkspace?.id === ws.id ? "border-nhs-blue ring-1 ring-nhs-blue" : "border-gray-200"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-gray-400" />
                          <h3 className="text-sm font-semibold text-gray-900">{ws.display_name}</h3>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">{ws.description || "No description"}</p>
                        <p className="mt-2 text-xs text-gray-400">ID: {ws.name}</p>
                      </div>
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
                <Building2 className="mx-auto h-12 w-12 text-gray-300" />
                <p className="mt-4 text-sm font-medium text-gray-900">No workspaces found</p>
                <p className="mt-1 text-xs text-gray-500">Create your first workspace to get started</p>
              </div>
            )}
          </div>

          {/* Workspace Form / Details */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
            {showWorkspaceForm || editingWorkspace ? (
              <div>
                <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {editingWorkspace ? "Edit Workspace" : "New Workspace"}
                  </h2>
                  <button onClick={() => { setShowWorkspaceForm(false); setEditingWorkspace(null); }} className="text-gray-400 hover:text-gray-600">
                    <X className="h-5 w-5" />
                  </button>
                </div>
                <div className="space-y-4 p-6">
                  {!editingWorkspace && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700">Name (ID)</label>
                      <input
                        type="text"
                        value={workspaceForm.name}
                        onChange={(e) => setWorkspaceForm({ ...workspaceForm, name: e.target.value })}
                        placeholder="my-workspace"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
                      />
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Display Name</label>
                    <input
                      type="text"
                      value={workspaceForm.display_name}
                      onChange={(e) => setWorkspaceForm({ ...workspaceForm, display_name: e.target.value })}
                      placeholder="My Workspace"
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Description</label>
                    <textarea
                      value={workspaceForm.description}
                      onChange={(e) => setWorkspaceForm({ ...workspaceForm, description: e.target.value })}
                      placeholder="Optional description..."
                      rows={3}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-nhs-blue focus:outline-none focus:ring-1 focus:ring-nhs-blue"
                    />
                  </div>
                  <button
                    onClick={editingWorkspace ? handleUpdateWorkspace : handleCreateWorkspace}
                    disabled={saving || (!editingWorkspace && !workspaceForm.name) || !workspaceForm.display_name}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-nhs-blue px-4 py-2 text-sm font-medium text-white hover:bg-nhs-dark-blue disabled:opacity-50"
                  >
                    {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    {editingWorkspace ? "Update Workspace" : "Create Workspace"}
                  </button>
                </div>
              </div>
            ) : selectedWorkspace ? (
              <div>
                <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                  <h2 className="text-lg font-semibold text-gray-900">{selectedWorkspace.display_name}</h2>
                  <div className="flex items-center gap-2">
                    <button onClick={() => startEditWorkspace(selectedWorkspace)} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                      <Edit className="h-4 w-4" />
                    </button>
                    <button onClick={() => handleDeleteWorkspace(selectedWorkspace)} className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="space-y-4 p-6">
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">ID</h3>
                    <p className="mt-1 font-mono text-sm text-gray-900">{selectedWorkspace.name}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">Description</h3>
                    <p className="mt-1 text-sm text-gray-900">{selectedWorkspace.description || "No description"}</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-medium uppercase text-gray-500">Created</h3>
                    <p className="mt-1 text-sm text-gray-900">{selectedWorkspace.created_at ? new Date(selectedWorkspace.created_at).toLocaleString() : "-"}</p>
                  </div>
                  <Link
                    href={`/projects?workspace=${selectedWorkspace.id}`}
                    className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    <FolderTree className="h-4 w-4" />
                    View Projects
                  </Link>
                </div>
              </div>
            ) : (
              <div className="flex h-80 flex-col items-center justify-center text-center p-6">
                <Building2 className="h-12 w-12 text-gray-300" />
                <p className="mt-4 text-sm font-medium text-gray-900">Select a workspace</p>
                <p className="mt-1 text-xs text-gray-500">Click on a workspace to view details</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Item Types Sub-Tab */}
      {activeTab === "items" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Registered Item Types ({itemTypes.length})</h2>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                Services ({itemTypes.filter((t) => t.category === "service").length})
              </span>
              <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
                Operations ({itemTypes.filter((t) => t.category === "operation").length})
              </span>
              <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-700">
                Processes ({itemTypes.filter((t) => t.category === "process").length})
              </span>
              <button
                onClick={async () => {
                  try {
                    const res = await fetch("/api/item-types/reload-custom", { method: "POST" });
                    if (res.ok) {
                      const data = await res.json();
                      alert(`Custom classes reloaded: ${data.modules_loaded || 0} modules, ${(data.registered?.hosts || []).length} hosts`);
                      const typesRes = await listItemTypes();
                      setItemTypes(typesRes.item_types || []);
                    }
                  } catch (e) { console.error("Reload failed", e); }
                }}
                className="flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100 transition-colors"
                title="Hot-reload custom.* classes from Engine/custom/ without restarting"
              >
                <RefreshCw className="h-3 w-3" />
                Reload Custom
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Class Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3"><div className="h-4 w-32 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-5 w-20 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-4 w-48 animate-pulse rounded bg-gray-200" /></td>
                      <td className="px-4 py-3"><div className="h-4 w-64 animate-pulse rounded bg-gray-200" /></td>
                    </tr>
                  ))
                ) : itemTypes.length > 0 ? (
                  itemTypes.map((itemType) => {
                    const isCustom = itemType.li_class_name.startsWith('custom.');
                    return (
                    <tr key={itemType.type} className={`hover:bg-gray-50 ${isCustom ? 'bg-emerald-50/30' : ''}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-gray-900">{itemType.name}</p>
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${isCustom ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                            {isCustom ? 'custom' : 'core'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${getItemTypeIcon(itemType.category)}`}>
                          {itemType.category}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <code className={`text-xs ${isCustom ? 'text-emerald-600' : 'text-gray-600'}`}>{itemType.li_class_name}</code>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-xs text-gray-500 truncate max-w-xs">{itemType.description || "-"}</p>
                      </td>
                    </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                      No item types registered
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Schemas Sub-Tab */}
      {activeTab === "schemas" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">HL7 Schemas</h2>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {["2.3", "2.4", "2.5", "2.5.1", "2.6", "2.7"].map((version) => (
              <div key={version} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-blue-100 p-2">
                      <Layers className="h-5 w-5 text-blue-700" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">HL7 v{version}</h3>
                      <p className="text-xs text-gray-500">Standard schema</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                    Active
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-900">FHIR Schemas</h3>
            <p className="mt-2 text-sm text-gray-500">FHIR R4 schema support is planned for a future release.</p>
          </div>
        </div>
      )}

      {/* Routes Sub-Tab */}
      {activeTab === "routes" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Routing Rules</h2>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
            <GitBranch className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm font-medium text-gray-900">Project-Level Routing Rules</p>
            <p className="mt-1 text-xs text-gray-500">
              Routing rules are managed within each project. Open a project and go to the <strong>Routing Rules</strong> tab to create, edit, and manage rules.
            </p>
            <Link
              href="/projects"
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <FolderTree className="h-4 w-4" />
              Go to Projects
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
