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

import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { MessagesSquare, Send, Loader2, Plus, Bot, User as UserIcon, Terminal, AlertCircle, Sparkles, Wrench, ShieldAlert, Upload, Download } from "lucide-react";
import { useAppContext } from "@/contexts/AppContext";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import { listProjects, type Project } from "@/lib/api-v2";

type RunnerType = "claude" | "codex" | "gemini" | "azure" | "bedrock" | "openli" | "custom";

function getRunnerApiBase(runner: RunnerType): string {
  if (runner === "codex") return "/api/codex-runner";
  return "/api/agent-runner";
}

function getRunnerLabel(runner: RunnerType): string {
  const labels: Record<string, string> = {
    claude: "Claude (Anthropic)",
    codex: "OpenAI Agent (Codex)",
    gemini: "Gemini",
    azure: "Azure OpenAI",
    bedrock: "AWS Bedrock",
    openli: "OpenLI Agent",
    custom: "Custom",
  };
  return labels[runner] || runner;
}

type DisplayMessage = {
  id: string;
  role: "user" | "assistant" | "tool" | "system" | "thinking";
  content: string;
  metadata?: {
    tool_name?: string;
    tool_input?: unknown;
    tool_output?: unknown;
    blocked_reason?: string;
    skill_name?: string;
    iteration?: { current: number; max: number };
  } | null;
  created_at: string;
  isStreaming?: boolean;
};

type ChatSession = {
  id: string;
  workspace_id: string;
  project_id: string | null;
  runner_type: RunnerType;
  created_at: string;
  message_count: number;
  title: string;
};

// ─────────────────────────────────────────────────────────────────────────────
// Bouncing Dots Component
// ─────────────────────────────────────────────────────────────────────────────

