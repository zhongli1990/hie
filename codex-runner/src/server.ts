/**
 * OpenLI HIE - Healthcare Integration Engine
 * Codex Runner - OpenAI Codex SDK Agent Service
 * 
 * Provides the same API contract as agent-runner (Claude):
 *   POST /threads       → create a thread
 *   POST /runs          → create a run (prompt execution)
 *   GET  /runs/:id/events → SSE event stream
 *   GET  /health        → health check
 * 
 * This enables plug-and-play interoperability between runners.
 */

import cors from "cors";
import express, { type Request, type Response } from "express";
import { Codex } from "@openai/codex-sdk";
import fs from "fs";
import path from "path";
import { randomUUID } from "crypto";

type ThreadRecord = {
  thread: any;
  workingDirectory: string;
};

type RunRecord = {
  id: string;
  threadId: string;
  prompt: string;
  buffer: string[];
  subscribers: Set<express.Response>;
  status: "running" | "completed" | "error";
};

const PORT = Number(process.env.PORT || "8081");
const WORKSPACES_ROOT = process.env.WORKSPACES_ROOT || "/workspaces";

const codex = new Codex();

const threads = new Map<string, ThreadRecord>();
const runs = new Map<string, RunRecord>();

function mustResolveWorkspace(p: string): string {
  const root = path.resolve(WORKSPACES_ROOT);
  const resolved = path.resolve(p);
  if (!resolved.startsWith(root + path.sep) && resolved !== root) {
    throw new Error("workingDirectory must be under WORKSPACES_ROOT");
  }
  return resolved;
}

function sseSend(res: express.Response, dataObj: unknown) {
  res.write(`data: ${JSON.stringify(dataObj)}\n\n`);
}

function publish(run: RunRecord, dataObj: unknown) {
  const line = `data: ${JSON.stringify(dataObj)}\n\n`;
  run.buffer.push(line);
  for (const sub of run.subscribers) {
    sub.write(line);
  }
}

const app = express();
app.use(cors());
app.use(express.json({ limit: "2mb" }));

// Health check - identical contract to agent-runner
app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", runner: "codex", version: "1.8.0" });
});

// Create thread - identical contract to agent-runner
app.post("/threads", async (req: Request, res: Response) => {
  try {
    // Derive working directory from HIE context or explicit path
    let workingDirectory: string;
    if (req.body?.workingDirectory) {
      workingDirectory = mustResolveWorkspace(String(req.body.workingDirectory));
    } else if (req.body?.workspaceId) {
      const wsName = req.body.workspaceName || req.body.workspaceId;
      const sub = req.body.projectId ? `${wsName}/${req.body.projectId}` : wsName;
      workingDirectory = mustResolveWorkspace(`${WORKSPACES_ROOT}/${sub}`);
    } else {
      workingDirectory = mustResolveWorkspace(WORKSPACES_ROOT);
    }
    const skipGitRepoCheck = Boolean(req.body?.skipGitRepoCheck ?? true);

    if (!fs.existsSync(workingDirectory)) {
      fs.mkdirSync(workingDirectory, { recursive: true });
    }
    const thread = codex.startThread({ workingDirectory, skipGitRepoCheck });
    const threadId = randomUUID();
    threads.set(threadId, { thread, workingDirectory });

    res.json({ threadId });
  } catch (err: any) {
    res.status(400).json({ error: err?.message || "error" });
  }
});

// Create run - identical contract to agent-runner
app.post("/runs", async (req: Request, res: Response) => {
  const threadId = String(req.body?.threadId || "");
  const prompt = req.body?.prompt;

  if (!threadId || typeof prompt !== "string" || !prompt.trim()) {
    res.status(400).json({ error: "threadId and prompt are required" });
    return;
  }

  const threadRecord = threads.get(threadId);
  if (!threadRecord) {
    res.status(404).json({ error: "thread not found" });
    return;
  }

  const runId = randomUUID();
  const run: RunRecord = {
    id: runId,
    threadId,
    prompt,
    buffer: [],
    subscribers: new Set(),
    status: "running",
  };
  runs.set(runId, run);

  res.json({ runId });

  // Execute the run asynchronously
  (async () => {
    try {
      publish(run, { type: "run.started", runId, threadId });
      const { events } = await threadRecord.thread.runStreamed(prompt);
      for await (const event of events) {
        publish(run, event);
      }
      run.status = "completed";
      publish(run, { type: "run.completed", runId, threadId });
      for (const sub of run.subscribers) {
        sub.end();
      }
      run.subscribers.clear();
    } catch (err: any) {
      run.status = "error";
      publish(run, { type: "error", message: err?.message || "error" });
      for (const sub of run.subscribers) {
        sub.end();
      }
      run.subscribers.clear();
    }
  })();
});

// SSE event stream - identical contract to agent-runner
app.get("/runs/:runId/events", (req: Request, res: Response) => {
  const runId = req.params.runId;
  const run = runs.get(runId);
  if (!run) {
    res.status(404).json({ error: "run not found" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");

  res.flushHeaders?.();
  res.write(`: connected\n\n`);

  // Replay buffered events
  for (const line of run.buffer) {
    res.write(line);
  }

  // If already finished, close immediately
  if (run.status !== "running") {
    sseSend(res, { type: "stream.closed", runId, status: run.status });
    res.end();
    return;
  }

  // Subscribe for live events
  run.subscribers.add(res);

  req.on("close", () => {
    run.subscribers.delete(res);
  });
});

app.listen(PORT, () => {
  console.log(`HIE Codex Runner listening on port ${PORT}`);
});
