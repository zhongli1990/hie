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

import { useCallback, useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { MessagesSquare, Send, Loader2, Plus, Bot, User as UserIcon, Terminal, AlertCircle } from "lucide-react";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import { listProjects, type Project } from "@/lib/api-v2";

type RunnerType = "claude" | "codex";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  metadata?: {
    tool_name?: string;
    tool_input?: any;
    tool_output?: any;
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

export default function ChatPage() {
  // Use the existing WorkspaceContext (provided by (app)/layout.tsx)
  const { workspaces, currentWorkspace } = useWorkspace();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [runnerType, setRunnerType] = useState<RunnerType>("claude");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [status, setStatus] = useState<string>("idle");
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-select current workspace from context
  useEffect(() => {
    if (currentWorkspace && !selectedWorkspaceId) {
      setSelectedWorkspaceId(currentWorkspace.id);
    }
  }, [currentWorkspace, selectedWorkspaceId]);

  // Fetch projects for selected workspace using api-v2
  useEffect(() => {
    if (!selectedWorkspaceId) {
      setProjects([]);
      return;
    }
    setSelectedProjectId(null);
    setSelectedSessionId(null);
    setMessages([]);
    let cancelled = false;
    (async () => {
      try {
        const data = await listProjects(selectedWorkspaceId);
        if (!cancelled) {
          setProjects(data.projects || []);
        }
      } catch (e) {
        console.error("Failed to fetch projects:", e);
        if (!cancelled) setProjects([]);
      }
    })();
    return () => { cancelled = true; };
  }, [selectedWorkspaceId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Create new session via agent-runner backend
  async function onCreateSession() {
    if (!selectedWorkspaceId) return;
    try {
      const ws = workspaces.find(w => w.id === selectedWorkspaceId);
      const workingDir = `/workspaces/${ws?.name || "default"}`;
      const res = await fetch("/api/agent-runner/threads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workingDirectory: workingDir }),
      });
      if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
      const data = await res.json();
      const newSession: ChatSession = {
        id: data.threadId || `session-${Date.now()}`,
        workspace_id: selectedWorkspaceId,
        project_id: selectedProjectId,
        runner_type: runnerType,
        created_at: new Date().toISOString(),
        message_count: 0,
        title: `Chat ${sessions.length + 1}`,
      };
      setSessions(prev => [newSession, ...prev]);
      setSelectedSessionId(newSession.id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to create session:", e);
      // Fallback to local session
      const newSession: ChatSession = {
        id: `session-${Date.now()}`,
        workspace_id: selectedWorkspaceId,
        project_id: selectedProjectId,
        runner_type: runnerType,
        created_at: new Date().toISOString(),
        message_count: 0,
        title: `Chat ${sessions.length + 1}`,
      };
      setSessions(prev => [newSession, ...prev]);
      setSelectedSessionId(newSession.id);
      setMessages([]);
    }
  }

  // Send message via agent-runner SSE streaming
  async function onSendMessage() {
    if (!selectedSessionId || !inputValue.trim() || status === "running") return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setStatus("running");
    setStreamingContent("");

    // Add user message
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      // Create a run on the thread
      const runRes = await fetch("/api/agent-runner/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ threadId: selectedSessionId, prompt: userMessage }),
      });
      if (!runRes.ok) throw new Error(`Failed to create run: ${runRes.statusText}`);
      const runData = await runRes.json();
      const runId = runData.runId;

      // Subscribe to SSE events
      const evtSource = new EventSource(`/api/agent-runner/runs/${runId}/events`);
      let accumulatedText = "";

      evtSource.onmessage = (event) => {
        if (!event.data || event.data.trim() === "") return;
        try {
          const parsed = JSON.parse(event.data);
          const eventType = parsed.type || "";

          if (eventType === "ui.message.assistant.delta") {
            accumulatedText += parsed.payload?.textDelta || "";
            setStreamingContent(accumulatedText);
          } else if (eventType === "ui.message.assistant.final") {
            const finalText = parsed.payload?.text || accumulatedText;
            setStreamingContent("");
            accumulatedText = "";
            const assistantMsg: ChatMessage = {
              id: `msg-${Date.now()}-assistant`,
              role: "assistant",
              content: finalText,
              created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, assistantMsg]);
          } else if (eventType === "ui.tool.call.start" || eventType === "ui.tool.call") {
            const toolMsg: ChatMessage = {
              id: `msg-${Date.now()}-tool`,
              role: "tool",
              content: `Calling ${parsed.payload?.toolName || "tool"}`,
              metadata: { tool_name: parsed.payload?.toolName, tool_input: parsed.payload?.input },
              created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, toolMsg]);
          } else if (eventType === "ui.tool.result") {
            const toolResultMsg: ChatMessage = {
              id: `msg-${Date.now()}-tool-result`,
              role: "tool",
              content: `Result from ${parsed.payload?.toolName || "tool"}`,
              metadata: { tool_name: parsed.payload?.toolName, tool_output: parsed.payload?.output },
              created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, toolResultMsg]);
          } else if (eventType === "run.completed" || eventType === "stream.closed") {
            setStatus("idle");
            setStreamingContent("");
            evtSource.close();
            inputRef.current?.focus();
          } else if (eventType === "error") {
            const errorMsg: ChatMessage = {
              id: `msg-${Date.now()}-error`,
              role: "system",
              content: `Error: ${parsed.payload?.message || "Unknown error"}`,
              created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMsg]);
            setStatus("idle");
            setStreamingContent("");
            evtSource.close();
          }
        } catch {
          // Ignore unparseable SSE events
        }
      };

      evtSource.onerror = () => {
        setStatus("idle");
        setStreamingContent("");
        evtSource.close();
        inputRef.current?.focus();
      };
    } catch (e) {
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now()}-error`,
        role: "system",
        content: `Error: ${e instanceof Error ? e.message : "Unknown error"}`,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
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

  return (
    <div className="flex h-[calc(100vh-120px)] bg-gray-50 dark:bg-zinc-900 rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-700">
      {/* Left Sidebar */}
      <div className="w-72 border-r border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 flex flex-col">
        {/* Workspace Selector */}
        <div className="p-4 border-b border-gray-200 dark:border-zinc-700">
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Workspace</label>
          <select
            value={selectedWorkspaceId || ""}
            onChange={(e) => setSelectedWorkspaceId(e.target.value || null)}
            className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
            <option value="">Select workspace...</option>
            {Array.isArray(workspaces) && workspaces.map((w) => (
              <option key={w.id} value={w.id}>{w.display_name || w.name}</option>
            ))}
          </select>
          {selectedWorkspaceId && (
            <select
              value={selectedProjectId || ""}
              onChange={(e) => setSelectedProjectId(e.target.value || null)}
              className="w-full mt-2 rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
            >
              <option value="">All projects</option>
              {Array.isArray(projects) && projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Sessions</span>
            {selectedWorkspaceId && (
              <button
                onClick={onCreateSession}
                className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-nhs-blue text-white hover:bg-nhs-dark-blue transition-colors"
              >
                <Plus className="h-3 w-3" /> New
              </button>
            )}
          </div>

          {!selectedWorkspaceId ? (
            <p className="text-xs text-gray-400 dark:text-gray-500">Select a workspace first</p>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500">No sessions yet. Click + New to start.</p>
          ) : (
            <div className="space-y-1">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setSelectedSessionId(s.id);
                    setMessages([]);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedSessionId === s.id
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
                    {s.runner_type} &bull; {new Date(s.created_at).toLocaleDateString()}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Runner Selector */}
        {selectedWorkspaceId && !selectedSessionId && (
          <div className="p-4 border-t border-gray-200 dark:border-zinc-700">
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Runner</label>
            <select
              value={runnerType}
              onChange={(e) => setRunnerType(e.target.value as RunnerType)}
              className="w-full rounded-md border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
            >
              <option value="claude">Claude (Anthropic)</option>
              <option value="codex">Codex (OpenAI)</option>
            </select>
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-14 border-b border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MessagesSquare className="h-5 w-5 text-nhs-blue" />
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Chat</h1>
            {selectedWorkspaceId && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {Array.isArray(workspaces) && workspaces.find((w) => w.id === selectedWorkspaceId)?.display_name}
              </span>
            )}
          </div>
          {status === "running" && (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-nhs-blue" />
              <span className="text-xs text-nhs-blue">Agent is thinking...</span>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {!selectedSessionId ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <MessagesSquare className="h-16 w-16 mx-auto text-gray-300 dark:text-zinc-600 mb-4" />
                <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Start a Conversation
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                  Select a workspace and create a new session to begin chatting with the HIE integration agent.
                  Describe your integration needs in plain English.
                </p>
              </div>
            </div>
          ) : messages.length === 0 && status !== "running" ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Bot className="h-12 w-12 mx-auto text-nhs-blue mb-4" />
                <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Ready to assist
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mb-4">
                  Ask me about HIE routes, items, HL7 configurations, or any integration question.
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                  {[
                    "How do I create an HL7 route?",
                    "Show system health status",
                    "Help me configure MLLP sender",
                    "What protocols are supported?",
                  ].map((q, i) => (
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
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {streamingContent && (
                <MessageBubble
                  message={{
                    id: "streaming",
                    role: "assistant",
                    content: streamingContent,
                    created_at: new Date().toISOString(),
                    isStreaming: true,
                  }}
                />
              )}
              {status === "running" && !streamingContent && (
                <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-zinc-700 rounded-lg border border-gray-200 dark:border-zinc-600">
                  <Loader2 className="h-4 w-4 animate-spin text-nhs-blue" />
                  <span className="text-sm text-gray-600 dark:text-gray-300">Agent is working on your request...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        {selectedSessionId && (
          <div className="border-t border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4">
            <div className="max-w-3xl mx-auto">
              <div className="flex gap-3">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setInputValue(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Describe your HIE integration need... (Enter to send, Shift+Enter for new line)"
                  className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-700 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-nhs-blue focus:border-transparent"
                  rows={2}
                  disabled={status === "running"}
                />
                <button
                  onClick={onSendMessage}
                  disabled={!inputValue.trim() || status === "running"}
                  className="px-6 py-3 rounded-lg bg-nhs-blue text-white font-medium hover:bg-nhs-dark-blue disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
        )}
      </div>
    </div>
  );
}

// Message Bubble Component
function MessageBubble({ message }: { message: ChatMessage }) {
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
            {message.metadata?.tool_input && (
              <div>
                <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Input:</div>
                <pre className="bg-amber-100 dark:bg-amber-900/30 rounded p-2 text-xs overflow-x-auto font-mono">
                  {typeof message.metadata.tool_input === "string"
                    ? message.metadata.tool_input
                    : JSON.stringify(message.metadata.tool_input, null, 2)}
                </pre>
              </div>
            )}
            {message.metadata?.tool_output && (
              <div>
                <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">Output:</div>
                <pre className="bg-amber-100 dark:bg-amber-900/30 rounded p-2 text-xs overflow-x-auto font-mono max-h-40">
                  {typeof message.metadata.tool_output === "string"
                    ? message.metadata.tool_output
                    : JSON.stringify(message.metadata.tool_output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </details>
      </div>
    );
  }

  if (isSystem) {
    return (
      <div className="mx-8 my-2 text-center">
        <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-full text-xs text-red-700 dark:text-red-300">
          <AlertCircle className="h-3 w-3" />
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
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-gray dark:prose-invert">
              <div className="text-sm whitespace-pre-wrap">{message.content}</div>
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-1" />
              )}
            </div>
          )}
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
