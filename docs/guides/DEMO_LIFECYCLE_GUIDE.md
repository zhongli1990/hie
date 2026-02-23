# OpenLI HIE — Natural Language Integration Lifecycle Demo Guide

**Version:** 1.9.7
**Audience:** Product demos, NHS Trust onboarding, investor presentations, developer training
**Prerequisite:** Docker stack running (`docker compose up -d --build`)

---

## The Proposition

OpenLI HIE is the first integration engine where **natural language IS the development language**. No HL7 syntax to memorise, no configuration forms, no code to write. A developer who speaks English but knows nothing about HL7, FHIR, MLLP, or InterSystems IRIS can build and manage production NHS healthcare integrations — because the AI agent understands all of it.

This guide walks through a **complete clinical integration lifecycle** — from design to production monitoring — using only English instructions.

---

## Prerequisites

### 1. Start the Platform

```bash
cd /path/to/HIE

# Fresh start (recommended for demos)
docker compose down -v
docker compose up -d --build

# Wait for all services to be healthy (~60s)
docker compose ps
```

### 2. Verify Services

| Service | URL | Port | Expected |
|---------|-----|------|----------|
| Portal (UI) | http://localhost:9303 | 9303 | Login page renders |
| Manager API | http://localhost:9302/api/health | 9302 | `{"version": "1.9.7"}` |
| Agent Runner | http://localhost:9340/health | 9340 | `{"version": "1.9.7"}` |
| Prompt Manager | http://localhost:9341/health | 9341 | `{"version": "1.9.7"}` |
| PostgreSQL | localhost:9310 | 9310 | — |
| Redis | localhost:9311 | 9311 | — |
| MLLP Echo | localhost:9320 | 9320 | — |

```bash
# Quick verification of all three service versions
curl -s http://localhost:9302/api/health | python3 -m json.tool
curl -s http://localhost:9340/health | python3 -m json.tool
curl -s http://localhost:9341/health | python3 -m json.tool
```

### 3. Verify Demo Data (DB Seed)

The `scripts/init-db.sql` seeds all demo data automatically on first start. Verify it loaded correctly:

```bash
# Verify all 7 demo users exist with correct roles
docker exec hie-postgres psql -U hie -d hie -c \
  "SELECT u.email, u.display_name, u.title, u.status, r.name as role_name
   FROM hie_users u JOIN hie_roles r ON u.role_id = r.id
   ORDER BY u.email;"
```

**Expected output (7 rows):**

| email | display_name | title | status | role_name |
|-------|-------------|-------|--------|-----------|
| admin@hie.nhs.uk | System Administrator | — | active | super_admin |
| auditor@sth.nhs.uk | Robert Singh | IG Auditor | active | auditor |
| cso@sth.nhs.uk | Dr. Priya Patel | Clinical Safety Officer | active | clinical_safety_officer |
| developer@sth.nhs.uk | James Chen | Integration Developer | active | integration_engineer |
| operator@sth.nhs.uk | Mike Williams | Systems Operator | active | operator |
| trust.admin@sth.nhs.uk | Sarah Thompson | IT Director | active | tenant_admin |
| viewer@sth.nhs.uk | Emma Davis | Service Desk Analyst | active | viewer |

```bash
# Verify demo tenant
docker exec hie-postgres psql -U hie -d hie -c \
  "SELECT name, code, status, admin_email FROM hie_tenants;"
```

**Expected:** `St Thomas' Hospital NHS Foundation Trust | STH | active | trust.admin@sth.nhs.uk`

```bash
# Verify workspaces (default + STH)
docker exec hie-postgres psql -U hie -d hie -c \
  "SELECT name, display_name, tenant_id FROM workspaces ORDER BY name;"
```

**Expected (2 rows):**

| name | display_name | tenant_id |
|------|-------------|-----------|
| default | Default Workspace | (null) |
| sth-integrations | STH Integrations | 10000000-...-000000000001 |

```bash
# Verify 7 system roles
docker exec hie-postgres psql -U hie -d hie -c \
  "SELECT name, display_name, is_system FROM hie_roles ORDER BY name;"
```

**Expected:** auditor, clinical_safety_officer, integration_engineer, operator, super_admin, tenant_admin, viewer — all `is_system = true`.

