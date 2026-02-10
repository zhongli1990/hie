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
import { Bot, Play, Square, RotateCcw, ChevronDown, ChevronRight, Terminal, FileCode, Loader2, Send, Sparkles } from "lucide-react";

type RunnerType = "claude" | "codex" | "gemini" | "custom";

const RUNNERS = [
  { value: "claude", label: "Claude Agent (Anthropic)", available: true },
  { value: "codex", label: "OpenAI Codex Agent", available: true },
  { value: "gemini", label: "Gemini Agent (Google)", available: false },
  { value: "custom", label: "Custom Agent", available: false },
] as const;

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

// HIE-specific context types
type HIEWorkspace = {
  id: string;
  name: string;
  display_name: string;
};

type HIEProject = {
  id: string;
  name: string;
  workspace_id: string;
  status: string;
  items_count: number;
};

export default function AgentsPage() {
  const [workspaces, setWorkspaces] = useState<HIEWorkspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [projects, setProjects] = useState<HIEProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [runnerType, setRunnerType] = useState<RunnerType>("claude");
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<string>("idle");
  const [events, setEvents] = useState<EventLine[]>([]);
  const [viewMode, setViewMode] = useState<"transcript" | "raw">("transcript");
  const [streamingText, setStreamingText] = useState("");
  const [activeToolCall, setActiveToolCall] = useState<{ name: string; input?: any } | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Fetch workspaces from HIE Manager API
  const fetchWorkspaces = useCallback(async () => {
    try {
      const r = await fetch("/api/workspaces");
      if (r.ok) {
        const data = await r.json();
        setWorkspaces(data.items || data || []);
      }
    } catch (e) {
      console.error("Failed to fetch workspaces:", e);
    }
  }, []);

  // Fetch projects for selected workspace
  const fetchProjects = useCallback(async (wsId: string) => {
    try {
      const r = await fetch(`/api/workspaces/${wsId}/projects`);
      if (r.ok) {
        const data = await r.json();
        setProjects(data.items || data || []);
      }
    } catch (e) {
      console.error("Failed to fetch projects:", e);
    }
  }, []);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  useEffect(() => {
    if (selectedWorkspaceId) {
      fetchProjects(selectedWorkspaceId);
      setSelectedProjectId(null);
    }
  }, [selectedWorkspaceId, fetchProjects]);

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

  // Placeholder for running prompts - will connect to backend agent runners
  async function onRunPrompt() {
    if (!prompt.trim()) return;
    setStatus("running");
    setEvents([]);
    setStreamingText("");
    setActiveToolCall(null);

    // Add user message to events
    setEvents([{ at: Date.now(), data: { type: "ui.message.user", payload: { text: prompt } } }]);

    // Build HIE context for the agent
    const hieContext = {
      workspace_id: selectedWorkspaceId,
      project_id: selectedProjectId,
      workspace: workspaces.find(w => w.id === selectedWorkspaceId),
      project: projects.find(p => p.id === selectedProjectId),
    };

    try {
      // TODO: Connect to actual agent runner backend
      // For now, simulate a response showing the architecture is ready
      await new Promise(resolve => setTimeout(resolve, 1500));

      const assistantResponse = selectedProjectId
        ? `I understand you want to work on project "${projects.find(p => p.id === selectedProjectId)?.name || selectedProjectId}" in workspace "${workspaces.find(w => w.id === selectedWorkspaceId)?.display_name || selectedWorkspaceId}".

**Your request:** ${prompt}

I'm ready to help you configure HIE routes, items, and integrations. Here's what I can do:

- **Create/modify routes** - Define message flows between services, processes, and operations
- **Configure items** - Set up HL7 receivers, MLLP senders, HTTP endpoints, file watchers
- **Build routing rules** - Content-based routing with HL7 field conditions
- **Deploy & test** - Deploy configurations and send test messages
- **Troubleshoot** - Analyze message flows, check connectivity, debug errors

The agent runner backend is being connected. Once live, I'll be able to directly modify your HIE configuration through natural language instructions.`
        : `Please select a workspace and project first, then I can help you configure HIE integrations through natural language.

**Available actions:**
- Select a workspace from the dropdown above
- Choose a project to work on
- Then describe what integration you need in plain English

For example: *"Create an HL7 ADT receiver on port 10001 that routes A01 messages to the PAS MLLP sender"*`;

      setEvents(prev => [
        ...prev,
        { at: Date.now(), data: { type: "ui.message.assistant.final", payload: { text: assistantResponse } } },
      ]);
      setStatus("completed");
    } catch (e) {
      setStatus(`error: ${e instanceof Error ? e.message : "Unknown error"}`);
    }
  }

  const selectedWorkspace = workspaces.find(w => w.id === selectedWorkspaceId);
  const selectedProject = projects.find(p => p.id === selectedProjectId);

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
          {/* Workspace Selector */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">Workspace</label>
            <select
              value={selectedWorkspaceId || ""}
              onChange={(e) => setSelectedWorkspaceId(e.target.value || null)}
              className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
            >
              <option value="">Select workspace...</option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>{w.display_name || w.name}</option>
              ))}
            </select>
          </div>

          {/* Project Selector */}
          {selectedWorkspaceId && (
            <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">Project</label>
              <select
                value={selectedProjectId || ""}
                onChange={(e) => setSelectedProjectId(e.target.value || null)}
                className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option value="">Select project...</option>
                {projects.map((p) => (
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
              onChange={(e) => setRunnerType(e.target.value as RunnerType)}
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
                <div><span className="font-medium">Workspace:</span> {selectedWorkspace?.display_name}</div>
                <div><span className="font-medium">Project:</span> {selectedProject.name}</div>
                <div><span className="font-medium">Status:</span> {selectedProject.status || "configured"}</div>
                <div><span className="font-medium">Items:</span> {selectedProject.items_count || 0}</div>
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 shadow-sm">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Quick Prompts</h3>
            <div className="space-y-2">
              {[
                "Create an HL7 ADT receiver on port 10001",
                "Add an MLLP sender to PAS system",
                "Route A01 messages to the EPR",
                "Show me the current route configuration",
                "Test the HL7 connectivity end-to-end",
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => setPrompt(q)}
                  className="w-full text-left text-xs px-3 py-2 rounded-md border border-gray-200 dark:border-zinc-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
                >
                  <Sparkles className="h-3 w-3 inline mr-1.5 text-nhs-blue" />
                  {q}
                </button>
              ))}
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
