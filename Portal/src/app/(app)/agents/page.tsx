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
import { Bot, Play, Square, RotateCcw, ChevronDown, ChevronRight, Terminal, FileCode, Loader2, Send, Sparkles, Upload, Download } from "lucide-react";
import { useAppContext } from "@/contexts/AppContext";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import { listProjects, type Project } from "@/lib/api-v2";

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
  const [viewMode, setViewMode] = useState<"transcript" | "raw">("transcript");
  const [streamingText, setStreamingText] = useState("");
  const [activeToolCall, setActiveToolCall] = useState<{ name: string; input?: any } | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

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

  // Build transcript from events
  const transcript = useMemo(() => {
    const messages: TranscriptMessage[] = [];
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
  }, [events]);

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

      // Step 1: Create or reuse a thread
      let currentThreadId = threadId;
      if (!currentThreadId) {
        const threadRes = await fetch(`${apiBase}/threads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
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

      // Step 2: Create a run
      const runRes = await fetch(`${apiBase}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
            Instruct HIE route implementations in plain English via GenAI agents.
          </p>
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

          {/* Prompt Manager */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <a
              href="/prompts"
              className="flex items-center gap-2 text-sm text-nhs-blue dark:text-nhs-light-blue hover:underline"
            >
              <Sparkles className="h-4 w-4" />
              Prompt Manager
            </a>
          </div>

          {/* Upload/Download */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Project Files</h3>
            <div className="space-y-2">
              <button
                disabled
                className="w-full flex items-center gap-2 px-3 py-2 text-xs border border-gray-200 dark:border-zinc-600 rounded-md text-gray-400 dark:text-gray-500 cursor-not-allowed"
                title="Coming soon"
              >
                <Upload className="h-4 w-4" />
                Upload Folder/Files
              </button>
              <button
                disabled
                className="w-full flex items-center gap-2 px-3 py-2 text-xs border border-gray-200 dark:border-zinc-600 rounded-md text-gray-400 dark:text-gray-500 cursor-not-allowed"
                title="Coming soon"
              >
                <Download className="h-4 w-4" />
                Download Project Files
              </button>
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
                  <div className="flex items-center justify-center h-full min-h-[300px]">
                    <div className="text-center">
                      <Bot className="h-16 w-16 mx-auto text-gray-300 dark:text-zinc-600 mb-4" />
                      <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        HIE Agent Console
                      </h2>
                      <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                        Describe your integration needs in plain English. The agent will configure
                        HIE routes, items, and connections for you.
                      </p>
                    </div>
                  </div>
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
            ) : (
              <pre className="text-xs font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {events.map((e) => `${new Date(e.at).toISOString()} ${JSON.stringify(e.data, null, 2)}`).join("\n\n")}
              </pre>
            )}
          </div>

          {/* Prompt Input */}
          <div className="border-t border-gray-200 dark:border-zinc-700 p-4">
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