```bash
# Verify 5 security hooks
docker exec hie-postgres psql -U hie -d hie -c \
  "SELECT name, hook_type, enabled, priority FROM hooks_config ORDER BY priority DESC;"
```

**Expected (5 rows):**
- Security: Block Dangerous Commands (pre_tool_use, priority 100)
- Security: Path Escape Prevention (pre_tool_use, priority 99)
- Clinical: Protect Patient Data (pre_tool_use, priority 98)
- Compliance: NHS Data Handling (pre_tool_use, priority 97)
- Audit: Tool Usage Logging (post_tool_use, priority 50)

### 4. Verify Demo User Login

```bash
# Test login for each demo user
python3 -c "
import urllib.request, json
users = [
    ('admin@hie.nhs.uk', 'Admin123!'),
    ('trust.admin@sth.nhs.uk', 'Demo12345!'),
    ('developer@sth.nhs.uk', 'Demo12345!'),
    ('cso@sth.nhs.uk', 'Demo12345!'),
    ('operator@sth.nhs.uk', 'Demo12345!'),
    ('viewer@sth.nhs.uk', 'Demo12345!'),
    ('auditor@sth.nhs.uk', 'Demo12345!'),
]
for email, pwd in users:
    data = json.dumps({'email': email, 'password': pwd}).encode()
    req = urllib.request.Request('http://localhost:9302/api/auth/login', data=data,
          headers={'Content-Type': 'application/json'}, method='POST')
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read().decode())
    print(f'{email:30s} => {d[\"user\"][\"display_name\"]:22s} token={\"yes\" if \"access_token\" in d else \"NO\"}')
"
```

**Expected:** All 7 users login successfully with JWT tokens issued.

### 5. Seed Skills and Prompt Templates

```bash
# Seed the 5 skills and 10 prompt templates into the database
curl -s -X POST http://localhost:9341/seed/skills | python3 -m json.tool
curl -s -X POST http://localhost:9341/seed/templates | python3 -m json.tool
```

**Expected:** `total_created: 5` skills, `total_created: 10` templates (or `skipped` if already seeded).

---

## Demo Users

All demo users belong to **St Thomas' Hospital NHS Foundation Trust** (code: STH).

| Persona | Email | Password | DB Role | Agent Role | What They Can Do |
|---------|-------|----------|---------|------------|------------------|
| **System Admin** | `admin@hie.nhs.uk` | `Admin123!` | super_admin | platform_admin | Everything across all tenants |
| **IT Director** | `trust.admin@sth.nhs.uk` | `Demo12345!` | tenant_admin | tenant_admin | Full access within STH tenant |
| **Integration Developer** | `developer@sth.nhs.uk` | `Demo12345!` | integration_engineer | developer | Design, Build, Test — no prod deploy |
| **Clinical Safety Officer** | `cso@sth.nhs.uk` | `Demo12345!` | clinical_safety_officer | clinical_safety_officer | Review, Test, Approve/Reject deployments |
| **Systems Operator** | `operator@sth.nhs.uk` | `Demo12345!` | operator | operator | Deploy, Start, Stop, Monitor — no build |
| **Service Desk Analyst** | `viewer@sth.nhs.uk` | `Demo12345!` | viewer | viewer | Read-only monitoring |
| **IG Auditor** | `auditor@sth.nhs.uk` | `Demo12345!` | auditor | auditor | Read-only + audit log access |

### Agent Role Resolution

The agent-runner maps DB roles to agent functional roles:

```
Database Role               Agent Role               Available Tools
────────────────────────────────────────────────────────────────────
super_admin              → platform_admin          → ALL 24 tools
tenant_admin             → tenant_admin            → 23 tools
integration_engineer     → developer               → 22 tools (no deploy/start/stop/rollback)
clinical_safety_officer  → clinical_safety_officer → 8 tools (read + test only)
operator                 → operator                → 11 tools (deploy/start/stop/rollback)
auditor                  → auditor                 → 8 tools (read-only + audit)
viewer                   → viewer                  → 6 tools (read-only monitoring)
```

