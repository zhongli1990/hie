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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Play, Square, RotateCcw, ChevronDown, ChevronRight, Terminal, FileCode, Loader2, Send, Sparkles, Upload, Download, FolderOpen, File, Eye, ArrowLeft, X, ShieldCheck, Zap } from "lucide-react";
import { useAppContext } from "@/contexts/AppContext";
import { useAuth } from "@/contexts/AuthContext";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import { listProjects, type Project } from "@/lib/api-v2";
import { getToken } from "@/lib/auth";
import QuickStartPanel, {
  mapPortalRoleToAgentRole,
  ROLE_DISPLAY,
  type AgentRole,
} from "@/components/AgentWorkflows/QuickStartPanel";

type RunnerType = "claude" | "codex" | "gemini" | "azure" | "bedrock" | "openli" | "custom";

const RUNNERS = [
  { value: "claude", label: "Claude Agent (Anthropic)", available: true },
  { value: "codex", label: "OpenAI Agent (Codex)", available: true },
  { value: "gemini", label: "Gemini Agent (Google)", available: false },
  { value: "azure", label: "Azure OpenAI", available: false },
  { value: "bedrock", label: "AWS Bedrock", available: false },
  { value: "openli", label: "OpenLI Agent", available: false },
  { value: "custom", label: "Custom Agent", available: false },
] as const;

/** Map runner type to the correct proxy API base path */
function getRunnerApiBase(runner: RunnerType): string {
  if (runner === "codex") return "/api/codex-runner";
  return "/api/agent-runner";
}

type TranscriptMessage = {
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  toolName?: string;
  toolInput?: any;
  toolOutput?: any;
  timestamp?: number;
};

type EventLine = {
  at: number;
  data: any;
};

