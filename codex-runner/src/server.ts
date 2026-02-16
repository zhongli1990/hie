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
const HIE_MANAGER_URL = process.env.HIE_MANAGER_URL || "http://hie-manager:8081";
const SKILLS_DIR = process.env.GLOBAL_SKILLS_PATH || "/app/skills";

const codex = new Codex();

const threads = new Map<string, ThreadRecord>();
const runs = new Map<string, RunRecord>();

/** Load skill files from the global skills directory */
function loadSkillContent(): string {
  const skillsPath = path.resolve(SKILLS_DIR);
  if (!fs.existsSync(skillsPath)) return "";

  const sections: string[] = [];
  for (const entry of fs.readdirSync(skillsPath)) {
    const skillFile = path.join(skillsPath, entry, "SKILL.md");
    if (fs.existsSync(skillFile)) {
      sections.push(fs.readFileSync(skillFile, "utf-8"));
    }
  }
  return sections.join("\n\n---\n\n");
}

/** Build HIE context instructions for the workspace */
function buildHieContext(): string {
  const mgr = HIE_MANAGER_URL;
  const skills = loadSkillContent();

  return `# OpenLI HIE - Agent Context

You are an AI agent for OpenLI HIE (Healthcare Integration Engine), an enterprise-grade NHS healthcare messaging platform.

## HIE Manager API Tools

You can manage HIE projects by calling the Manager API. Use curl or shell commands:

### Workspace Management
- List workspaces: \`curl -s ${mgr}/api/workspaces\`
- Create workspace: \`curl -s -X POST ${mgr}/api/workspaces -H 'Content-Type: application/json' -d '{"name":"...","display_name":"..."}'\`

### Project Management
- List projects: \`curl -s ${mgr}/api/workspaces/{workspace_id}/projects\`
- Create project: \`curl -s -X POST ${mgr}/api/workspaces/{workspace_id}/projects -H 'Content-Type: application/json' -d '{"name":"...","display_name":"..."}'\`
- Get project: \`curl -s ${mgr}/api/workspaces/{workspace_id}/projects/{project_id}\`

### Item Management
- Create item: \`curl -s -X POST ${mgr}/api/projects/{project_id}/items -H 'Content-Type: application/json' -d '{"name":"...","item_type":"service|process|operation","class_name":"...","enabled":true}'\`
- List item types: \`curl -s ${mgr}/api/item-types\`

### Connection Management
- Create connection: \`curl -s -X POST ${mgr}/api/projects/{project_id}/connections -H 'Content-Type: application/json' -d '{"source_item_id":"...","target_item_id":"...","connection_type":"standard"}'\`

### Routing Rules
- Create rule: \`curl -s -X POST ${mgr}/api/projects/{project_id}/routing-rules -H 'Content-Type: application/json' -d '{"name":"...","condition_expression":"{MSH-9.1} = \\"ADT\\"","action":"send","target_items":["..."]}'\`

### Production Lifecycle
- Deploy: \`curl -s -X POST ${mgr}/api/workspaces/{ws}/projects/{proj}/deploy -H 'Content-Type: application/json' -d '{"start_after_deploy":true}'\`
- Start: \`curl -s -X POST ${mgr}/api/workspaces/{ws}/projects/{proj}/start\`
- Stop: \`curl -s -X POST ${mgr}/api/workspaces/{ws}/projects/{proj}/stop\`
- Status: \`curl -s ${mgr}/api/workspaces/{ws}/projects/{proj}/status\`

### Testing
- Test item: \`curl -s -X POST ${mgr}/api/workspaces/{ws}/projects/{proj}/items/{item_name}/test -H 'Content-Type: application/json' -d '{"message":"..."}'\`

### Custom Classes
- Reload: \`curl -s -X POST ${mgr}/api/item-types/reload-custom\`

## Class Namespace Convention
- Protected (product): \`li.*\`, \`Engine.li.*\`, \`EnsLib.*\` - DO NOT modify
- Developer extensible: \`custom.*\` - Safe to create/modify

## Common Item Class Names
- HL7 TCP Inbound: \`Engine.li.hosts.hl7.HL7TCPService\`
- HL7 TCP Outbound: \`Engine.li.hosts.hl7.HL7TCPOperation\`
- Routing Engine: \`Engine.li.hosts.routing.RoutingEngine\`
- File Inbound: \`Engine.li.hosts.file.FileService\`
- File Outbound: \`Engine.li.hosts.file.FileOperation\`
- FHIR REST Server: \`Engine.li.hosts.fhir.FHIRRESTService\`
- FHIR REST Client: \`Engine.li.hosts.fhir.FHIRRESTOperation\`
${skills ? `\n## Integration Skills\n\n${skills}` : ""}
`;
}

/** Write AGENTS.md to workspace so the Codex agent discovers HIE context */
function ensureHieContext(workingDirectory: string): void {
  const agentsFile = path.join(workingDirectory, "AGENTS.md");
  // Only write if it doesn't exist or is from us (has our header)
  if (fs.existsSync(agentsFile)) {
    const existing = fs.readFileSync(agentsFile, "utf-8");
    if (!existing.startsWith("# OpenLI HIE - Agent Context")) {
      return; // Don't overwrite user-created AGENTS.md
    }
  }
  fs.writeFileSync(agentsFile, buildHieContext(), "utf-8");
}

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
  res.json({ status: "ok", runner: "codex", version: "1.9.1" });
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

    // Write HIE context file so the Codex agent knows about HIE tools and skills
    ensureHieContext(workingDirectory);

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

// Skills listing - returns available skills for the UI
app.get("/api/skills", (_req: Request, res: Response) => {
  const skillsPath = path.resolve(SKILLS_DIR);
  if (!fs.existsSync(skillsPath)) {
    res.json([]);
    return;
  }

  const skills: { name: string; description: string; scope: string }[] = [];
  for (const entry of fs.readdirSync(skillsPath)) {
    const skillFile = path.join(skillsPath, entry, "SKILL.md");
    if (!fs.existsSync(skillFile)) continue;

    const content = fs.readFileSync(skillFile, "utf-8");
    let description = "";

    // Parse YAML frontmatter
    if (content.startsWith("---")) {
      const parts = content.split("---", 3);
      if (parts.length >= 3) {
        const fmLines = parts[1].split("\n");
        for (const line of fmLines) {
          const match = line.match(/^description:\s*["']?(.+?)["']?\s*$/);
          if (match) {
            description = match[1];
            break;
          }
        }
      }
    }

    skills.push({ name: entry, description, scope: "platform" });
  }

  res.json(skills);
});

app.listen(PORT, () => {
  console.log(`HIE Codex Runner listening on port ${PORT}`);
});