Verify agent role resolution:
```bash
# Login as developer, check agent role
python3 -c "
import urllib.request, json
data = json.dumps({'email': 'developer@sth.nhs.uk', 'password': 'Demo12345!'}).encode()
req = urllib.request.Request('http://localhost:9302/api/auth/login', data=data,
      headers={'Content-Type': 'application/json'}, method='POST')
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']
req = urllib.request.Request('http://localhost:9340/roles/me',
      headers={'Authorization': f'Bearer {token}'})
d = json.loads(urllib.request.urlopen(req).read().decode())
print(f'Agent role: {d[\"role\"]} ({d[\"displayName\"]})')
"
```

**Expected:** `Agent role: developer (Integration Developer)`

---

## The Clinical Scenario

**St Thomas' Hospital** needs a new **ADT (Admit/Discharge/Transfer) integration** to route patient admission and discharge messages from their **Cerner PAS (Patient Administration System)** to two downstream systems:

- **RIS** (Radiology Information System) — needs admissions (A01), transfers (A02), and discharges (A03)
- **EPR** (Electronic Patient Record) — needs admissions (A01) and discharges (A03) only

This is a standard NHS integration pattern. In a traditional integration engine, this would take days of configuration by an HL7 specialist. With OpenLI HIE, it takes minutes.

---

## ACT 1: DESIGN & BUILD (Developer)

### Login

1. Open **http://localhost:9303** in your browser
2. Login as: **`developer@sth.nhs.uk`** / **`Demo12345!`**
3. **Verify you see:**
   - Dashboard page loads with workspace stats
   - Sidebar navigation: Dashboard, Projects, Agents, Configure, Monitoring, Logs
   - Your role is shown in the interface

### Step 1: Navigate to the AI Agent

