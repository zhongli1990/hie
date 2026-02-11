# Release Notes - v1.7.4

**Release Date:** February 11, 2026
**Code Name:** "GenAI Multi-Runner Enhancement & Developer Platform"
**Status:** 🚀 Production Ready

---

## 🎯 Release Highlights

### Major Features

1. **✅ OpenAI/Codex Runner Enhancement**
   - Fixed response persistence - OpenAI responses now reload from database
   - Ported all 5 HIE Skills to Codex runner (hl7-route-builder, fhir-mapper, clinical-safety-review, integration-test, nhs-compliance-check)
   - Unified skill format between Claude and Codex runners
   - Created automated skill porting script

2. **✅ Prompt Manager Enhancement**
   - Added "Send to Chat" button for direct template-to-chat workflow
   - Added "Send to Agent Console" button
   - Implemented prefill logic for both Chat and Agents pages
   - Improved template-to-execution UX

3. **✅ Project File Management**
   - Implemented upload/download functionality for project files
   - Created workspace folder structure: `/app/data/project-files/{workspace_id}/{project_id}/`
   - ZIP download support with archiver package
   - Multi-file upload support
   - Buttons enabled with project context awareness

4. **✅ Custom Class Hot-Reload**
   - Dynamic reload of custom.* classes without engine restart
   - New Manager API endpoint: `POST /api/item-types/reload-custom`
   - Agent tool: `hie_reload_custom_classes`
   - Portal UI: "Reload Custom" button in Configure page
   - Namespace badges (core/custom) in item types table

5. **✅ Developer Platform Foundation**
   - Class namespace enforcement (li.* protected, custom.* developer)
   - Custom class examples and templates
   - E2E test suite for agent tools → Manager API pipeline
   - Enhanced developer guides and workflow scenarios

---

## 📦 What's New

### Backend (Engine)

**GenAI Session Persistence:**
- New routes: `/api/genai-sessions` for session management
- Database schema: `genai_sessions`, `genai_messages` tables
- Session persistence across page navigation
- Message history with metadata support

**Custom Class System:**
- `Engine/custom/` package for developer classes
- `ClassRegistry.reload_custom_classes()` for hot-reload
- Dynamic class registration at runtime
- Example: `Engine/custom/nhs/validation.py` (NHS validation process)
- Example: `Engine/custom/_example/example_process.py` (template)

**Class Registry Enhancement:**
- Dynamic custom class discovery
- Hot-reload without production restart
- Namespace validation and enforcement
- Integration with Manager API

### Frontend (Portal)

**Agents Page Enhancements:**
- File upload/download tab (replaces sidebar)
- Upload multiple files to project workspace
- Download project files as ZIP
- Session history with full transcript reload
- Project-aware file management

**Chat Page Enhancements:**
- Fixed OpenAI/Codex response persistence
- Added prefill support from Prompt Manager
- Thread lifecycle management per session
- Project Files tab integration
- Improved runner event handling

**Prompt Manager Enhancements:**
- "Send to Chat" button (green) - Opens Chat with template prefilled
- "Send to Agent Console" button (indigo) - Opens Agents with template prefilled
- Copy button for template text
- sessionStorage-based prefill mechanism

**Configure Page Enhancements:**
- "Reload Custom" button with emerald styling
- Namespace badges (li.core vs custom.dev)
- Real-time custom class discovery
- Visual feedback for reload operations

**Admin > Skills Page:**
- Healthcare-specific categories (HL7, FHIR, Clinical, Compliance, etc.)
- Rich metadata panel (source, invocable, timestamps, allowed tools, file path)
- Improved categorization and filtering

### Agent Runner

**Tool Expansion:**
- 17 total HIE Manager API tools (up from 14)
- New: `hie_reload_custom_classes` - Hot-reload custom classes
- Enhanced: `hie_create_item` - Better validation and error handling
- Enhanced: `hie_list_item_types` - Includes dynamic custom classes

**Skills Rewrite:**
- All 5 skills rewritten for Acute Trust TIE clinical workflows
- Updated API paths and tool references
- Added class namespace conventions
- Improved E2E workflow coverage
- **Skills now compatible with Codex runner**

### Codex Runner

**Skills Integration:**
- 5 HIE skills ported from Claude runner
- Skills location: `/root/.codex/skills/`
- Compatible SKILL.md format
- System skills: `.system/skill-installer`, `.system/skill-creator`
- Automated porting script: `scripts/port-skills-to-codex.sh`

### API Changes

