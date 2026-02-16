# OpenLI HIE v1.9.1 Release Notes

**Release Date:** 2026-02-13
**Previous Release:** v1.9.0

---

## Summary

v1.9.1 is a defect-fix release addressing three issues in the AI Agent subsystem
that were identified after the v1.9.0 enterprise topology viewer release. All three
fixes target the Portal Agents/Chat interface and its backing runners.

---

## Fixes

### 1. Codex Runner — Response Persistence

**Problem:** OpenAI Codex runner sessions displayed user queries in the chat history
but agent responses and command execution results were not persisted. The Raw Events
tab remained blank, making sessions unrecoverable after page reload.

**Root Cause:** The `item.completed` SSE event type emitted by the Codex SDK was not
handled in the Portal event stream processor.

**Fix:** Added `item.completed` event handling in `agents/page.tsx` with
`persistMessage()` calls for both `command_execution` (tool results) and
`agent_message` (assistant text) item types.

**Files changed:**
- `Portal/src/app/(app)/agents/page.tsx`

---

### 2. Codex Runner — Skills and HIE Tool Context

**Problem:** The Codex runner had no awareness of HIE Manager API tools or platform
skills. It could not perform any healthcare integration operations (create projects,
deploy items, manage routing rules, etc.), making it effectively non-functional for
HIE workflows.

**Root Cause:** Unlike the Claude agent-runner which has a built-in tools array and
skills loader, the Codex runner relied solely on an `AGENTS.md` file that was never
generated.

**Fix:** Added `buildHieContext()` and `ensureHieContext()` functions to
`codex-runner/src/server.ts` that generate a comprehensive `AGENTS.md` context file
containing:
- Full HIE Manager REST API documentation (19 tool endpoints)
- Class namespace conventions (`li.*` protected, `custom.*` extensible)
- Common core class names for HL7 operations
- All loaded platform skills (from `/app/skills/*/SKILL.md`)

Also added a `/api/skills` endpoint for skill enumeration.

**Files changed:**
- `codex-runner/src/server.ts`

---

### 3. Portal — File Browser and Upload/Download

**Problem:** The file upload/download panel in the Agents tab was non-functional.
File operations failed because the Portal container had no access to the shared
workspaces volume and the API routes used incorrect base paths.

**Root Cause:** The Portal container was missing the `hie_workspaces` volume mount
and `WORKSPACES_ROOT` environment variable. The upload/download API routes still
referenced old `PROJECT_FILES_BASE` paths from an earlier architecture.

**Fix:**
- **Docker Compose:** Added `hie_workspaces:/workspaces` volume and
  `WORKSPACES_ROOT=/workspaces` env var to Portal service in both
  `docker-compose.yml` and `docker-compose.dev.yml`. Added skills volume mount and
  HIE Manager URL env to codex-runner service.
- **Upload API:** Rewritten to use `WORKSPACES_ROOT` with `workspace_id/project_id`
  directory structure and path traversal validation.
- **Download API:** Rewritten with single-file download and directory ZIP support.
- **File List API (new):** Added `project-files/list/route.ts` providing directory
  browsing (`action=list`) and file content viewing (`action=view`) with extension
  filtering and 1MB view size limit.
- **File Browser UI:** Added full file browser panel to `agents/page.tsx` with
  directory navigation, breadcrumbs, file content viewer modal, and upload/download
  toolbar.

**Files changed:**
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `Portal/src/app/api/project-files/upload/route.ts`
- `Portal/src/app/api/project-files/download/route.ts`
- `Portal/src/app/api/project-files/list/route.ts` (new)
- `Portal/src/app/(app)/agents/page.tsx`

---

## Upgrade Notes

- **Docker volumes:** After pulling v1.9.1, run `docker compose down && docker compose up -d`
  to ensure the new volume mounts take effect.
- **No database migrations** required for this release.
- **No breaking API changes** — all existing endpoints remain compatible.

---

## Full Changeset

```
6 files changed, 403 insertions(+), 74 deletions(-)
1 new file: Portal/src/app/api/project-files/list/route.ts
```