1. Click **Agents** in the sidebar (http://localhost:9303/agents)
2. **Verify you see:**
   - A chat interface with the AI agent
   - **Quick Start Panel** with role-specific prompt templates for: Design, Build, Test, Monitor
   - Agent runner selector (Claude is default)
   - Project selector dropdown

### Step 2: Design the Integration

Paste this prompt into the agent chat:

```
I need to build an ADT integration for St Thomas' Hospital.

The Cerner PAS (Patient Administration System) sends HL7 ADT messages
on MLLP port 5001.

I need to route messages to two downstream systems:
  - RIS (Radiology) at 10.0.1.50:5002 — needs A01 admissions, A02 transfers, and A03 discharges
  - EPR (Electronic Patient Record) at 10.0.1.60:5003 — needs A01 admissions and A03 discharges only

Please start by listing available workspaces and creating a project for this integration.
```

**What the AI does** (using tools automatically):
1. `hie_list_workspaces` — finds the "STH Integrations" workspace
2. `hie_create_project` — creates "Cerner ADT Integration" project
3. Explains the architecture it will build: 1 inbound service, 1 routing engine, 2 outbound operations

**What to verify:**
- Tool calls appear as SSE events streamed in real-time
- The agent identifies the STH workspace (tenant-scoped)
- A project is created and confirmed

### Step 3: Build the Complete Integration

```
Now build the complete integration. Create:
1. An inbound HL7 TCP service called "Cerner.PAS.Receiver" on port 5001
   with Application AckMode
2. A routing engine called "ADT.Router" to evaluate message types
3. An outbound operation "RIS.Sender" targeting 10.0.1.50:5002
4. An outbound operation "EPR.Sender" targeting 10.0.1.60:5003
5. Wire all connections from receiver → router → both senders
6. Create routing rules:
   - Route A01, A02, A03 to RIS
   - Route A01, A03 to EPR (no A02 transfers)
```

**What the AI does** (6-8 tool calls):
1. `hie_create_item` x 4 — Creates the service, process, and both operations with correct class names (`li.hosts.hl7.HL7TCPService`, `li.hosts.routing.HL7RoutingEngine`, `li.hosts.hl7.HL7TCPOperation`)
2. `hie_create_connection` x 3 — Wires Receiver→Router, Router→RIS, Router→EPR
3. `hie_create_routing_rule` x 2 — Creates HL7 condition expressions:
   - `{MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A02","A03")` → RIS
   - `{MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A03")` → EPR

**What to verify:**
- Each tool call is streamed as an SSE event in real-time
- Agent creates 4 items, 3 connections, 2 routing rules
- All use correct class names from the `li.*` namespace

### Step 4: Test the Integration

```
Test this integration by sending sample HL7 ADT messages:
1. Send an A01 admission for patient John Smith, NHS number 943 476 5919
2. Send an A02 transfer for the same patient
3. Send an A03 discharge

Tell me which messages went to which targets.
```

**What the AI does:**
1. `hie_test_item` x 3 — Generates valid HL7 v2.4 messages with correct MSH, PID, PV1 segments and sends them through the inbound service
2. Reports routing results: A01 → RIS + EPR, A02 → RIS only, A03 → RIS + EPR
3. **PII sanitisation**: The audit log records this action but the NHS number `943 476 5919` is replaced with `[NHS_NUMBER]` before storage

### Step 5: Attempt Production Deploy (RBAC in Action)

```
This looks good. Deploy it to production.
```

**What happens:**
- The AI agent **cannot see** the `hie_deploy_project` tool — it's not in the developer's permitted tool set (Layer 1: proactive filtering)
- Even if the model hallucinated the tool call, the pre-tool-use hook would block it (Layer 2: defensive validation)
- The agent responds: *"I've built and tested the integration successfully. However, as an Integration Developer, I don't have permission to deploy to production. Production deployments require approval from a Clinical Safety Officer or Tenant Admin. I'll create a deployment approval request."*
- **Every tool call above has been logged** to the audit trail with user, role, action, and PII-sanitised input/output

---

## ACT 2: CLINICAL SAFETY REVIEW (CSO)

### Login

1. **Log out** of the developer account
2. Login as: **`cso@sth.nhs.uk`** / **`Demo12345!`**
3. **Verify you see:**
   - Dashboard loads
   - Navigate to Agents page — different Quick Start templates than developer (Review, Test, Approve)

### Step 6: Review the Integration

Navigate to **Agents** and paste:

```
I need to review the Cerner ADT Integration project at St Thomas' Hospital.
Show me the full project configuration and then run a DCB0129 clinical
safety review.
```

**What the AI does:**
1. `hie_list_workspaces` → `hie_list_projects` → `hie_get_project` — Retrieves full project configuration
2. Runs the `clinical-safety-review` skill — a 32-item DCB0129/DCB0160 checklist covering:
   - Hazard identification (message loss, mis-routing, data corruption)
   - Error handling assessment (ACK modes, retry policies, dead-letter queues)
   - Audit trail coverage (every tool call logged)
   - Data integrity (PID segment handling, NHS number validation)
   - Fail-safe defaults (what happens if RIS is down?)
3. Produces a structured safety report with risk ratings and recommendations

### Step 7: Independent Test

```
Send a test A01 admission through the route so I can verify the
message flow independently.
```

**What to verify:**
- CSOs CAN test — they have `hie_test_item` permission
- Routing results are shown
- This is logged as a CSO action in the audit trail

### Step 8: Approve the Deployment

**Via Portal UI:**
1. Navigate to **Admin > Approvals** in the sidebar (http://localhost:9303/admin/approvals)
2. **Verify you see:**
   - Stats cards: Pending Review, Approved, Rejected
   - The pending approval request from James Chen (developer)
3. Click to expand and review the config snapshot
4. Click **Approve**
5. Enter review notes: *"DCB0129 review passed. All 32 safety criteria met. ADT routing logic verified. Approved for production."*
6. **Verify:** Status changes to **Approved** (green)

**Or via natural language (in Agents chat):**
```
Approve the pending deployment for the Cerner ADT Integration.
Add review notes: "DCB0129 review passed. All routing rules verified
against NHS ADT specification. PII sanitisation confirmed. Approved."
```

### Step 9: Verify CSO Cannot Build

```
Create a new inbound service called "New.Receiver" on port 6001.
```

**What to verify:**
- Agent **CANNOT** create items — `hie_create_item` is not in the CSO's 8-tool set
- Agent explains CSOs can review and test but not create configurations

---

## ACT 3: DEPLOY & MONITOR (Operator)

### Login

1. **Log out** of the CSO account
2. Login as: **`operator@sth.nhs.uk`** / **`Demo12345!`**
3. Navigate to the **Agents** page

### Step 10: Deploy to Production

```
Deploy the approved Cerner ADT Integration to production and start
all items.
```

**What the AI does:**
1. `hie_list_workspaces` → `hie_list_projects` — Finds the approved project
2. `hie_deploy_project` — Deploys the configuration to the HIE Engine
3. `hie_start_project` — Starts all enabled items (receiver, router, senders)
4. `hie_project_status` — Confirms all 4 items are running

### Step 11: Monitor

```
Show me the status of all running integrations at St Thomas'.
Include queue depths, error counts, and connection health.
```

**What the AI does:**
1. `hie_project_status` — Returns runtime metrics for all items

### Step 12: Operational Commands

```
Stop the EPR Sender operation — EPR is going down for maintenance.
```

**What the AI does:**
- Operators can start/stop individual items or entire projects
- `hie_stop_project` (or item-level stop when available)
- Reports: "EPR.Sender stopped. RIS.Sender and Cerner.PAS.Receiver continue running."

---

## ACT 4: AUDIT & COMPLIANCE (Auditor)

### Login

1. Login as: **`auditor@sth.nhs.uk`** / **`Demo12345!`**

### Step 13: Review Audit Trail

**Via Portal UI:**
1. Navigate to **Admin > Audit Log** (http://localhost:9303/admin/audit)
2. **Verify you see:**
   - **Stats cards**: Total Actions, Successful, Denied, Errors
   - **Chronological entries** from all Acts:
     - Developer's create/build/test actions (success)
     - Developer's deploy attempt (denied)
     - CSO's review and test actions (success)
     - Operator's deploy and start actions (success)
   - **PII Sanitisation**: NHS number `943 476 5919` appears as `[NHS_NUMBER]`, postcodes appear as `[POSTCODE]`
   - **Filters**: Action type, Status dropdown, search
   - **CSV Export** button
   - **Expandable rows** showing sanitised input/output summaries

**What you'll see in the audit log:**

| Time | User | Role | Action | Target | Status |
|------|------|------|--------|--------|--------|
| 10:01 | James Chen | developer | hie_create_project | ADT Integration | success |
| 10:02 | James Chen | developer | hie_create_item | Cerner.PAS.Receiver | success |
| 10:02 | James Chen | developer | hie_create_item | ADT.Router | success |
| 10:03 | James Chen | developer | hie_create_item | RIS.Sender | success |
| 10:03 | James Chen | developer | hie_create_item | EPR.Sender | success |
| 10:04 | James Chen | developer | hie_create_connection | Receiver→Router | success |
| 10:05 | James Chen | developer | hie_test_item | A01 test | success |
| 10:06 | James Chen | developer | hie_deploy_project | — | **denied** |
| 10:10 | Dr. Patel | cso | hie_get_project | ADT Integration | success |
| 10:11 | Dr. Patel | cso | hie_test_item | A01 verify | success |
| 10:15 | Mike Williams | operator | hie_deploy_project | ADT Integration | success |
| 10:15 | Mike Williams | operator | hie_start_project | ADT Integration | success |

**Key compliance points:**
- NHS number `943 476 5919` appears as `[NHS_NUMBER]` in all audit entries
- UK postcodes appear as `[POSTCODE]`
- Developer's denied deploy attempt is recorded for IG review
- Complete chain of custody: Developer built → CSO reviewed → Operator deployed

### Step 14: Verify Auditor is Read-Only

Navigate to Agents and type:

```
Create a new project called "Test Project".
```

**What to verify:** Agent CANNOT create — auditor role is read-only + audit access.

---

## ACT 5: ADMIN OVERVIEW (Trust Admin)

### Login

1. Login as: **`trust.admin@sth.nhs.uk`** / **`Demo12345!`**

### Step 15: Full Lifecycle in One Session

Trust admins have full access within their tenant. Navigate to Agents:

```
Show me everything in the St Thomas' workspace — all projects,
their status, recent audit entries, and any pending approvals.
```

**What the AI does:**
- Full tool access within tenant scope (23 tools)
- Lists all projects, statuses, audit statistics
- Shows pending approvals (if any)

### Step 16: Portal Pages Walkthrough

Visit each page and verify it loads with data:

| Page | URL | What to See |
|------|-----|-------------|
| Dashboard | http://localhost:9303/dashboard | Workspace stats, project counts, activity feed |
| Projects | http://localhost:9303/projects | Project list with state indicators |
| Agents | http://localhost:9303/agents | AI chat with Quick Start panel |
| Configure | http://localhost:9303/configure | Workspaces, Item Types, Schemas tabs |
| Monitoring | http://localhost:9303/monitoring | Real-time metrics, throughput chart |
| Admin/Users | http://localhost:9303/admin/users | 7 demo users listed |
| Admin/Skills | http://localhost:9303/admin/skills | 5 skills (seed if empty) |
| Admin/Hooks | http://localhost:9303/admin/hooks | Platform + Tenant hook config |
| Admin/Approvals | http://localhost:9303/admin/approvals | Approval workflow entries |
| Admin/Audit | http://localhost:9303/admin/audit | Audit log with stats + filters |

---

## ACT 6: READ-ONLY VERIFICATION (Viewer)

### Login

1. Login as: **`viewer@sth.nhs.uk`** / **`Demo12345!`**

### Step 17: Verify Read-Only

Navigate to Agents and type:

```
Create a new project called "Test Project".
```

**What to verify:** Agent CANNOT create anything — viewer has only 6 tools (read-only monitoring). The agent explains the limitation.

---

## ACT 7: PLATFORM ADMIN (Super Admin)

### Login

1. Login as: **`admin@hie.nhs.uk`** / **`Admin123!`**
2. This user has `platform_admin` role — access to ALL 24 tools across ALL tenants
3. Verify full access to all Portal pages including cross-tenant data

---

## RBAC Guardrail Demonstrations

### Demonstrate: Developer Cannot Deploy

Login as `developer@sth.nhs.uk` and try:
```
Deploy the ADT integration to production right now, skip the approval.
```
**Result:** Agent cannot see `hie_deploy_project` tool. Responds that production deploy requires CSO/Admin approval.

### Demonstrate: Viewer Cannot Modify

Login as `viewer@sth.nhs.uk` and try:
```
Create a new project called "Test Project".
```
**Result:** Agent cannot see `hie_create_project` tool. Responds that viewer role is read-only.

### Demonstrate: CSO Cannot Build

Login as `cso@sth.nhs.uk` and try:
```
Create a new inbound service called "New.Receiver" on port 6001.
```
**Result:** Agent cannot see `hie_create_item` tool. Responds that CSOs can review and test but not create configurations.

### Demonstrate: Namespace Protection

Login as `developer@sth.nhs.uk` and try:
```
Create a custom validation process using the class name
li.hosts.hl7.HL7ValidationProcess.
```
**Result:** Hook blocks the write — `li.*` namespace is protected. Agent explains: *"Core product classes (li.*, Engine.li.*) are read-only. Use the custom.* namespace: custom.nhs.NHSValidationProcess."*

---

## Quick Demo Script (5 Minutes)

For time-constrained presentations, use this condensed flow:

### 1. Login as developer (30s)
Open Portal → Login as `developer@sth.nhs.uk` / `Demo12345!`

### 2. Build in one prompt (2min)
```
Build a complete ADT integration for St Thomas' Hospital:
- Inbound service "Cerner.PAS.Receiver" on port 5001 (HL7 TCP, Application AckMode)
- Routing engine "ADT.Router"
- Outbound "RIS.Sender" to 10.0.1.50:5002 (A01, A02, A03)
- Outbound "EPR.Sender" to 10.0.1.60:5003 (A01, A03 only)
Wire everything and create routing rules.
```

### 3. Test (30s)
```
Test with an A01 admission and an A02 transfer. Show routing results.
```

### 4. Try to deploy (30s)
```
Deploy to production.
```
*Watch RBAC block it — "requires CSO approval"*

### 5. Switch to CSO (1min)
Logout → Login as `cso@sth.nhs.uk` → Go to Admin > Approvals → Approve

### 6. Switch to operator (30s)
Logout → Login as `operator@sth.nhs.uk` → Type: "Deploy and start the ADT integration"

**Total: ~5 minutes for a complete enterprise integration lifecycle**

---

## Enterprise Guardrail Summary

| Guardrail | Status | What It Protects |
|-----------|--------|-----------------|
| **GR-1 Role-Based Tool Access** | ACTIVE | 7 roles, 2-layer defense-in-depth (Layer 1: tool filtering, Layer 2: hook validation) |
| **GR-2 Audit Logging** | ACTIVE | Every AI tool call logged with PII sanitisation (NHS numbers → `[NHS_NUMBER]`, postcodes → `[POSTCODE]`) |
| **GR-3 Approval Workflows** | ACTIVE | Production deploys require CSO/Admin approval — developers cannot bypass |
| **GR-4 Configuration Snapshots** | ACTIVE | Auto-snapshot on deploy, list/get/rollback versions |
| **GR-5 Rate Limiting** | ACTIVE | Redis sliding-window enforcement on API endpoints |
| **GR-6 Namespace Enforcement** | ACTIVE | Core `li.*` classes read-only; developers write to `custom.*` only |

---

## Manual E2E Test Checklist

| # | Test | Expected | Pass? |
|---|------|----------|-------|
| 1 | All 3 health endpoints report version | `1.9.7` (from VERSION file) | |
| 2 | All 7 demo users login successfully | JWT tokens issued, correct role names | |
| 3 | Agent role resolution works | developer→developer, cso→clinical_safety_officer, etc. | |
| 4 | Developer can design/build/test | Items, connections, rules created via NL | |
| 5 | Developer CANNOT deploy to prod | RBAC blocks, suggests approval | |
| 6 | CSO can review and test | Safety report generated, test items work | |
| 7 | CSO can approve deployment | Approval status → Approved in Portal | |
| 8 | CSO CANNOT build | `hie_create_item` not available | |
| 9 | Operator can deploy after approval | Project deployed and started | |
| 10 | Operator can stop/start items | Items stopped/started | |
| 11 | Auditor sees full audit trail | PII sanitised, filters work | |
| 12 | Auditor is read-only | Cannot create/modify | |
| 13 | Viewer is read-only | Cannot create/modify | |
| 14 | Trust Admin has full tenant access | All tools available | |
| 15 | Super Admin has platform access | Cross-tenant access | |
| 16 | Audit log shows PII sanitisation | NHS numbers → `[NHS_NUMBER]` | |
| 17 | Namespace protection enforced | `li.*` writes blocked for non-admin | |
| 18 | All 11 Portal pages render | HTTP 200 with real content | |

---

## Troubleshooting

### "Login failed" for demo users
```bash
# Reset database and re-seed
docker compose down -v
docker compose up -d --build
# Wait 30s for init-db.sql to execute
```

### Agent returns "I don't have access to that tool"
This is RBAC working correctly. Check the user's role — they may not have permission for the requested action. See the role permission matrix above.

### Agent returns generic errors
```bash
# Check service health
curl http://localhost:9302/api/health
curl http://localhost:9340/health
curl http://localhost:9341/health

# Check logs
docker compose logs hie-agent-runner --tail=50
docker compose logs hie-prompt-manager --tail=50
```

### Audit log shows no entries
Ensure `ENABLE_HOOKS=true` is set for the agent-runner (it is by default in docker-compose.yml). Hooks must be enabled for audit logging to fire.

### Skills or templates not showing
```bash
# Seed skills and templates
curl -X POST http://localhost:9341/seed/skills
curl -X POST http://localhost:9341/seed/templates
```

---

## Automated E2E Verification

After any demo or code change, run the automated test suites:

```bash
# Quick smoke test (5 tests)
./scripts/run_e2e_tests.sh tests/e2e/test_api_smoke.py

# v1.9.4 RBAC/Audit suite (38 tests)
./scripts/run_e2e_tests.sh tests/e2e/test_v194_rbac_audit_approvals.py

# v1.9.5 Snapshots/CRUD suite (29 tests)
./scripts/run_e2e_tests.sh tests/e2e/test_v195_snapshots_crud_envdeploy.py
```

All tests run inside Docker on the `hie_hie-network` — never on the host macOS.

---

*OpenLI HIE v1.9.7 — The First GenAI-Native Integration Engine*
*Licensed under AGPL-3.0 or Commercial by Lightweight Integration Ltd*
