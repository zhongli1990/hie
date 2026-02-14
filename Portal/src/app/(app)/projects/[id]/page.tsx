'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useWorkspace } from '@/contexts/WorkspaceContext';
import { ReactFlowProvider } from 'reactflow';
import { ProductionDiagram } from '@/components/ProductionDiagram';
import {
  getProject,
  deployProject,
  startProject,
  stopProject,
  createItem,
  updateItem,
  deleteItem,
  reloadItem,
  testItem,
  createConnection,
  deleteConnection,
  createRoutingRule,
  updateRoutingRule,
  deleteRoutingRule,
  listItemTypes,
  type ProjectDetail,
  type ProjectItem,
  type Connection,
  type RoutingRule,
  type RoutingRuleCreate,
  type ItemCreate,
  type ItemTypeDefinition,
  type TestMessageResult,
} from '@/lib/api-v2';

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { currentWorkspace } = useWorkspace();
  
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [itemTypes, setItemTypes] = useState<ItemTypeDefinition[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<ProjectItem | null>(null);
  const [showAddItemModal, setShowAddItemModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'items' | 'connections' | 'routing' | 'topology' | 'settings'>('items');

  const loadProject = async () => {
    if (!currentWorkspace || !projectId) return;
    
    try {
      setIsLoading(true);
      setError(null);
      const [projectData, typesData] = await Promise.all([
        getProject(currentWorkspace.id, projectId),
        listItemTypes(),
      ]);
      setProject(projectData);
      setItemTypes(typesData.item_types);
      
      // Update selectedItem if it exists in the new data
      if (selectedItem) {
        const updatedItem = projectData.items.find(i => i.id === selectedItem.id);
        if (updatedItem) {
          setSelectedItem(updatedItem);
        } else {
          setSelectedItem(null);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProject();
  }, [currentWorkspace, projectId]);

  const handleDeploy = async () => {
    if (!currentWorkspace || !projectId) return;
    try {
      await deployProject(currentWorkspace.id, projectId, true);
      await loadProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deploy project');
    }
  };

  const handleStart = async () => {
    if (!currentWorkspace || !projectId) return;
    try {
      await startProject(currentWorkspace.id, projectId);
      await loadProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start project');
    }
  };

  const handleStop = async () => {
    if (!currentWorkspace || !projectId) return;
    try {
      await stopProject(currentWorkspace.id, projectId);
      await loadProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop project');
    }
  };

  const handleDeleteItem = async (itemId: string, itemName: string) => {
    if (!confirm(`Delete item "${itemName}"?`)) return;
    try {
      await deleteItem(projectId, itemId);
      await loadProject();
      if (selectedItem?.id === itemId) {
        setSelectedItem(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete item');
    }
  };

  const handleDeleteConnection = async (connectionId: string) => {
    if (!confirm('Delete this connection?')) return;
    try {
      await deleteConnection(projectId, connectionId);
      await loadProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete connection');
    }
  };

  if (!currentWorkspace) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a workspace</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <h2 className="text-lg font-medium text-gray-900">Project not found</h2>
          <Link href="/projects" className="mt-4 text-blue-600 hover:underline">
            Back to projects
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/projects" className="text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{project.display_name}</h1>
              <p className="text-sm text-gray-500">{project.name} • v{project.version}</p>
            </div>
            <StateIndicator state={project.state} />
          </div>
          <div className="flex items-center gap-3">
            {project.state === 'running' ? (
              <button
                onClick={handleStop}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
                Stop
              </button>
            ) : (
              <>
                <button
                  onClick={handleDeploy}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Deploy & Start
                </button>
                {project.items.length > 0 && (
                  <button
                    onClick={handleStart}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Start
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg">
            {error}
            <button onClick={() => setError(null)} className="ml-2 underline">Dismiss</button>
          </div>
        )}

        {/* Tabs */}
        <div className="mt-4 flex gap-4 border-b -mb-px">
          {(['items', 'connections', 'routing', 'topology', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === tab
                  ? 'text-blue-600 border-blue-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              {tab === 'routing' ? 'Routing Rules' : tab === 'topology' ? '⭐ Topology' : tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'items' && ` (${project.items.length})`}
              {tab === 'connections' && ` (${project.connections.length})`}
              {tab === 'routing' && ` (${project.routing_rules?.length || 0})`}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {activeTab === 'items' && (
          <>
            {/* Items List */}
            <div className="w-80 border-r bg-gray-50 overflow-y-auto">
              <div className="p-4">
                <button
                  onClick={() => setShowAddItemModal(true)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Item
                </button>
              </div>

              {project.items.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-gray-500">
                  No items yet. Add a service, process, or operation to get started.
                </div>
              ) : (
                <div className="space-y-1 px-2">
                  {project.items.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setSelectedItem(item)}
                      className={`w-full text-left px-3 py-2 rounded-lg ${
                        selectedItem?.id === item.id
                          ? 'bg-blue-100 text-blue-900'
                          : 'hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <ItemTypeIcon type={item.item_type} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{item.name}</p>
                          <p className="text-xs text-gray-500 truncate">{item.class_name}</p>
                        </div>
                        {!item.enabled && (
                          <span className="text-xs text-gray-400">Disabled</span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Item Detail */}
            <div className="flex-1 overflow-y-auto p-6">
              {selectedItem ? (
                <ItemDetailPanel
                  item={selectedItem}
                  itemTypes={itemTypes}
                  projectId={projectId}
                  existingItems={project.items}
                  onUpdate={loadProject}
                  onDelete={() => handleDeleteItem(selectedItem.id, selectedItem.name)}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500">
                  Select an item to view details
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'connections' && (
          <div className="flex-1 overflow-y-auto p-6">
            <ConnectionsPanel
              connections={project.connections}
              items={project.items}
              projectId={projectId}
              onUpdate={loadProject}
              onDelete={handleDeleteConnection}
            />
          </div>
        )}

        {activeTab === 'routing' && (
          <div className="flex-1 overflow-y-auto p-6">
            <RoutingRulesPanel
              rules={project.routing_rules || []}
              items={project.items}
              projectId={projectId}
              onUpdate={loadProject}
            />
          </div>
        )}

        {activeTab === 'topology' && (
          <div className="flex-1 overflow-y-auto p-6">
            <ReactFlowProvider>
              <ProductionDiagram
                items={project.items}
                connections={project.connections}
                routingRules={project.routing_rules || []}
                onUpdatePosition={async (itemId, x, y) => {
                  try {
                    await updateItem(projectId, itemId, { position: { x, y } });
                  } catch (err) {
                    console.error('Failed to update item position:', err);
                  }
                }}
              />
            </ReactFlowProvider>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="flex-1 overflow-y-auto p-6">
            <ProjectSettingsPanel project={project} />
          </div>
        )}
      </div>

      {showAddItemModal && (
        <AddItemModal
          projectId={projectId}
          itemTypes={itemTypes}
          existingItems={project.items}
          onClose={() => setShowAddItemModal(false)}
          onCreated={() => {
            setShowAddItemModal(false);
            loadProject();
          }}
        />
      )}
    </div>
  );
}

function StateIndicator({ state }: { state: string }) {
  const config: Record<string, { color: string; label: string }> = {
    running: { color: 'bg-green-100 text-green-800', label: 'Running' },
    stopped: { color: 'bg-gray-100 text-gray-800', label: 'Stopped' },
    starting: { color: 'bg-yellow-100 text-yellow-800', label: 'Starting' },
    stopping: { color: 'bg-yellow-100 text-yellow-800', label: 'Stopping' },
    error: { color: 'bg-red-100 text-red-800', label: 'Error' },
  };
  const c = config[state] || config.stopped;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${c.color}`}>
      {state === 'running' && <span className="w-2 h-2 mr-1.5 bg-green-500 rounded-full animate-pulse" />}
      {c.label}
    </span>
  );
}

function ItemTypeIcon({ type }: { type: string }) {
  const colors: Record<string, string> = {
    service: 'bg-green-100 text-green-600',
    process: 'bg-blue-100 text-blue-600',
    operation: 'bg-purple-100 text-purple-600',
  };
  const icons: Record<string, React.ReactNode> = {
    service: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 4H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-2m-4-1v8m0 0l3-3m-3 3L9 8m-5 5h2.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293h3.172a1 1 0 00.707-.293l2.414-2.414a1 1 0 01.707-.293H20" />
      </svg>
    ),
    process: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
    operation: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
      </svg>
    ),
  };
  return (
    <div className={`p-1.5 rounded ${colors[type] || 'bg-gray-100 text-gray-600'}`}>
      {icons[type] || icons.process}
    </div>
  );
}

interface ItemDetailPanelProps {
  item: ProjectItem;
  itemTypes: ItemTypeDefinition[];
  projectId: string;
  existingItems: ProjectItem[];
  onUpdate: () => void;
  onDelete: () => void;
}

// Generate default HL7 test message
function generateDefaultHL7Message(): string {
  const now = new Date();
  const timestamp = now.toISOString().replace(/[-:T.Z]/g, '').slice(0, 14);
  const msgId = `TEST${timestamp}`;
  return [
    `MSH|^~\\&|HIE|HIE|REMOTE|REMOTE|${timestamp}||ADT^A01|${msgId}|P|2.4`,
    `EVN|A01|${timestamp}`,
    `PID|1||TEST123^^^MRN||Doe^John^Q||19800101|M|||123 Main St^^London^^SW1A 1AA^UK`,
    `PV1|1|I|WARD1^ROOM1^BED1||||12345^Smith^Jane|||MED||||||||V123456`,
  ].join('\r');
}

// Format HL7 message for display with segment highlighting
function formatHL7Display(message: string): React.ReactNode {
  if (!message) return null;
  
  // Handle both \r and \\r as segment separators
  const segments = message.split(/\\r|\r|\n/).filter(s => s.trim());
  
  const segmentColors: Record<string, string> = {
    'MSH': 'text-blue-400',
    'EVN': 'text-cyan-400',
    'PID': 'text-green-400',
    'PV1': 'text-yellow-400',
    'MSA': 'text-purple-400',
    'ERR': 'text-red-400',
    'OBR': 'text-orange-400',
    'OBX': 'text-pink-400',
  };
  
  return segments.map((segment, idx) => {
    const segmentType = segment.substring(0, 3);
    const colorClass = segmentColors[segmentType] || 'text-gray-300';
    return (
      <div key={idx} className={`${colorClass} hover:bg-gray-800 px-1 -mx-1 rounded`}>
        <span className="text-gray-500 select-none mr-2">{String(idx + 1).padStart(2, '0')}</span>
        {segment}
      </div>
    );
  });
}

function ItemDetailPanel({ item, itemTypes, projectId, existingItems, onUpdate, onDelete }: ItemDetailPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestMessageResult | null>(null);
  const [showTestModal, setShowTestModal] = useState(false);
  const [testMessage, setTestMessage] = useState(generateDefaultHL7Message());
  const [sentMessage, setSentMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editedPoolSize, setEditedPoolSize] = useState(item.pool_size);
  const [editedEnabled, setEditedEnabled] = useState(item.enabled);
  const [editedAdapterSettings, setEditedAdapterSettings] = useState<Record<string, unknown>>(item.adapter_settings);
  const [editedHostSettings, setEditedHostSettings] = useState<Record<string, unknown>>(item.host_settings);
  
  const itemType = itemTypes.find(t => t.li_class_name === item.class_name || t.iris_class_name === item.class_name);
  const isOperation = item.item_type === 'operation';

  // Reset edit state when item changes
  useEffect(() => {
    setEditedPoolSize(item.pool_size);
    setEditedEnabled(item.enabled);
    setEditedAdapterSettings(item.adapter_settings);
    setEditedHostSettings(item.host_settings);
    setIsEditing(false);
    setError(null);
  }, [item.id]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      await updateItem(projectId, item.id, {
        pool_size: editedPoolSize,
        enabled: editedEnabled,
        adapter_settings: editedAdapterSettings,
        host_settings: editedHostSettings,
      });
      setIsEditing(false);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReload = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const result = await reloadItem(projectId, item.id);
      if (result.message) {
        // Show info message (not an error)
        setError(`ℹ️ ${result.message}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reload item');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedPoolSize(item.pool_size);
    setEditedEnabled(item.enabled);
    setEditedAdapterSettings(item.adapter_settings);
    setEditedHostSettings(item.host_settings);
    setIsEditing(false);
    setError(null);
  };

  const handleTest = async (customMessage?: string) => {
    setIsTesting(true);
    setError(null);
    setTestResult(null);
    const messageToSend = customMessage || testMessage;
    setSentMessage(messageToSend);
    try {
      const result = await testItem(projectId, item.name, messageToSend);
      setTestResult(result);
      setShowTestModal(true);
    } catch (err) {
      setTestResult({ status: 'error', item_name: item.name, error: err instanceof Error ? err.message : 'Failed to send test message' });
      setShowTestModal(true);
    } finally {
      setIsTesting(false);
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{item.name}</h2>
          <p className="text-sm text-gray-500">{item.class_name}</p>
        </div>
        <div className="flex gap-2">
          {!isEditing ? (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                title="Edit item"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                onClick={handleReload}
                disabled={isSaving}
                className="p-2 text-green-600 hover:bg-green-50 rounded disabled:opacity-50"
                title="Hot reload item (apply changes to running engine)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              {isOperation && (
                <button
                  onClick={() => setShowTestModal(true)}
                  disabled={isTesting}
                  className="p-2 text-purple-600 hover:bg-purple-50 rounded disabled:opacity-50"
                  title="Send test message"
                >
                  {isTesting ? (
                    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                </button>
              )}
              <button
                onClick={onDelete}
                className="p-2 text-red-600 hover:bg-red-50 rounded"
                title="Delete item"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleCancel}
                disabled={isSaving}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">×</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs font-medium text-gray-500 uppercase">Type</p>
          <p className="mt-1 text-sm font-medium text-gray-900 capitalize">{item.item_type}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs font-medium text-gray-500 uppercase">Pool Size</p>
          {isEditing ? (
            <input
              type="number"
              min={1}
              max={100}
              value={editedPoolSize}
              onChange={(e) => setEditedPoolSize(Number(e.target.value))}
              className="mt-1 w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
            />
          ) : (
            <p className="mt-1 text-sm font-medium text-gray-900">{item.pool_size}</p>
          )}
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs font-medium text-gray-500 uppercase">Enabled</p>
          {isEditing ? (
            <label className="mt-1 flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={editedEnabled}
                onChange={(e) => setEditedEnabled(e.target.checked)}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded"
              />
              <span className="text-sm text-gray-700">{editedEnabled ? 'Yes' : 'No'}</span>
            </label>
          ) : (
            <p className="mt-1 text-sm font-medium text-gray-900">{item.enabled ? 'Yes' : 'No'}</p>
          )}
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-xs font-medium text-gray-500 uppercase">Category</p>
          <p className="mt-1 text-sm font-medium text-gray-900">{item.category || '-'}</p>
        </div>
      </div>

      {(Object.keys(item.adapter_settings).length > 0 || isEditing) && itemType && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Adapter Settings</h3>
          {isEditing ? (
            <div className="space-y-4 bg-gray-50 rounded-lg p-4">
              {itemType.adapter_settings.map((setting) => (
                <SettingField
                  key={setting.key}
                  setting={setting}
                  value={editedAdapterSettings[setting.key]}
                  onChange={(v) => setEditedAdapterSettings({ ...editedAdapterSettings, [setting.key]: v })}
                  existingItems={existingItems}
                />
              ))}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg divide-y">
              {Object.entries(item.adapter_settings).map(([key, value]) => (
                <div key={key} className="px-4 py-3 flex justify-between">
                  <span className="text-sm text-gray-600">{key}</span>
                  <span className="text-sm font-medium text-gray-900">{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(Object.keys(item.host_settings).length > 0 || isEditing) && itemType && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Host Settings</h3>
          {isEditing ? (
            <div className="space-y-4 bg-gray-50 rounded-lg p-4">
              {itemType.host_settings.map((setting) => (
                <SettingField
                  key={setting.key}
                  setting={setting}
                  value={editedHostSettings[setting.key]}
                  onChange={(v) => setEditedHostSettings({ ...editedHostSettings, [setting.key]: v })}
                  existingItems={existingItems}
                />
              ))}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg divide-y">
              {Object.entries(item.host_settings).map(([key, value]) => (
                <div key={key} className="px-4 py-3 flex justify-between">
                  <span className="text-sm text-gray-600">{key}</span>
                  <span className="text-sm font-medium text-gray-900 max-w-xs truncate">{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {item.metrics && (
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-3">Runtime Metrics</h3>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(item.metrics).map(([key, value]) => {
              const isMessageMetric = key.includes('messages');
              const numValue = Number(value);
              return (
                <div 
                  key={key} 
                  className={`bg-blue-50 rounded-lg p-4 ${isMessageMetric && numValue > 0 ? 'cursor-pointer hover:bg-blue-100 transition-colors' : ''}`}
                  onClick={() => {
                    if (isMessageMetric && numValue > 0) {
                      window.location.href = `/messages?project=${projectId}&item=${item.name}`;
                    }
                  }}
                  title={isMessageMetric && numValue > 0 ? 'Click to view messages' : undefined}
                >
                  <p className="text-xs font-medium text-blue-600 uppercase">{key.replace(/_/g, ' ')}</p>
                  <p className={`mt-1 text-lg font-semibold text-blue-900 ${isMessageMetric && numValue > 0 ? 'underline' : ''}`}>{String(value)}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Enhanced Test Message Modal */}
      {showTestModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">HL7 Message Tester</h3>
                <p className="text-sm text-gray-500">Send test messages to {item.name}</p>
              </div>
              <button
                onClick={() => { setShowTestModal(false); setTestResult(null); }}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="p-6 space-y-6 overflow-y-auto max-h-[70vh]">
              {/* Message Editor */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-gray-700">Message to Send</h4>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setTestMessage(generateDefaultHL7Message())}
                      className="px-2 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100"
                    >
                      Reset to Default
                    </button>
                    <span className="px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded">
                      HL7 v2.4
                    </span>
                  </div>
                </div>
                <textarea
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  className="w-full h-40 p-3 font-mono text-sm bg-gray-900 text-green-400 rounded-lg border border-gray-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                  placeholder="Enter HL7 message..."
                  spellCheck={false}
                />
                <p className="mt-1 text-xs text-gray-500">
                  Use \r or newlines to separate segments. Remote: {String(item.adapter_settings?.ipAddress || 'localhost')}:{String(item.adapter_settings?.port || '2575')}
                </p>
              </div>

              {/* Send Button */}
              <div className="flex justify-center">
                <button
                  onClick={() => handleTest()}
                  disabled={isTesting || !testMessage.trim()}
                  className="px-6 py-2.5 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isTesting ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Sending...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                      Send Message
                    </>
                  )}
                </button>
              </div>

              {/* Results Section */}
              {testResult && (
                <div className="space-y-4 pt-4 border-t border-gray-200">
                  {/* Status Badge */}
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1.5 text-sm font-medium rounded-full ${
                      testResult.status === 'sent' 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {testResult.status === 'sent' ? '✓ Message Sent Successfully' : '✗ Send Failed'}
                    </span>
                    {testResult.status === 'sent' && (
                      <span className="text-sm text-gray-500">
                        Response received from remote system
                      </span>
                    )}
                  </div>

                  {/* Sent Message Preview */}
                  {sentMessage && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                        <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
                        </svg>
                        Sent Message
                      </h4>
                      <div className="bg-gray-900 p-4 rounded-lg text-sm font-mono overflow-x-auto">
                        {formatHL7Display(sentMessage)}
                      </div>
                    </div>
                  )}

                  {/* ACK Response */}
                  {testResult.ack && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
                        </svg>
                        ACK Response
                        {testResult.ack.includes('MSA|CA') && (
                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded">Commit Accept</span>
                        )}
                        {testResult.ack.includes('MSA|AA') && (
                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded">Application Accept</span>
                        )}
                        {testResult.ack.includes('MSA|CR') && (
                          <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded">Commit Reject</span>
                        )}
                        {testResult.ack.includes('MSA|AR') && (
                          <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded">Application Reject</span>
                        )}
                        {testResult.ack.includes('MSA|AE') && (
                          <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded">Application Error</span>
                        )}
                      </h4>
                      <div className="bg-gray-900 p-4 rounded-lg text-sm font-mono overflow-x-auto">
                        {formatHL7Display(testResult.ack)}
                      </div>
                    </div>
                  )}

                  {/* Error Display */}
                  {testResult.error && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                      <div className="flex items-start gap-3">
                        <svg className="w-5 h-5 text-red-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div>
                          <h4 className="text-sm font-medium text-red-700">Error</h4>
                          <p className="text-sm text-red-600 mt-1">{testResult.error}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center bg-gray-50">
              <div className="text-xs text-gray-500">
                Protocol: MLLP/TCP • Format: HL7 v2.x
              </div>
              <button
                onClick={() => { setShowTestModal(false); setTestResult(null); }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface ConnectionsPanelProps {
  connections: Connection[];
  items: ProjectItem[];
  projectId: string;
  onUpdate: () => void;
  onDelete: (id: string) => void;
}

function ConnectionsPanel({ connections, items, projectId, onUpdate, onDelete }: ConnectionsPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  
  const getItemName = (id: string) => items.find(i => i.id === id)?.name || 'Unknown';

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Connections</h2>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Connection
        </button>
      </div>

      {connections.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed">
          <p className="text-gray-500">No connections defined</p>
          <p className="text-sm text-gray-400 mt-1">Connect items to define message flow</p>
        </div>
      ) : (
        <div className="space-y-2">
          {connections.map((conn) => (
            <div key={conn.id} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex-1 flex items-center gap-3">
                <span className="font-medium text-gray-900">{getItemName(conn.source_item_id)}</span>
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
                <span className="font-medium text-gray-900">{getItemName(conn.target_item_id)}</span>
              </div>
              <span className={`px-2 py-0.5 text-xs rounded ${
                conn.connection_type === 'error' ? 'bg-red-100 text-red-700' :
                conn.connection_type === 'async' ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {conn.connection_type}
              </span>
              <button
                onClick={() => onDelete(conn.id)}
                className="p-1 text-gray-400 hover:text-red-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <AddConnectionModal
          projectId={projectId}
          items={items}
          onClose={() => setShowAddModal(false)}
          onCreated={() => {
            setShowAddModal(false);
            onUpdate();
          }}
        />
      )}
    </div>
  );
}

function ProjectSettingsPanel({ project }: { project: ProjectDetail }) {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Display Name</label>
            <input
              type="text"
              value={project.display_name}
              readOnly
              className="mt-1 w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-700"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              value={project.description || ''}
              readOnly
              rows={3}
              className="mt-1 w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-700"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-3">Engine Settings</h3>
        <div className="bg-gray-50 rounded-lg divide-y">
          {Object.entries(project.settings).map(([key, value]) => (
            <div key={key} className="px-4 py-3 flex justify-between">
              <span className="text-sm text-gray-600">{key.replace(/_/g, ' ')}</span>
              <span className="text-sm font-medium text-gray-900">{String(value)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface RoutingRulesPanelProps {
  rules: RoutingRule[];
  items: ProjectItem[];
  projectId: string;
  onUpdate: () => void;
}

function RoutingRulesPanel({ rules, items, projectId, onUpdate }: RoutingRulesPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<RoutingRule | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formPriority, setFormPriority] = useState(10);
  const [formEnabled, setFormEnabled] = useState(true);
  const [formCondition, setFormCondition] = useState('');
  const [formAction, setFormAction] = useState<'send' | 'transform' | 'stop' | 'delete'>('send');
  const [formTargets, setFormTargets] = useState<string[]>([]);
  const [formTransform, setFormTransform] = useState('');

  const resetForm = () => {
    setFormName('');
    setFormPriority(10);
    setFormEnabled(true);
    setFormCondition('');
    setFormAction('send');
    setFormTargets([]);
    setFormTransform('');
    setEditingRule(null);
    setError(null);
  };

  const openCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const openEdit = (rule: RoutingRule) => {
    setEditingRule(rule);
    setFormName(rule.name);
    setFormPriority(rule.priority);
    setFormEnabled(rule.enabled);
    setFormCondition(rule.condition_expression || '');
    setFormAction(rule.action);
    setFormTargets(rule.target_items || []);
    setFormTransform(rule.transform_name || '');
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!formName.trim()) return;
    setIsSaving(true);
    setError(null);
    try {
      const data: RoutingRuleCreate = {
        name: formName,
        priority: formPriority,
        enabled: formEnabled,
        condition_expression: formCondition || undefined,
        action: formAction,
        target_items: formTargets,
        transform_name: formTransform || undefined,
      };
      if (editingRule) {
        await updateRoutingRule(projectId, editingRule.id, data);
      } else {
        await createRoutingRule(projectId, data);
      }
      setShowForm(false);
      resetForm();
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save routing rule');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (rule: RoutingRule) => {
    if (!confirm(`Delete routing rule "${rule.name}"?`)) return;
    try {
      await deleteRoutingRule(projectId, rule.id);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete routing rule');
    }
  };

  const handleToggleEnabled = async (rule: RoutingRule) => {
    try {
      await updateRoutingRule(projectId, rule.id, { enabled: !rule.enabled });
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle rule');
    }
  };

  const getItemName = (id: string) => items.find(i => i.id === id || i.name === id)?.name || id;

  const sortedRules = [...rules].sort((a, b) => a.priority - b.priority);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Routing Rules</h2>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Rule
        </button>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">×</button>
        </div>
      )}

      {/* Rules List */}
      {sortedRules.length === 0 && !showForm ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed">
          <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <p className="mt-4 text-gray-500">No routing rules defined</p>
          <p className="text-sm text-gray-400 mt-1">Add rules to control how messages are routed between items</p>
          <button
            onClick={openCreate}
            className="mt-4 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
          >
            Create First Rule
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {sortedRules.map((rule) => (
            <div key={rule.id} className={`p-4 rounded-lg border ${rule.enabled ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200 opacity-60'}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                      {rule.priority}
                    </span>
                    <h3 className="text-sm font-semibold text-gray-900">{rule.name}</h3>
                    <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                      rule.action === 'send' ? 'bg-green-100 text-green-700' :
                      rule.action === 'transform' ? 'bg-purple-100 text-purple-700' :
                      rule.action === 'stop' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {rule.action}
                    </span>
                    {!rule.enabled && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-500">disabled</span>
                    )}
                  </div>
                  {rule.condition_expression && (
                    <p className="mt-2 text-xs font-mono text-gray-600 bg-gray-50 px-3 py-1.5 rounded border">
                      {rule.condition_expression}
                    </p>
                  )}
                  {rule.target_items && rule.target_items.length > 0 && (
                    <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                      <span className="text-xs text-gray-500">→</span>
                      {rule.target_items.map((t, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded">
                          {getItemName(t)}
                        </span>
                      ))}
                    </div>
                  )}
                  {rule.transform_name && (
                    <p className="mt-1 text-xs text-gray-500">Transform: <code className="text-purple-600">{rule.transform_name}</code></p>
                  )}
                </div>
                <div className="flex items-center gap-1 ml-4">
                  <button
                    onClick={() => handleToggleEnabled(rule)}
                    className={`p-1.5 rounded ${rule.enabled ? 'text-green-600 hover:bg-green-50' : 'text-gray-400 hover:bg-gray-100'}`}
                    title={rule.enabled ? 'Disable rule' : 'Enable rule'}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      {rule.enabled ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      )}
                    </svg>
                  </button>
                  <button
                    onClick={() => openEdit(rule)}
                    className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                    title="Edit rule"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDelete(rule)}
                    className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                    title="Delete rule"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingRule ? 'Edit Routing Rule' : 'New Routing Rule'}
              </h2>
              <button onClick={() => { setShowForm(false); resetForm(); }} className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto">
              {error && (
                <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700">Rule Name *</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. ADT_to_EPR"
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Priority</label>
                  <input
                    type="number"
                    min={1}
                    max={999}
                    value={formPriority}
                    onChange={(e) => setFormPriority(Number(e.target.value))}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-400">Lower = evaluated first</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Action *</label>
                  <select
                    value={formAction}
                    onChange={(e) => setFormAction(e.target.value as typeof formAction)}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="send">Send</option>
                    <option value="transform">Transform</option>
                    <option value="stop">Stop (discard)</option>
                    <option value="delete">Delete</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Condition Expression</label>
                <textarea
                  value={formCondition}
                  onChange={(e) => setFormCondition(e.target.value)}
                  placeholder='e.g. HL7.MSH:MessageType.MessageCode = "ADT" AND HL7.MSH:MessageType.TriggerEvent IN ("A01","A02","A03")'
                  rows={3}
                  className="mt-1 w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-400">HL7 field-based condition. Leave empty to match all messages.</p>
              </div>

              {(formAction === 'send' || formAction === 'transform') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Target Items</label>
                  <div className="mt-1 space-y-1 max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-2">
                    {items.filter(i => i.item_type === 'process' || i.item_type === 'operation').map((item) => (
                      <label key={item.id} className="flex items-center gap-2 px-2 py-1 hover:bg-gray-50 rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formTargets.includes(item.name)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormTargets([...formTargets, item.name]);
                            } else {
                              setFormTargets(formTargets.filter(t => t !== item.name));
                            }
                          }}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                        />
                        <span className="text-sm text-gray-700">{item.name}</span>
                        <span className="text-xs text-gray-400 capitalize">({item.item_type})</span>
                      </label>
                    ))}
                    {items.filter(i => i.item_type === 'process' || i.item_type === 'operation').length === 0 && (
                      <p className="text-xs text-gray-400 px-2 py-1">No process or operation items available</p>
                    )}
                  </div>
                </div>
              )}

              {formAction === 'transform' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Transform Name</label>
                  <input
                    type="text"
                    value={formTransform}
                    onChange={(e) => setFormTransform(e.target.value)}
                    placeholder="e.g. custom.sth.v23_to_v251_RIS"
                    className="mt-1 w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="rule-enabled"
                  checked={formEnabled}
                  onChange={(e) => setFormEnabled(e.target.checked)}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                />
                <label htmlFor="rule-enabled" className="text-sm text-gray-700">Enabled</label>
              </div>
            </div>

            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => { setShowForm(false); resetForm(); }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={isSaving || !formName.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : editingRule ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface AddItemModalProps {
  projectId: string;
  itemTypes: ItemTypeDefinition[];
  existingItems: ProjectItem[];
  onClose: () => void;
  onCreated: () => void;
}

function AddItemModal({ projectId, itemTypes, existingItems, onClose, onCreated }: AddItemModalProps) {
  const [step, setStep] = useState<'select' | 'configure'>('select');
  const [selectedType, setSelectedType] = useState<ItemTypeDefinition | null>(null);
  const [name, setName] = useState('');
  const [adapterSettings, setAdapterSettings] = useState<Record<string, unknown>>({});
  const [hostSettings, setHostSettings] = useState<Record<string, unknown>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectType = (type: ItemTypeDefinition) => {
    setSelectedType(type);
    // Initialize default values
    const adapterDefaults: Record<string, unknown> = {};
    type.adapter_settings.forEach(s => {
      if (s.default !== undefined) adapterDefaults[s.key] = s.default;
    });
    const hostDefaults: Record<string, unknown> = {};
    type.host_settings.forEach(s => {
      if (s.default !== undefined) hostDefaults[s.key] = s.default;
    });
    setAdapterSettings(adapterDefaults);
    setHostSettings(hostDefaults);
    setStep('configure');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedType || !name) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const data: ItemCreate = {
        name,
        item_type: selectedType.category,
        class_name: selectedType.li_class_name,
        adapter_settings: adapterSettings,
        host_settings: hostSettings,
      };
      await createItem(projectId, data);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create item');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">
            {step === 'select' ? 'Select Item Type' : `Configure ${selectedType?.name}`}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {step === 'select' ? (
          <div className="p-6 overflow-y-auto">
            <div className="grid grid-cols-1 gap-3">
              {(['service', 'process', 'operation'] as const).map((category) => {
                const catTypes = itemTypes.filter(t => t.category === category);
                const builtIn = catTypes.filter(t => !t.li_class_name.startsWith('custom.'));
                const custom = catTypes.filter(t => t.li_class_name.startsWith('custom.'));
                return (
                <div key={category}>
                  <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">{category}s</h3>
                  <div className="space-y-2">
                    {builtIn.map((type) => (
                      <button
                        key={type.type}
                        onClick={() => handleSelectType(type)}
                        className="w-full text-left p-4 border rounded-lg hover:border-blue-300 hover:bg-blue-50"
                      >
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900">{type.name}</p>
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600">core</span>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                        <code className="text-[11px] text-gray-400 mt-1 block">{type.li_class_name}</code>
                      </button>
                    ))}
                    {custom.length > 0 && builtIn.length > 0 && (
                      <div className="border-t border-dashed border-gray-200 my-2 pt-1">
                        <span className="text-[10px] font-medium text-emerald-600 uppercase">Custom Extensions</span>
                      </div>
                    )}
                    {custom.map((type) => (
                      <button
                        key={type.type}
                        onClick={() => handleSelectType(type)}
                        className="w-full text-left p-4 border border-emerald-200 rounded-lg hover:border-emerald-400 hover:bg-emerald-50"
                      >
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900">{type.name}</p>
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-700">custom</span>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                        <code className="text-[11px] text-emerald-600 mt-1 block">{type.li_class_name}</code>
                      </button>
                    ))}
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {error && (
                <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Item Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., HL7.In.PAS"
                  required
                />
              </div>

              {selectedType && selectedType.adapter_settings.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-900 mb-3">Adapter Settings</h3>
                  <div className="space-y-4">
                    {selectedType.adapter_settings.map((setting) => (
                      <SettingField
                        key={setting.key}
                        setting={setting}
                        value={adapterSettings[setting.key]}
                        onChange={(v) => setAdapterSettings({ ...adapterSettings, [setting.key]: v })}
                        existingItems={existingItems}
                      />
                    ))}
                  </div>
                </div>
              )}

              {selectedType && selectedType.host_settings.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-900 mb-3">Host Settings</h3>
                  <div className="space-y-4">
                    {selectedType.host_settings.map((setting) => (
                      <SettingField
                        key={setting.key}
                        setting={setting}
                        value={hostSettings[setting.key]}
                        onChange={(v) => setHostSettings({ ...hostSettings, [setting.key]: v })}
                        existingItems={existingItems}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between gap-3 px-6 py-4 border-t bg-gray-50">
              <button
                type="button"
                onClick={() => setStep('select')}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                ← Back
              </button>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !name}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Create Item'}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

interface SettingFieldProps {
  setting: {
    key: string;
    label: string;
    type: string;
    required: boolean;
    default?: unknown;
    options?: { value: string; label: string }[];
    description?: string;
  };
  value: unknown;
  onChange: (value: unknown) => void;
  existingItems: ProjectItem[];
}

function SettingField({ setting, value, onChange, existingItems }: SettingFieldProps) {
  if (setting.type === 'boolean') {
    return (
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id={setting.key}
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 text-blue-600 border-gray-300 rounded"
        />
        <label htmlFor={setting.key} className="text-sm text-gray-700">
          {setting.label}
          {setting.description && <span className="text-gray-400 ml-1">- {setting.description}</span>}
        </label>
      </div>
    );
  }

  if (setting.type === 'select') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {setting.label} {setting.required && '*'}
        </label>
        <select
          value={String(value || '')}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          required={setting.required}
        >
          <option value="">Select...</option>
          {setting.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        {setting.description && <p className="mt-1 text-xs text-gray-500">{setting.description}</p>}
      </div>
    );
  }

  if (setting.type === 'multiselect' && setting.key === 'targetConfigNames') {
    const selectedTargets = String(value || '').split(',').filter(Boolean);
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {setting.label}
          <span className="text-gray-400 font-normal ml-1">(optional)</span>
        </label>
        {existingItems.length > 0 ? (
          <div className="border border-gray-300 rounded-lg p-2 max-h-40 overflow-y-auto">
            {existingItems.map((item) => (
              <label key={item.id} className="flex items-center gap-2 p-1 hover:bg-gray-50 rounded cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedTargets.includes(item.name)}
                  onChange={(e) => {
                    const newTargets = e.target.checked
                      ? [...selectedTargets, item.name]
                      : selectedTargets.filter(t => t !== item.name);
                    onChange(newTargets.join(','));
                  }}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                />
                <span className="text-sm text-gray-700">{item.name}</span>
              </label>
            ))}
          </div>
        ) : (
          <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
            <p className="text-sm text-gray-500">No other items in project yet. You can configure targets after creating more items.</p>
          </div>
        )}
        {setting.description && <p className="mt-1 text-xs text-gray-500">{setting.description}</p>}
      </div>
    );
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {setting.label} {setting.required && '*'}
      </label>
      <input
        type={setting.type === 'number' ? 'number' : 'text'}
        value={String(value ?? '')}
        onChange={(e) => onChange(setting.type === 'number' ? Number(e.target.value) : e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        required={setting.required}
      />
      {setting.description && <p className="mt-1 text-xs text-gray-500">{setting.description}</p>}
    </div>
  );
}

interface AddConnectionModalProps {
  projectId: string;
  items: ProjectItem[];
  onClose: () => void;
  onCreated: () => void;
}

function AddConnectionModal({ projectId, items, onClose, onCreated }: AddConnectionModalProps) {
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [connectionType, setConnectionType] = useState<'standard' | 'error' | 'async'>('standard');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceId || !targetId) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await createConnection(projectId, {
        source_item_id: sourceId,
        target_item_id: targetId,
        connection_type: connectionType,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create connection');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Add Connection</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source Item *</label>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              required
            >
              <option value="">Select source...</option>
              {items.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Item *</label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              required
            >
              <option value="">Select target...</option>
              {items.filter(i => i.id !== sourceId).map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Connection Type</label>
            <select
              value={connectionType}
              onChange={(e) => setConnectionType(e.target.value as 'standard' | 'error' | 'async')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="standard">Standard</option>
              <option value="error">Error</option>
              <option value="async">Async</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !sourceId || !targetId}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Creating...' : 'Create Connection'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