**New Endpoints:**
- `GET /api/genai-sessions?workspace_id=<id>` - List sessions
- `POST /api/genai-sessions` - Create session
- `GET /api/genai-sessions/{session_id}` - Get session
- `GET /api/genai-sessions/{session_id}/messages` - List messages
- `POST /api/genai-sessions/{session_id}/messages` - Create message
- `POST /api/item-types/reload-custom` - Hot-reload custom classes
- `POST /api/project-files/upload` - Upload project files
- `GET /api/project-files/download` - Download project files as ZIP

**Enhanced Endpoints:**
- `GET /api/item-types` - Now includes dynamically registered custom classes

### Database Schema

**New Tables:**
```sql
CREATE TABLE genai_sessions (
  session_id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL,
  project_id UUID,
  runner_type VARCHAR(50) NOT NULL,
  thread_id VARCHAR(255),
  title VARCHAR(500),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE genai_messages (
  message_id UUID PRIMARY KEY,
  session_id UUID NOT NULL,
  run_id VARCHAR(255),
  role VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Docker Compose

**Development Environment:**
- Added `agent-runner` service to `docker-compose.dev.yml`
- Added `prompt-manager` service
- Portal env vars for GenAI connectivity
- Skills volume mounting for live editing

**Production Environment:**
- Added `HIE_MANAGER_URL` to agent-runner
- Added `WORKSPACES_ROOT` environment variable
- Skills volume: `./agent-runner/skills:/app/skills:ro`
- Health check dependencies

---

## 🔧 Bug Fixes

### Critical Fixes

1. **OpenAI Runner Response Persistence** (Issue #1)
   - **Problem:** Questions loaded from DB but responses didn't
   - **Root Cause:** Codex runner events updated local state but never persisted
   - **Fix:** Added `persistMessage()` calls for Codex assistant and tool messages
   - **Files:** `Portal/src/app/(app)/chat/page.tsx:334-349`

2. **Chat Thread Lifecycle** (v1.8.0)
   - **Problem:** Thread not found 404 errors in Chat page
   - **Root Cause:** Missing thread creation before run creation
   - **Fix:** Proper thread lifecycle management per session
   - **Files:** `Portal/src/app/(app)/chat/page.tsx:210-230`

3. **Hooks Config API** (v1.7.3)
   - **Problem:** Hooks not persisting to database
   - **Fix:** Data-driven seed system with proper database persistence

4. **Workspace Context** (v1.7.3)
   - **Problem:** Agents page workspace selector not working
   - **Fix:** Proper workspace context from WorkspaceContext

### Minor Fixes

- Fixed Codex runner error event format handling
- Fixed Portal proxy for GenAI API endpoints
- Fixed item type picker namespace distinction
- Fixed skills seed button functionality
- Fixed session title auto-generation
- Version bumps in health check endpoints

---

## 🎓 Documentation

### New Documentation

1. **SKILLS_COMPATIBILITY.md**
   - Skill format comparison (Claude vs Codex)
   - Porting process and automation
   - Verification and testing
   - Troubleshooting guide

2. **DEVELOPER_WORKFLOW_SCENARIOS.md**
   - 10+ developer workflow scenarios
   - Custom class development
   - Integration testing patterns
   - Agent-assisted development

3. **CUSTOM_CLASSES.md**
   - Custom class development guide
   - Namespace conventions
   - Hot-reload workflow
   - Examples and templates

4. **RELEASE_NOTES_v1.8.0.md**
   - Developer platform details
   - GenAI session architecture
   - Class namespace system

### Updated Documentation

- **LI_HIE_DEVELOPER_GUIDE.md** - Expanded custom class sections
- **NHS_TRUST_DEMO.md** - Updated with real-world TIE scenarios
- **IMPLEMENTATION_STATUS.md** - v1.8.0 and v1.7.4 updates
- **IMPLEMENTATION_PROGRESS.md** - Detailed progress tracking

---

## 📜 Scripts & Tools

### New Scripts

1. **scripts/port-skills-to-codex.sh**
   - Automated skill porting from Claude to Codex
   - Strips Claude-specific frontmatter
   - Copies to Codex container
   - Restarts runner to load skills

### New Tests

1. **tests/e2e/test_agent_tools_e2e.py**
   - 14 E2E tests for agent tools
   - Tests agent-runner → Manager API pipeline
   - Validates tool inputs/outputs
   - Tests custom class integration

---

## 🔄 Migration Guide

### From v1.8.0 to v1.7.4

**Database Migration:**
```bash
# Migration already applied if upgrading from v1.8.0
# If upgrading from earlier version, run:
docker exec hie-manager python -m alembic upgrade head
```

**Docker Compose Changes:**
```bash
# Rebuild Portal with new dependencies (archiver)
docker-compose build hie-portal

