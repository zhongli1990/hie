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

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { useWorkspace } from "./WorkspaceContext";

type RunnerType = "claude" | "codex" | "gemini" | "azure" | "bedrock" | "openli" | "custom";

const RUNNER_TYPE_STORAGE_KEY = "hie-runner-type";

// Helper to get initial runner type from localStorage
function getInitialRunnerType(): RunnerType {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(RUNNER_TYPE_STORAGE_KEY);
    if (stored === "codex" || stored === "claude" || stored === "gemini" ||
        stored === "azure" || stored === "bedrock" || stored === "openli" || stored === "custom") {
      return stored as RunnerType;
    }
  }
  return "claude";
}

type Session = {
  session_id: string;
  workspace_id: string;
  project_id: string | null;  // HIE addition - link to project
  runner_type: RunnerType;
  thread_id: string;
  title: string;  // Display title generated from first prompt
  created_at: string;
  run_count: number;
};

type AgentMessage = {
  message_id: string;
  session_id: string;
  run_id: string | null;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  metadata: any;
  created_at: string;
};

type ChatMessage = {
  message_id: string;
  session_id: string;
  run_id: string | null;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  metadata: {
    tool_name?: string;
    tool_input?: any;
    tool_output?: any;
  } | null;
  created_at: string;
  isStreaming?: boolean;
};

type SetStateAction<T> = T | ((prev: T) => T);

type AppContextType = {
  // Session state
  sessions: Session[];
  selectedSessionId: string | null;
  setSelectedSessionId: (id: string | null) => void;
  runnerType: RunnerType;
  setRunnerType: (type: RunnerType) => void;

  // Agents page state
  agentMessages: AgentMessage[];
  setAgentMessages: (messages: SetStateAction<AgentMessage[]>) => void;
  agentStatus: string;
  setAgentStatus: (status: string) => void;

  // Chat page state
  chatMessages: ChatMessage[];
  setChatMessages: (messages: SetStateAction<ChatMessage[]>) => void;
  chatStatus: string;
  setChatStatus: (status: string) => void;

  // Data fetching
  fetchSessions: () => Promise<void>;
  fetchAgentMessages: (sessionId: string) => Promise<void>;
  fetchChatMessages: (sessionId: string) => Promise<void>;
  createSession: (projectId: string | null, runnerType: RunnerType, title?: string) => Promise<string | null>;
  persistMessage: (sessionId: string, role: string, content: string, runId?: string, metadata?: any) => Promise<void>;
};

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  // Get workspace from global WorkspaceContext
  const { currentWorkspace } = useWorkspace();

  // Session state
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [runnerType, setRunnerTypeState] = useState<RunnerType>(getInitialRunnerType);

  // Persist runner type to localStorage
  const setRunnerType = useCallback((type: RunnerType) => {
    setRunnerTypeState(type);
    if (typeof window !== "undefined") {
      localStorage.setItem(RUNNER_TYPE_STORAGE_KEY, type);
    }
  }, []);

  // Agents page state
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [agentStatus, setAgentStatus] = useState<string>("idle");

  // Chat page state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatStatus, setChatStatus] = useState<string>("idle");

  // Fetch GenAI sessions for current workspace
  const fetchSessions = useCallback(async () => {
    if (!currentWorkspace) return;
    try {
      const r = await fetch(`/api/genai-sessions?workspace_id=${currentWorkspace.id}`);
      if (r.ok) {
        const data = await r.json();
        setSessions(data.sessions || []);
      }
    } catch (e) {
      console.error("Failed to fetch sessions:", e);
    }
  }, [currentWorkspace]);

  // Fetch messages for Agents page
  const fetchAgentMessages = useCallback(async (sessionId: string) => {
    try {
      const r = await fetch(`/api/genai-sessions/${sessionId}/messages`);
      if (r.ok) {
        const data = await r.json();
        setAgentMessages(data.messages || []);
      }
    } catch (e) {
      console.error("Failed to fetch agent messages:", e);
    }
  }, []);

  // Fetch messages for Chat page
  const fetchChatMessages = useCallback(async (sessionId: string) => {
    try {
      const r = await fetch(`/api/genai-sessions/${sessionId}/messages`);
      if (r.ok) {
        const data = await r.json();
        setChatMessages(data.messages || []);
      }
    } catch (e) {
      console.error("Failed to fetch chat messages:", e);
    }
  }, []);

  // Create a new session in current workspace
  const createSession = useCallback(async (
    projectId: string | null,
    runnerType: RunnerType,
    title?: string
  ) => {
    if (!currentWorkspace) {
      console.error("No workspace selected");
      return null;
    }
    try {
      const r = await fetch("/api/genai-sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: currentWorkspace.id,
          project_id: projectId,
          runner_type: runnerType,
          title: title || `${runnerType.charAt(0).toUpperCase() + runnerType.slice(1)} Session`,
        }),
      });
      if (r.ok) {
        const data = await r.json();
        await fetchSessions();
        return data.session_id;
      }
    } catch (e) {
      console.error("Failed to create session:", e);
    }
    return null;
  }, [currentWorkspace, fetchSessions]);

  // Persist a message to the database
  const persistMessage = useCallback(async (
    sessionId: string,
    role: string,
    content: string,
    runId?: string,
    metadata?: any
  ) => {
    try {
      await fetch(`/api/genai-sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, content, run_id: runId, metadata }),
      });
    } catch (e) {
      console.error("Failed to persist message:", e);
    }
  }, []);

  return (
    <AppContext.Provider
      value={{
        sessions,
        selectedSessionId,
        setSelectedSessionId,
        runnerType,
        setRunnerType,
        agentMessages,
        setAgentMessages,
        agentStatus,
        setAgentStatus,
        chatMessages,
        setChatMessages,
        chatStatus,
        setChatStatus,
        fetchSessions,
        fetchAgentMessages,
        fetchChatMessages,
        createSession,
        persistMessage,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}