export default function AgentsPage() {
  // Get workspace from global WorkspaceContext
  const { currentWorkspace } = useWorkspace();

  // Derive agent-runner role from Portal auth
  const { user } = useAuth();
  const agentRole: AgentRole = mapPortalRoleToAgentRole(user?.role_name);
  const roleDisplay = ROLE_DISPLAY[agentRole];

  // Use AppContext for session persistence
  const {
    sessions,
    selectedSessionId,
    setSelectedSessionId,
    runnerType,
    setRunnerType,
    agentMessages,
    setAgentMessages,
    agentStatus,
    setAgentStatus,
    fetchSessions,
    fetchAgentMessages,
    createSession,
    persistMessage,
  } = useAppContext();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [events, setEvents] = useState<EventLine[]>([]);
  const [viewMode, setViewMode] = useState<"transcript" | "raw" | "files">("transcript");
  const [streamingText, setStreamingText] = useState("");
  const [activeToolCall, setActiveToolCall] = useState<{ name: string; input?: any } | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [fileItems, setFileItems] = useState<{ name: string; path: string; type: "file" | "directory"; size: number | null; modified_at: string }[]>([]);
  const [currentFilePath, setCurrentFilePath] = useState("/");
  const [parentFilePath, setParentFilePath] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [viewingFile, setViewingFile] = useState<{ name: string; content: string } | null>(null);

  // Use agentStatus from context as primary status
  const status = agentStatus;

  // Pick up prefilled prompt from Prompts page
  useEffect(() => {
    const prefill = sessionStorage.getItem("prefill-prompt");
    if (prefill) {
      setPrompt(prefill);
      sessionStorage.removeItem("prefill-prompt");
    }
  }, []);

  // Load sessions when workspace changes
  useEffect(() => {
    if (currentWorkspace) {
      fetchSessions();
    }
  }, [currentWorkspace, fetchSessions]);

  // Load messages when session changes
  useEffect(() => {
    if (selectedSessionId) {
      fetchAgentMessages(selectedSessionId);
      setEvents([]); // Clear local events when loading from session
      setStreamingText("");
      setActiveToolCall(null);
    }
  }, [selectedSessionId, fetchAgentMessages]);

  // Fetch projects for selected workspace using api-v2
  useEffect(() => {
    if (!currentWorkspace?.id) {
      setProjects([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await listProjects(currentWorkspace.id);
        if (!cancelled) {
          setProjects(data.projects || []);
        }
      } catch (e) {
        console.error("Failed to fetch projects:", e);
        if (!cancelled) setProjects([]);
      }
    })();
    return () => { cancelled = true; };
  }, [currentWorkspace?.id]);

  // Build transcript from agentMessages (DB) + events (current run)
  const transcript = useMemo(() => {
    const messages: TranscriptMessage[] = [];

    // First, add messages from database (historical messages)
    for (const msg of agentMessages) {
      if (msg.role === "user" || msg.role === "assistant") {
        messages.push({
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at).getTime(),
        });
      } else if (msg.role === "tool" && msg.metadata) {
        messages.push({
          role: "tool",
          content: `Tool: ${msg.metadata.tool_name || "tool"}`,
          toolName: msg.metadata.tool_name,
          toolInput: msg.metadata.tool_input,
          toolOutput: msg.metadata.tool_output,
          timestamp: new Date(msg.created_at).getTime(),
        });
      } else if (msg.role === "system") {
        messages.push({
          role: "system",
          content: msg.content,
          timestamp: new Date(msg.created_at).getTime(),
        });
      }
    }

    // Then, add events from current run (if any)
    let currentAssistantText = "";
    for (const event of events) {
      const data = event.data;
      if (!data || typeof data !== "object") continue;
      const eventType = data.type || "";

      // Claude runner events
      if (eventType === "ui.message.user") {
        messages.push({ role: "user", content: data.payload?.text || "", timestamp: event.at });
      } else if (eventType === "ui.message.assistant.delta") {
        currentAssistantText += data.payload?.textDelta || "";
      } else if (eventType === "ui.message.assistant.final") {
        messages.push({ role: "assistant", content: data.payload?.text || currentAssistantText, timestamp: event.at });
        currentAssistantText = "";
      } else if (eventType === "ui.tool.call" || eventType === "ui.tool.call.start") {
        messages.push({
          role: "tool",
          content: `Calling ${data.payload?.toolName}`,
          toolName: data.payload?.toolName,
          toolInput: data.payload?.input,
          timestamp: event.at,
        });
      } else if (eventType === "ui.tool.result") {
        messages.push({
          role: "tool",
          content: `Result from ${data.payload?.toolName}`,
          toolName: data.payload?.toolName,
          toolOutput: data.payload?.output,
          timestamp: event.at,
        });
      }

      // Codex runner events
      if (eventType === "item.completed" && data.item) {
        const item = data.item;
        if (item.type === "command_execution") {
          messages.push({
            role: "tool",
            content: item.status === "completed" ? "Command executed" : "Command failed",
            toolName: "shell",
            toolInput: item.command,
            toolOutput: item.aggregated_output || `Exit code: ${item.exit_code}`,
            timestamp: event.at,
          });
        } else if (item.type === "agent_message" || item.text) {
          messages.push({ role: "assistant", content: item.text || "", timestamp: event.at });
        }
      }
    }

    if (currentAssistantText) {
      messages.push({ role: "assistant", content: currentAssistantText });
    }

    return messages;
  }, [agentMessages, events]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript, streamingText]);

  // Create a new session
  async function handleNewSession() {
    if (!currentWorkspace) {
      alert("Please select a workspace first");
      return;
    }
    const sessionId = await createSession(
      selectedProjectId,
      runnerType,
      `${runnerType.charAt(0).toUpperCase() + runnerType.slice(1)} Session`
    );
    if (sessionId) {
      setSelectedSessionId(sessionId);
      setEvents([]);
      setThreadId(null);
      setStreamingText("");
      setActiveToolCall(null);
      setAgentStatus("idle");
    }
  }

  // Connect to agent-runner backend with SSE streaming
  async function onRunPrompt() {
    if (!prompt.trim()) return;

    // Create session if none selected
    let currentSessionId = selectedSessionId;
    if (!currentSessionId) {
      if (!currentWorkspace) {
        alert("Please select a workspace first");
        return;
      }
      currentSessionId = await createSession(
        selectedProjectId,
        runnerType,
        `${runnerType.charAt(0).toUpperCase() + runnerType.slice(1)} Session`
      );
      if (!currentSessionId) {
        alert("Failed to create session");
        return;
      }
      setSelectedSessionId(currentSessionId);
    }

    setAgentStatus("running");
    setEvents([]);
    setStreamingText("");
    setActiveToolCall(null);

    const userPrompt = prompt;
    setPrompt("");

    // Persist user message to database
    await persistMessage(currentSessionId, "user", userPrompt);

    // Add user message to events immediately
    setEvents([{ at: Date.now(), data: { type: "ui.message.user", payload: { text: userPrompt } } }]);

    try {
      const apiBase = getRunnerApiBase(runnerType);

      // Attach JWT for role-based access control in agent-runner
      const authToken = getToken();
      const authHeaders: Record<string, string> = {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      };

      // Step 1: Create or reuse a thread
      let currentThreadId = threadId;
      if (!currentThreadId) {
        const threadRes = await fetch(`${apiBase}/threads`, {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify({
            workspaceId: currentWorkspace!.id,
            workspaceName: currentWorkspace!.name || "default",
            projectId: selectedProjectId || undefined,
            runnerType,
            skipGitRepoCheck: true,
          }),
        });
        if (!threadRes.ok) {
          throw new Error(`Failed to create thread: ${threadRes.statusText}`);
        }
        const threadData = await threadRes.json();
        currentThreadId = threadData.threadId;
        setThreadId(currentThreadId);
      }

      // Step 2: Create a run (with auth header for RBAC)
      const runRes = await fetch(`${apiBase}/runs`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({ threadId: currentThreadId, prompt: userPrompt }),
      });
      if (!runRes.ok) {
        throw new Error(`Failed to create run: ${runRes.statusText}`);
      }
      const runData = await runRes.json();
      const runId = runData.runId;

      // Step 3: Subscribe to SSE events
      const evtSource = new EventSource(`${apiBase}/runs/${runId}/events`);
      eventSourceRef.current = evtSource;

      evtSource.onmessage = (event) => {
        if (!event.data || event.data.trim() === "") return;
        try {
          const parsed = JSON.parse(event.data);
          const eventType = parsed.type || "";

          setEvents((prev) => [...prev, { at: Date.now(), data: parsed }]);

          // Handle streaming text deltas
          if (eventType === "ui.message.assistant.delta") {
            setStreamingText((prev) => prev + (parsed.payload?.textDelta || ""));
          } else if (eventType === "ui.message.assistant.final") {
            const assistantText = parsed.payload?.text || "";
            setStreamingText("");
            // Persist assistant message to database
            if (currentSessionId && assistantText) {
              persistMessage(currentSessionId, "assistant", assistantText, runId);
            }

          // ── Codex runner events ───────────────────────────────────────
          } else if (eventType === "item.completed" && parsed.item) {
            const item = parsed.item;
            if (item.type === "command_execution") {
              // Persist tool message to database
              if (currentSessionId) {
                persistMessage(currentSessionId, "tool",
                  item.status === "completed" ? "Command executed" : "Command failed",
                  runId, {
                    tool_name: "shell",
                    tool_input: item.command,
                    tool_output: item.aggregated_output || `Exit code: ${item.exit_code}`,
                  });
              }
            } else if (item.type === "agent_message" || item.text) {
              setStreamingText("");
              // Persist assistant message to database
              if (currentSessionId && item.text) {
                persistMessage(currentSessionId, "assistant", item.text, runId);
              }
            }
          } else if (eventType === "run.started") {
            // Codex run started
          }

          // Handle tool call indicators
          if (eventType === "ui.tool.call.start") {
            setActiveToolCall({ name: parsed.payload?.toolName || "tool", input: parsed.payload?.input });
          } else if (eventType === "ui.tool.result" || eventType === "ui.tool.blocked") {
            setActiveToolCall(null);
          }

          // Handle completion
          if (eventType === "run.completed" || eventType === "stream.closed") {
            setAgentStatus("completed");
            setStreamingText("");
            setActiveToolCall(null);
            evtSource.close();
            eventSourceRef.current = null;
            // Refresh sessions to update run count
            fetchSessions();
          }

          // Handle errors
          if (eventType === "error") {
            setAgentStatus(`error: ${parsed.message || parsed.payload?.message || "Unknown error"}`);
            setStreamingText("");
            setActiveToolCall(null);
            evtSource.close();
            eventSourceRef.current = null;
          }
        } catch {
          // Ignore unparseable events (e.g. SSE comments)
        }
      };

      evtSource.onerror = () => {
        if (evtSource.readyState === EventSource.CLOSED) {
          if (status === "running") setAgentStatus("completed");
        } else {
          setAgentStatus("error: Connection lost");
        }
        evtSource.close();
        eventSourceRef.current = null;
        setStreamingText("");
        setActiveToolCall(null);
      };
    } catch (e) {
      setAgentStatus(`error: ${e instanceof Error ? e.message : "Unknown error"}`);
    }
  }

  // ─── File Upload/Download ────────────────────────────────────────────────────

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    if (!currentWorkspace || !selectedProjectId) {
      alert("Please select a project first");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }
      formData.append("workspace_id", currentWorkspace.id);
      formData.append("project_id", selectedProjectId);

      const res = await fetch("/api/project-files/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({ error: "Upload failed" }));
        throw new Error(error.error || "Upload failed");
      }

      alert(`Successfully uploaded ${files.length} file(s)`);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleFileDownload() {
    if (!currentWorkspace || !selectedProjectId) {
      alert("Please select a project first");
      return;
    }

    try {
      const res = await fetch(
        `/api/project-files/download?workspace_id=${currentWorkspace.id}&project_id=${selectedProjectId}`
      );

      if (!res.ok) {
        const error = await res.json().catch(() => ({ error: "Download failed" }));
        throw new Error(error.error || "Download failed");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `project-${selectedProjectId}-files.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed");
    }
  }

  // ─── File Browser ──────────────────────────────────────────────────────────

  const fetchFileList = useCallback(async (browsePath: string = "/") => {
    if (!currentWorkspace) return;
    setFileLoading(true);
    try {
      const params = new URLSearchParams({
        workspace_id: currentWorkspace.id,
        path: browsePath,
      });
      if (selectedProjectId) params.set("project_id", selectedProjectId);

      const res = await fetch(`/api/project-files/list?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to list files");
      const data = await res.json();
      setFileItems(data.items || []);
      setCurrentFilePath(data.current_path || "/");
      setParentFilePath(data.parent_path);
    } catch (err) {
      console.error("File list error:", err);
      setFileItems([]);
    } finally {
      setFileLoading(false);
    }
  }, [currentWorkspace, selectedProjectId]);

  async function handleViewFile(filePath: string) {
    if (!currentWorkspace) return;
    try {
      const params = new URLSearchParams({
        workspace_id: currentWorkspace.id,
        path: filePath,
        action: "view",
      });
      if (selectedProjectId) params.set("project_id", selectedProjectId);

      const res = await fetch(`/api/project-files/list?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to view file");
      const data = await res.json();
      if (data.is_binary) {
        alert("Binary file - cannot view in browser");
        return;
      }
      setViewingFile({ name: data.name, content: data.content || "" });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to view file");
    }
  }

  // Load file list when switching to files tab
  useEffect(() => {
    if (viewMode === "files" && currentWorkspace) {
      fetchFileList("/");
    }
  }, [viewMode, currentWorkspace, selectedProjectId, fetchFileList]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  // selectedWorkspace is now currentWorkspace from WorkspaceContext
  const selectedProject = projects.find((p) => p.id === selectedProjectId) || null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Bot className="h-6 w-6" />
            Agent Console
          </h1>
          <p className="mt-1 text-xs md:text-sm text-gray-600 dark:text-gray-400">
            Describe your integration needs in plain English — the GenAI agent builds it for you.
          </p>
        </div>
        {/* Role Badge */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${roleDisplay.bg} ${roleDisplay.color}`}>
          <ShieldCheck className="h-3.5 w-3.5" />
          {roleDisplay.label}
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 h-auto lg:h-[calc(100vh-220px)] min-h-0 lg:min-h-[600px]">
        {/* Controls Panel */}
        <div className="lg:w-80 flex-shrink-0 space-y-4 overflow-y-auto">
          {/* Project Selector */}
          {currentWorkspace && (
            <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">Project</label>
              <select
                value={selectedProjectId || ""}
                onChange={(e) => setSelectedProjectId(e.target.value || null)}
                className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option value="">Select project...</option>
                {Array.isArray(projects) && projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} ({p.items_count || 0} items)</option>
                ))}
              </select>
            </div>
          )}

          {/* Runner Selector */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">Agent Runner</label>
            <select
              value={runnerType}
              onChange={(e) => {
                const newRunner = e.target.value as RunnerType;
                const runner = RUNNERS.find((r) => r.value === newRunner);
                if (runner && !runner.available) {
                  alert(`${runner.label} is coming soon!`);
                  return;
                }
                setRunnerType(newRunner);
                // Clear thread when runner changes (different backend)
                setThreadId(null);
                setEvents([]);
                setAgentStatus("idle");
                setStreamingText("");
                setActiveToolCall(null);
                eventSourceRef.current?.close();
                eventSourceRef.current = null;
              }}
              className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
            >
              {RUNNERS.map((r) => (
                <option key={r.value} value={r.value} disabled={!r.available}>
                  {r.label}{!r.available ? " (Coming Soon)" : ""}
                </option>
              ))}
            </select>
          </div>

          {/* HIE Context Info */}
          {selectedProject && (
            <div className="rounded-lg border border-nhs-light-blue/30 bg-blue-50 dark:bg-zinc-800 p-4 shadow-sm">
              <h3 className="text-sm font-medium text-nhs-blue dark:text-nhs-light-blue mb-2">HIE Context</h3>
              <div className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                <div><span className="font-medium">Workspace:</span> {currentWorkspace?.display_name}</div>
                <div><span className="font-medium">Project:</span> {selectedProject?.name}</div>
                <div><span className="font-medium">Status:</span> {selectedProject?.state || "configured"}</div>
                <div><span className="font-medium">Items:</span> {selectedProject?.items_count || 0}</div>
              </div>
            </div>
          )}

          {/* Capabilities Panel */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5 text-nhs-blue" />
              Your Capabilities
            </h3>
            <div className="space-y-1.5 text-xs text-gray-600 dark:text-gray-400">
              {agentRole === "platform_admin" || agentRole === "tenant_admin" ? (
                <>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Build integrations (custom.* namespace)</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Deploy &amp; manage projects</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Run tests &amp; safety reviews</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> All tools available</div>
                </>
              ) : agentRole === "developer" ? (
                <>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Build integrations (custom.* namespace)</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Run integration tests</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Read/write custom.* files</div>
                  <div className="flex items-center gap-1"><span className="text-amber-500">&#x26A0;</span> Cannot deploy to production</div>
                  <div className="flex items-center gap-1"><span className="text-red-400">&#x2717;</span> Cannot modify li.* / EnsLib.* core</div>
                </>
              ) : agentRole === "clinical_safety_officer" ? (
                <>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Run safety reviews (DCB0129)</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Run integration tests</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> View all configurations</div>
                  <div className="flex items-center gap-1"><span className="text-red-400">&#x2717;</span> Cannot create or modify items</div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> View project status</div>
                  <div className="flex items-center gap-1"><span className="text-green-500">&#x2713;</span> Read configurations</div>
                  <div className="flex items-center gap-1"><span className="text-red-400">&#x2717;</span> Read-only access</div>
                </>
              )}
            </div>
          </div>

          {/* Session History */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">Agent Sessions</h3>
              <button
                onClick={handleNewSession}
                disabled={!currentWorkspace}
                className="px-2 py-1 text-xs bg-nhs-blue text-white rounded hover:bg-nhs-dark-blue disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                + New
              </button>
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {sessions.length === 0 ? (
                <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-4">
                  No sessions yet. Click &quot;+ New&quot; to start.
                </p>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => setSelectedSessionId(session.session_id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-xs transition-colors ${
                      selectedSessionId === session.session_id
                        ? "bg-nhs-blue text-white"
                        : "bg-gray-50 dark:bg-zinc-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-600"
                    }`}
                  >
                    <div className="font-medium truncate">{session.title}</div>
                    <div className="text-xs opacity-75 mt-0.5">
                      {session.runner_type} · {session.run_count || 0} runs
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Main Panel */}
        <div className="flex-1 flex flex-col min-w-0 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 shadow-sm overflow-hidden">
          {/* View Mode Tabs */}
          <div className="flex items-center justify-between border-b border-gray-200 dark:border-zinc-700 px-4 py-2">
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode("transcript")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  viewMode === "transcript"
                    ? "bg-nhs-blue text-white"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-700"
                }`}
              >
                Transcript
              </button>
              <button
                onClick={() => setViewMode("raw")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  viewMode === "raw"
                    ? "bg-nhs-blue text-white"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-700"
                }`}
              >
                Raw Events
              </button>
              <button
                onClick={() => setViewMode("files")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  viewMode === "files"
                    ? "bg-nhs-blue text-white"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-700"
                }`}
              >
                Project Files
              </button>
            </div>
            <div className="flex items-center gap-2">
              {status === "running" && (
                <div className="flex items-center gap-2 text-xs text-nhs-blue">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Agent working...
                </div>
              )}
              {status === "completed" && (
                <span className="text-xs text-green-600 dark:text-green-400">Completed</span>
              )}
              {status.startsWith("error") && (
                <span className="text-xs text-red-600">{status}</span>
              )}
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-4">
            {viewMode === "transcript" ? (
              <div className="space-y-4">
                {transcript.length === 0 && !streamingText && status !== "running" ? (
                  <QuickStartPanel
                    agentRole={agentRole}
                    onSelectTemplate={(tmplPrompt) => {
                      setPrompt(tmplPrompt);
                      // Focus the textarea after selecting a template
                      const textarea = document.querySelector<HTMLTextAreaElement>("textarea");
                      textarea?.focus();
                    }}
                  />
                ) : (
                  <>
                    {transcript.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[85%] rounded-xl px-4 py-3 ${
                            msg.role === "user"
                              ? "bg-nhs-blue text-white"
                              : msg.role === "tool"
                              ? "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200"
                              : msg.role === "system"
                              ? "bg-gray-100 dark:bg-zinc-700 text-gray-600 dark:text-gray-300 text-xs"
                              : "bg-gray-100 dark:bg-zinc-700 text-gray-900 dark:text-white"
                          }`}
                        >
                          {msg.role === "tool" ? (
                            <details className="text-sm">
                              <summary className="cursor-pointer font-medium flex items-center gap-2">
                                <Terminal className="h-3 w-3" />
                                {msg.toolName || "Tool"}
                              </summary>
                              <div className="mt-2 space-y-2">
                                {msg.toolInput && (
                                  <pre className="bg-amber-100 dark:bg-amber-900/30 rounded p-2 text-xs overflow-x-auto font-mono">
                                    {typeof msg.toolInput === "string" ? msg.toolInput : JSON.stringify(msg.toolInput, null, 2)}
                                  </pre>
                                )}
                                {msg.toolOutput && (
                                  <pre className="bg-amber-100 dark:bg-amber-900/30 rounded p-2 text-xs overflow-x-auto font-mono max-h-40">
                                    {typeof msg.toolOutput === "string" ? msg.toolOutput : JSON.stringify(msg.toolOutput, null, 2)}
                                  </pre>
                                )}
                              </div>
                            </details>
                          ) : (
                            <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                          )}
                        </div>
                      </div>
                    ))}
                    {streamingText && (
                      <div className="flex justify-start">
                        <div className="max-w-[85%] rounded-xl px-4 py-3 bg-gray-100 dark:bg-zinc-700 text-gray-900 dark:text-white">
                          <div className="text-sm whitespace-pre-wrap">{streamingText}</div>
                          <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-1" />
                        </div>
                      </div>
                    )}
                    {activeToolCall && (
                      <div className="flex justify-start">
                        <div className="rounded-xl px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                          <div className="flex items-center gap-2 text-sm text-amber-800 dark:text-amber-200">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Running: {activeToolCall.name}
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
                <div ref={transcriptEndRef} />
              </div>
            ) : viewMode === "raw" ? (
              <pre className="text-xs font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {events.map((e) => `${new Date(e.at).toISOString()} ${JSON.stringify(e.data, null, 2)}`).join("\n\n")}
              </pre>
            ) : (
              <div className="space-y-4">
                {/* File Viewer Modal */}
                {viewingFile && (
                  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-zinc-800 rounded-lg w-full max-w-3xl mx-4 max-h-[80vh] flex flex-col border border-gray-200 dark:border-zinc-700">
                      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-zinc-700">
                        <span className="font-medium text-sm text-gray-900 dark:text-white">{viewingFile.name}</span>
                        <button onClick={() => setViewingFile(null)} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <pre className="flex-1 overflow-auto p-4 text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                        {viewingFile.content}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Toolbar */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {parentFilePath !== null && (
                      <button
                        onClick={() => fetchFileList(parentFilePath!)}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-200 dark:border-zinc-600 rounded"
                      >
                        <ArrowLeft className="h-3 w-3" /> Back
                      </button>
                    )}
                    <span className="text-xs text-gray-500 dark:text-gray-400 font-mono truncate max-w-[200px]">
                      {currentFilePath}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      className="hidden"
                      onChange={handleFileUpload}
                    />
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={!currentWorkspace || uploading}
                      className="flex items-center gap-1 px-2 py-1 text-xs border border-gray-200 dark:border-zinc-600 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 disabled:opacity-50"
                    >
                      <Upload className="h-3 w-3" />
                      {uploading ? "..." : "Upload"}
                    </button>
                    <button
                      onClick={handleFileDownload}
                      disabled={!currentWorkspace}
                      className="flex items-center gap-1 px-2 py-1 text-xs border border-gray-200 dark:border-zinc-600 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 disabled:opacity-50"
                    >
                      <Download className="h-3 w-3" /> ZIP
                    </button>
                  </div>
                </div>

                {/* File List */}
                {fileLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                  </div>
                ) : fileItems.length === 0 ? (
                  <div className="text-center py-8">
                    <FolderOpen className="h-10 w-10 mx-auto text-gray-300 dark:text-zinc-600 mb-2" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {currentWorkspace ? "No files yet. Upload files or run an agent to generate them." : "Select a workspace to browse files."}
                    </p>
                  </div>
                ) : (
                  <div className="border border-gray-200 dark:border-zinc-700 rounded-lg overflow-hidden">
                    {fileItems.map((item) => (
                      <div
                        key={item.path}
                        className="flex items-center gap-3 px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-zinc-700/50 border-b border-gray-100 dark:border-zinc-700/50 last:border-b-0 cursor-pointer"
                        onClick={() => {
                          if (item.type === "directory") {
                            fetchFileList(item.path);
                          } else {
                            handleViewFile(item.path);
                          }
                        }}
                      >
                        {item.type === "directory" ? (
                          <FolderOpen className="h-4 w-4 text-amber-500 flex-shrink-0" />
                        ) : (
                          <File className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        )}
                        <span className="flex-1 truncate text-gray-900 dark:text-white">{item.name}</span>
                        {item.size !== null && (
                          <span className="text-xs text-gray-400 flex-shrink-0">
                            {item.size < 1024 ? `${item.size}B` : item.size < 1024 * 1024 ? `${(item.size / 1024).toFixed(1)}KB` : `${(item.size / 1024 / 1024).toFixed(1)}MB`}
                          </span>
                        )}
                        {item.type === "file" && (
                          <Eye className="h-3 w-3 text-gray-400 flex-shrink-0" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Prompt Input */}
          <div className="border-t border-gray-200 dark:border-zinc-700 p-4 space-y-3">
            {/* Prompt Manager Link + Namespace hint */}
            <div className="flex items-center justify-between">
              <a
                href="/prompts"
                className="flex items-center gap-2 text-xs text-nhs-blue dark:text-nhs-light-blue hover:underline"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Open Prompt Manager
              </a>
              {agentRole === "developer" && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  Namespace: <span className="font-mono text-green-600 dark:text-green-400">custom.*</span> only
                </span>
              )}
            </div>

            {/* Input Area */}
            <div className="flex gap-3">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    onRunPrompt();
                  }
                }}
                placeholder="Describe what HIE integration you need... (Enter to send, Shift+Enter for new line)"
                className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-nhs-blue focus:border-transparent"
                rows={2}
                disabled={status === "running"}
              />
              <button
                onClick={onRunPrompt}
                disabled={!prompt.trim() || status === "running"}
                className="px-6 py-3 rounded-lg bg-nhs-blue text-white font-medium hover:bg-nhs-dark-blue disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {status === "running" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