# Restart all services
docker-compose restart

# Verify skills in Codex runner
docker exec hie-codex-runner ls /root/.codex/skills/
```

**Port HIE Skills to Codex:**
```bash
# Run automated porting script
./scripts/port-skills-to-codex.sh
```

**Verify Installation:**
1. Navigate to Agents page
2. Select "OpenAI Agent (Codex)" runner
3. Ask: "Can you help me build an HL7 route?"
4. ✅ Should invoke `hl7-route-builder` skill

---

## 🧪 Testing

### Test Coverage

**E2E Tests:**
- ✅ Agent tools → Manager API pipeline (14 tests)
- ✅ Custom class hot-reload workflow
- ✅ GenAI session persistence
- ✅ File upload/download functionality

**Manual Testing:**
- ✅ OpenAI runner response persistence
- ✅ Prompt Manager "Send to Chat" workflow
- ✅ Project file upload/download
- ✅ Custom class namespace enforcement
- ✅ Skills triggering in both Claude and Codex runners

### Testing Checklist

**GenAI Session Persistence:**
- [ ] Create session with OpenAI runner
- [ ] Send message and get response
- [ ] Navigate away and return
- [ ] ✅ Both question and response reload from DB

**Prompt Manager:**
- [ ] Open Prompt Manager, select template
- [ ] Click "Send to Chat"
- [ ] ✅ Chat page opens with template prefilled
- [ ] Click "Send to Agent Console"
- [ ] ✅ Agents page opens with template prefilled

**File Management:**
- [ ] Select project in Agents page
- [ ] Upload files to project
- [ ] ✅ Files uploaded successfully
- [ ] Download project files
- [ ] ✅ ZIP file downloads with all files

**Skills in Codex:**
- [ ] Select OpenAI runner in Agents page
- [ ] Ask: "Build an HL7 route for ADT messages"
- [ ] ✅ Codex invokes `hl7-route-builder` skill
- [ ] Check Raw Events tab for skill loading

**Custom Class Hot-Reload:**
- [ ] Modify `Engine/custom/nhs/validation.py`
- [ ] Click "Reload Custom" in Configure page
- [ ] ✅ Changes reflected without engine restart
- [ ] Verify in item types list

---

## 📊 Statistics

**Code Changes:**
- **52 files changed**
- **8,102 insertions**
- **1,592 deletions**
- **Net: +6,510 lines**

**New Features:**
- 4 major features
- 3 new API routes
- 5 skills ported to Codex
- 17 agent tools total

**Documentation:**
- 4 new docs (1,200+ lines)
- 4 updated docs (2,000+ lines)
- 1 new script (69 lines)

---

## 🙏 Acknowledgments

### Contributors

- **Zhong Li** - Lead Developer, HIE Core Team
- **Claude Sonnet 4.5** - AI Pair Programming Assistant

### Changelog

See [CHANGELOG.md](../../CHANGELOG.md) for detailed commit history.

---

## 🔗 Resources

### Documentation
- [Developer Guide](../guides/DEVELOPER_AND_USER_GUIDE.md)
- [Custom Classes Guide](../guides/CUSTOM_CLASSES_GUIDE.md)
- [Skills Compatibility](../reference/SKILLS_COMPATIBILITY.md)
- [Developer Workflows](../guides/DEVELOPER_WORKFLOW_SCENARIOS.md)
- [NHS Trust Demo](../guides/NHS_TRUST_DEMO_GUIDE.md)

### Release Notes
- [v1.7.4 (Current)](RELEASE_NOTES_v1.7.4.md)
- [v1.8.0](RELEASE_NOTES_v1.8.0.md)

### Support
- GitHub Issues: https://github.com/openli/hie/issues
- Contact: zhong@li-ai.co.uk

---

## 📅 Roadmap

### v1.10.0 (Planned)
- Bi-directional skill sync (Codex → Claude)
- CI/CD integration for automatic skill porting
- Skill version management
- Enhanced file management UI
- Custom class versioning

### v2.0.0 (Future)
- Multi-tenant architecture enhancements
- Advanced routing engine with ML
- Real-time monitoring dashboard
- API rate limiting and quotas

---

**Next Steps:**
1. Test all 4 critical fixes in staging
2. Verify skills work in both Claude and Codex runners
3. Monitor GenAI session persistence performance
4. Gather user feedback on file management UX

---

*OpenLI HIE - Healthcare Integration Engine*
*Release v1.7.4 - February 11, 2026*