function BouncingDots() {
  return (
    <span className="inline-flex items-center gap-1 ml-1">
      <span className="w-1.5 h-1.5 rounded-full bg-nhs-blue animate-bounce" style={{ animationDelay: "0ms" }} />
      <span className="w-1.5 h-1.5 rounded-full bg-nhs-blue animate-bounce" style={{ animationDelay: "150ms" }} />
      <span className="w-1.5 h-1.5 rounded-full bg-nhs-blue animate-bounce" style={{ animationDelay: "300ms" }} />
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Thinking Indicator
// ─────────────────────────────────────────────────────────────────────────────

function ThinkingIndicator({ iteration }: { iteration?: { current: number; max: number } }) {
  return (
    <div className="flex items-start gap-2">
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-nhs-blue to-indigo-500 flex items-center justify-center mt-1">
        <Sparkles className="h-4 w-4 text-white animate-pulse" />
      </div>
      <div className="rounded-2xl px-4 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2 text-sm text-blue-700 dark:text-blue-300">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Thinking</span>
          <BouncingDots />
          {iteration && (
            <span className="text-xs text-blue-500 dark:text-blue-400 ml-2">
              (turn {iteration.current}/{iteration.max})
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Chat Page
// ─────────────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const {
    sessions,
    selectedSessionId,
    setSelectedSessionId,
    runnerType,
    setRunnerType,
    chatMessages,
    setChatMessages,
    chatStatus,
    setChatStatus,
    fetchSessions,
    fetchChatMessages,
    createSession,
    persistMessage,
  } = useAppContext();

  const { currentWorkspace } = useWorkspace();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [currentIteration, setCurrentIteration] = useState<{ current: number; max: number } | null>(null);
  const [activeToolName, setActiveToolName] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"messages" | "files">("messages");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Use chatStatus from context, but maintain local status states for UI
  const [status, setStatus] = useState<"idle" | "connecting" | "thinking" | "streaming" | "tool_running">("idle");
  // Map chatMessages from context to local messages format
  const messages: DisplayMessage[] = chatMessages.map((m) => ({
    id: m.message_id,
    role: m.role as "user" | "assistant" | "tool" | "system",
    content: m.content,
    metadata: m.metadata,
    created_at: m.created_at,
  }));

  // Load sessions when workspace changes
  useEffect(() => {
    if (currentWorkspace) {
      fetchSessions();
    }
  }, [currentWorkspace, fetchSessions]);

  // Load messages when session changes
  useEffect(() => {
    if (selectedSessionId) {
      fetchChatMessages(selectedSessionId);
    }
  }, [selectedSessionId, fetchChatMessages]);

  // Fetch projects when workspace changes
  useEffect(() => {
    if (!currentWorkspace) {
      setProjects([]);
      return;
    }
    setSelectedProjectId(null);
    let cancelled = false;
    (async () => {
      try {
        const data = await listProjects(currentWorkspace.id);
        if (!cancelled) setProjects(data.projects || []);
      } catch (err: unknown) {
        console.error("Failed to fetch projects:", err);
        if (!cancelled) setProjects([]);
      }
    })();
    return () => { cancelled = true; };
  }, [currentWorkspace]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, status]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => { eventSourceRef.current?.close(); };
  }, []);

  // ─── Create Session ──────────────────────────────────────────────────────

  async function onCreateSession() {
    if (!currentWorkspace) {
      alert("Please select a workspace first");
      return;
    }

    const sessionId = await createSession(
      selectedProjectId,
      runnerType,
      `${getRunnerLabel(runnerType).split(" ")[0]} Chat`
    );

    if (sessionId) {
      setSelectedSessionId(sessionId);
      setStreamingContent("");
      setStatus("idle");
      setChatStatus("idle");
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      alert("Failed to create session");
    }
  }

  // ─── Send Message ────────────────────────────────────────────────────────

  async function onSendMessage() {
    if (!selectedSessionId || !inputValue.trim() || status !== "idle") return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setStatus("connecting");
    setStreamingContent("");
    setCurrentIteration(null);
    setActiveToolName(null);

    // Persist user message to database
    await persistMessage(selectedSessionId, "user", userMessage);

    try {
      const session = sessions.find((s) => s.session_id === selectedSessionId);
      const apiBase = getRunnerApiBase(session?.runner_type || runnerType);

      const runRes = await fetch(`${apiBase}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ threadId: selectedSessionId, prompt: userMessage }),
      });
      if (!runRes.ok) {
        const errBody = await runRes.json().catch(() => ({}));
        throw new Error(errBody.detail || errBody.error || runRes.statusText);
      }
      const runData = await runRes.json();
      const runId = runData.runId;

      setStatus("thinking");

      // Subscribe to SSE events
      eventSourceRef.current?.close();
      const evtSource = new EventSource(`${apiBase}/runs/${runId}/events`);
      eventSourceRef.current = evtSource;
      let accumulatedText = "";

      evtSource.onmessage = async (event: MessageEvent) => {
        if (!event.data || event.data.trim() === "") return;
        try {
          const parsed = JSON.parse(event.data);
          const eventType: string = parsed.type || "";

          // ── Claude runner events ──────────────────────────────────────
          if (eventType === "ui.iteration") {
            setCurrentIteration(parsed.payload);
            setStatus("thinking");
          } else if (eventType === "ui.skill.activated") {
            const skillMsg: DisplayMessage = {
              id: `msg-${Date.now()}-skill-${parsed.payload?.skillName}`,
              role: "system",
              content: `Skill activated: ${parsed.payload?.skillName}`,
              metadata: { skill_name: parsed.payload?.skillName },
              created_at: new Date().toISOString(),
            };
            setChatMessages((prev: any) => [...prev, skillMsg as any]);
          } else if (eventType === "ui.message.assistant.delta") {
            accumulatedText += parsed.payload?.textDelta || "";
            setStreamingContent(accumulatedText);
            setStatus("streaming");
          } else if (eventType === "ui.message.assistant.final") {
            const finalText = parsed.payload?.text || accumulatedText;
            setStreamingContent("");
            accumulatedText = "";
            // Persist assistant message to database
            if (selectedSessionId && finalText) {
              await persistMessage(selectedSessionId, "assistant", finalText, runId);
            }
            setStatus("thinking");
          } else if (eventType === "ui.tool.call.start") {
            setActiveToolName(parsed.payload?.toolName || "tool");
            setStatus("tool_running");
          } else if (eventType === "ui.tool.call") {
            const toolMsg: DisplayMessage = {
              id: `msg-${Date.now()}-tool-${parsed.payload?.toolId}`,
              role: "tool",
              content: `Calling ${parsed.payload?.toolName || "tool"}`,
              metadata: { tool_name: parsed.payload?.toolName, tool_input: parsed.payload?.input },
              created_at: new Date().toISOString(),
            };
            setChatMessages((prev: any) => [...prev, toolMsg as any]);
          } else if (eventType === "ui.tool.result") {
            const toolResultMsg: DisplayMessage = {
              id: `msg-${Date.now()}-result-${parsed.payload?.toolId}`,
              role: "tool",
              content: `Result from ${parsed.payload?.toolName || "tool"}`,
              metadata: { tool_name: parsed.payload?.toolName, tool_output: parsed.payload?.output },
              created_at: new Date().toISOString(),
            };
            setChatMessages((prev: any) => [...prev, toolResultMsg as any]);
            setActiveToolName(null);
            setStatus("thinking");
          } else if (eventType === "ui.tool.blocked") {
            const blockedMsg: DisplayMessage = {
              id: `msg-${Date.now()}-blocked`,
              role: "system",
              content: `Tool blocked: ${parsed.payload?.toolName} - ${parsed.payload?.reason}`,
              metadata: { tool_name: parsed.payload?.toolName, blocked_reason: parsed.payload?.reason },
              created_at: new Date().toISOString(),
            };
            setChatMessages((prev: any) => [...prev,blockedMsg]);
            setActiveToolName(null);
            setStatus("thinking");

          // ── Codex runner events ───────────────────────────────────────
          } else if (eventType === "run.started") {
            setStatus("thinking");
          } else if (eventType === "item.completed" && parsed.item) {
            const item = parsed.item;
            if (item.type === "command_execution") {
              const toolMsg: DisplayMessage = {
                id: `msg-${Date.now()}-codex-tool`,
                role: "tool",
                content: item.status === "completed" ? "Command executed" : "Command failed",
                metadata: { tool_name: "shell", tool_input: item.command, tool_output: item.aggregated_output || `Exit code: ${item.exit_code}` },
                created_at: new Date().toISOString(),
              };
              setChatMessages((prev: any) => [...prev, toolMsg as any]);
            } else if (item.type === "agent_message" || item.text) {
              const assistantMsg: DisplayMessage = {
                id: `msg-${Date.now()}-codex-msg`,
                role: "assistant",
                content: item.text || "",
                created_at: new Date().toISOString(),
              };
              setChatMessages((prev: any) => [...prev, assistantMsg as any]);
            }

          // ── Common completion events ──────────────────────────────────
          } else if (eventType === "run.completed" || eventType === "stream.closed") {
            // Flush any remaining streamed content
            if (accumulatedText) {
              const finalMsg: DisplayMessage = {
                id: `msg-${Date.now()}-final`,
                role: "assistant",
                content: accumulatedText,
                created_at: new Date().toISOString(),
              };
              setChatMessages((prev: any) => [...prev, finalMsg as any]);
              accumulatedText = "";
              setStreamingContent("");
            }
            setStatus("idle");
            setCurrentIteration(null);
            setActiveToolName(null);
            evtSource.close();
            eventSourceRef.current = null;
            inputRef.current?.focus();
          } else if (eventType === "error") {
            const errorMsg: DisplayMessage = {
              id: `msg-${Date.now()}-error`,
              role: "system",
              content: `Error: ${parsed.message || parsed.payload?.message || "Unknown error"}`,
              created_at: new Date().toISOString(),
            };
            setChatMessages((prev: any) => [...prev, errorMsg as any]);
            setStatus("idle");
            setStreamingContent("");
            setCurrentIteration(null);
            setActiveToolName(null);
            evtSource.close();
            eventSourceRef.current = null;
          }
        } catch {
          // Ignore unparseable SSE events
        }
      };

      evtSource.onerror = () => {
        // Flush any remaining streamed content
        if (accumulatedText) {
          const finalMsg: DisplayMessage = {
            id: `msg-${Date.now()}-final`,
            role: "assistant",
            content: accumulatedText,
            created_at: new Date().toISOString(),
          };
          setChatMessages((prev: any) => [...prev, finalMsg as any]);
          accumulatedText = "";
        }
        setStatus("idle");
        setStreamingContent("");
        setCurrentIteration(null);
        setActiveToolName(null);
        evtSource.close();
        eventSourceRef.current = null;
        inputRef.current?.focus();
      };
    } catch (err: unknown) {
      const errorMsg: DisplayMessage = {
        id: `msg-${Date.now()}-error`,
        role: "system",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        created_at: new Date().toISOString(),
      };
      setChatMessages((prev: any) => [...prev, errorMsg as any]);
      setStatus("idle");
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  }

  const isRunning = status !== "idle";
  const wsName = currentWorkspace?.display_name || currentWorkspace?.name || "";
  const selectedProject = projects.find((p: Project) => p.id === selectedProjectId);

  return (
    <div className="flex h-[calc(100vh-120px)] bg-gray-50 dark:bg-zinc-900 rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-700">
      {/* Left Sidebar */}
      <div className="w-72 border-r border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 flex flex-col">
        {/* Context Panel */}
        <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{wsName || "No workspace"}</span>
          </div>
          {currentWorkspace && (
            <>
              <select
                value={selectedProjectId || ""}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedProjectId(e.target.value || null)}
                className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
              >
                <option value="">All projects</option>
                {projects.map((p: Project) => (
                  <option key={p.id} value={p.id}>{p.display_name || p.name}</option>
                ))}
              </select>
              <div className="mt-2">
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Runner</label>
                <select
                  value={runnerType}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => setRunnerType(e.target.value as RunnerType)}
                  className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
                >
                  <option value="claude">Claude (Anthropic)</option>
                  <option value="codex">OpenAI Agent (Codex)</option>
                  <option value="gemini" disabled>Gemini (Coming Soon)</option>
                  <option value="azure" disabled>Azure OpenAI (Coming Soon)</option>
                  <option value="bedrock" disabled>AWS Bedrock (Coming Soon)</option>
                </select>
              </div>
            </>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Sessions</span>
            {currentWorkspace && (
              <button
                onClick={onCreateSession}
                disabled={isRunning}
                className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-nhs-blue text-white hover:bg-nhs-dark-blue disabled:opacity-50 transition-colors"
              >
                <Plus className="h-3 w-3" /> New
              </button>
            )}
          </div>

          {!currentWorkspace ? (
            <p className="text-xs text-gray-400 dark:text-gray-500">Select a workspace from the sidebar</p>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500">No sessions yet. Click + New to start.</p>
          ) : (
            <div className="space-y-1">
              {sessions.map((s) => (
                <button
                  key={s.session_id}
                  onClick={() => {
                    setSelectedSessionId(s.session_id);
                    setStreamingContent("");
                  }}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedSessionId === s.session_id
                      ? "bg-blue-100 dark:bg-blue-900/30 text-nhs-blue dark:text-nhs-light-blue border border-blue-200 dark:border-blue-800"
                      : "bg-gray-50 dark:bg-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-600 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      s.runner_type === "claude" ? "bg-orange-400" : "bg-green-400"
                    }`} />
                    <span className="font-medium truncate">{s.title}</span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {getRunnerLabel(s.runner_type as RunnerType).split("(")[0].trim()} · {s.run_count || 0} msgs
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header with Tabs */}
        <div className="border-b border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800">
          <div className="h-14 px-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <MessagesSquare className="h-5 w-5 text-nhs-blue" />
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Chat</h1>
              {wsName && <span className="text-sm text-gray-500 dark:text-gray-400">{wsName}</span>}
              {selectedProject && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                  {selectedProject.display_name || selectedProject.name}
                </span>
              )}
            </div>
            {/* Status Indicator */}
            <div className="flex items-center gap-2">
              {status === "connecting" && (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                  <span className="text-xs text-gray-400">Connecting...</span>
                </>
              )}
              {status === "thinking" && (
                <>
                  <Sparkles className="h-4 w-4 text-nhs-blue animate-pulse" />
                  <span className="text-xs text-nhs-blue">Thinking<BouncingDots /></span>
                </>
              )}
              {status === "streaming" && (
                <>
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-xs text-green-600 dark:text-green-400">Streaming</span>
                </>
              )}
              {status === "tool_running" && (
                <>
                  <Wrench className="h-4 w-4 text-amber-500 animate-spin" />
                  <span className="text-xs text-amber-600 dark:text-amber-400">Running {activeToolName || "tool"}</span>
                </>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 px-6 pb-2">
            <button
              onClick={() => setViewMode("messages")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                viewMode === "messages"
                  ? "bg-nhs-blue text-white"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-700"
              }`}
            >
              Messages
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
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
          {viewMode === "messages" ? (
            !selectedSessionId ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <MessagesSquare className="h-16 w-16 mx-auto text-gray-300 dark:text-zinc-600 mb-4" />
                <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Start a Conversation
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                  {currentWorkspace
                    ? "Create a new session to begin chatting with the HIE integration agent."
                    : "Select a workspace from the sidebar first, then create a new session."}
                </p>
              </div>
            </div>
          ) : messages.length === 0 && !isRunning ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Bot className="h-12 w-12 mx-auto text-nhs-blue mb-4" />
                <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Ready to assist
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-4">
                  Ask about HIE routes, HL7 configurations, FHIR mappings, or any integration question.
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                  {[
                    "How do I create an HL7 route?",
                    "Show system health status",
                    "Help me configure MLLP sender",
                    "What protocols are supported?",
                  ].map((q: string, i: number) => (
                    <button
                      key={i}
                      onClick={() => { setInputValue(q); inputRef.current?.focus(); }}
                      className="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-zinc-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg: DisplayMessage) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {/* Streaming content */}
              {streamingContent && (
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full bg-nhs-blue flex items-center justify-center mt-1">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="rounded-2xl px-4 py-3 bg-white dark:bg-zinc-700 border border-gray-200 dark:border-zinc-600 text-gray-900 dark:text-white max-w-[80%]">
                    <div className="text-sm whitespace-pre-wrap">{streamingContent}</div>
                    <span className="inline-block w-2 h-4 bg-nhs-blue animate-pulse ml-0.5 rounded-sm" />
                  </div>
                </div>
              )}
              {/* Thinking indicator */}
              {(status === "thinking" || status === "connecting") && !streamingContent && (
                <ThinkingIndicator iteration={currentIteration || undefined} />
              )}
              {/* Tool running indicator */}
              {status === "tool_running" && (
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full bg-amber-500 flex items-center justify-center mt-1">
                    <Wrench className="h-4 w-4 text-white" />
                  </div>
                  <div className="rounded-2xl px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                    <div className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Running {activeToolName || "tool"}</span>
                      <BouncingDots />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )
          ) : (
            <div className="max-w-2xl mx-auto space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">Project Files</h3>
                {selectedProject && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Project: {selectedProject.display_name || selectedProject.name}
                  </span>
                )}
              </div>
              <div className="space-y-3">
                <button
                  disabled
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm border border-gray-200 dark:border-zinc-600 rounded-lg text-gray-400 dark:text-gray-500 cursor-not-allowed hover:bg-gray-50 dark:hover:bg-zinc-700/50"
                  title="Coming soon"
                >
                  <Upload className="h-4 w-4" />
                  Upload Folder/Files
                </button>
                <button
                  disabled
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm border border-gray-200 dark:border-zinc-600 rounded-lg text-gray-400 dark:text-gray-500 cursor-not-allowed hover:bg-gray-50 dark:hover:bg-zinc-700/50"
                  title="Coming soon"
                >
                  <Download className="h-4 w-4" />
                  Download Project Files
                </button>
              </div>
              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-xs text-blue-800 dark:text-blue-200">
                  File management will allow you to upload code, configuration files, and download generated outputs from the chat workspace.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        {selectedSessionId && (
          <div className="border-t border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4">
            <div className="max-w-3xl mx-auto space-y-3">
              {/* Prompt Manager Link */}
              <div className="flex items-center justify-between">
                <a
                  href="/prompts"
                  className="flex items-center gap-2 text-xs text-nhs-blue dark:text-nhs-light-blue hover:underline"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Open Prompt Manager
                </a>
              </div>

              {/* Input */}
              <div className="flex gap-3">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setInputValue(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Describe your HIE integration need... (Enter to send, Shift+Enter for new line)"
                  className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-nhs-blue focus:border-transparent"
                  rows={2}
                  disabled={isRunning}
                />
                <button
                  onClick={onSendMessage}
                  disabled={!inputValue.trim() || isRunning}
                  className="px-6 py-3 rounded-lg bg-nhs-blue text-white font-medium hover:bg-nhs-dark-blue disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isRunning ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Message Bubble Component
// ─────────────────────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const isSystem = message.role === "system";

  if (isTool) {
    return (
      <div className="mx-8 my-2">
        <details className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm">
          <summary className="cursor-pointer font-medium text-amber-800 dark:text-amber-200 flex items-center gap-2">
            <Terminal className="h-3 w-3" />
            {message.metadata?.tool_name || "Tool"}
          </summary>
          <div className="mt-2 space-y-2">
            {!!message.metadata?.tool_input && (
              <div>
                <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Input:</div>
                <pre className="bg-amber-100 dark:bg-amber-900/30 rounded p-2 text-xs overflow-x-auto font-mono">
                  {typeof message.metadata!.tool_input === "string"
                    ? message.metadata!.tool_input
                    : JSON.stringify(message.metadata!.tool_input, null, 2)}
                </pre>
              </div>
            )}
            {!!message.metadata?.tool_output && (
              <div>
                <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Output:</div>
                <pre className="bg-amber-100 dark:bg-amber-900/30 rounded p-2 text-xs overflow-x-auto font-mono max-h-40 overflow-y-auto">
                  {typeof message.metadata!.tool_output === "string"
                    ? message.metadata!.tool_output
                    : JSON.stringify(message.metadata!.tool_output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </details>
      </div>
    );
  }

  if (isSystem) {
    const isBlocked = !!message.metadata?.blocked_reason;
    const isSkill = !!message.metadata?.skill_name;
    return (
      <div className="mx-8 my-2 text-center">
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs ${
          isBlocked
            ? "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
            : isSkill
            ? "bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300"
            : "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
        }`}>
          {isBlocked ? <ShieldAlert className="h-3 w-3" /> : isSkill ? <Sparkles className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className="flex items-start gap-2 max-w-[80%]">
        {!isUser && (
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-nhs-blue flex items-center justify-center mt-1">
            <Bot className="h-4 w-4 text-white" />
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-nhs-blue text-white"
              : "bg-white dark:bg-zinc-700 border border-gray-200 dark:border-zinc-600 text-gray-900 dark:text-white"
          }`}
        >
          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
        </div>
        {isUser && (
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-200 dark:bg-zinc-600 flex items-center justify-center mt-1">
            <UserIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
          </div>
        )}
      </div>
    </div>
  );
}
