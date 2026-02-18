# OpenLI HIE — Natural Language Integration Lifecycle Demo Guide

**Version:** 1.9.4
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
git checkout feature/nl-development-rbac

# Fresh start (recommended for demos)
docker compose down -v
docker compose up -d --build

# Wait for all services to be healthy (~60s)
docker compose ps
```

### 2. Verify Services

| Service | URL | Port |
|---------|-----|------|
| Portal (UI) | http://localhost:9303 | 9303 |
| Manager API | http://localhost:9302/api/health | 9302 |
| Agent Runner | http://localhost:9340/health | 9340 |
| Prompt Manager | http://localhost:9341/health | 9341 |
| PostgreSQL | localhost:9310 | 9310 |
| Redis | localhost:9311 | 9311 |
| MLLP Echo | localhost:9320 | 9320 |

### 3. Verify Demo Data

```bash
# Check demo users exist (Python avoids shell JSON escaping issues)
python3 -c "
import urllib.request, json
data = json.dumps({'email': 'developer@sth.nhs.uk', 'password': 'Demo12345!'}).encode()
req = urllib.request.Request('http://localhost:9302/api/auth/login', data=data,
      headers={'Content-Type': 'application/json'}, method='POST')
resp = urllib.request.urlopen(req)
d = json.loads(resp.read().decode())
print(f'Login OK: {d[\"user\"][\"display_name\"]} ({d[\"user\"][\"role_name\"]})')
"
```

You should see `Login OK: James Chen (Integration Engineer)` confirming the demo users are seeded.

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
3. You should see:
   - Role badge: **Integration Developer** (green)
   - Capabilities panel showing: Design, Build, Test, Monitor
   - Quick Start templates filtered for developer role

### Step 1: Design the Integration

Navigate to the **Agents** page (sidebar). Click **"Guided Workflow"** to enter lifecycle mode, or type directly into the chat:

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

### Step 2: Build the Complete Integration

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
1. `hie_create_item` × 4 — Creates the service, process, and both operations with correct class names (`li.hosts.hl7.HL7TCPService`, `li.hosts.routing.HL7RoutingEngine`, `li.hosts.hl7.HL7TCPOperation`)
2. `hie_create_connection` × 3 — Wires Receiver→Router, Router→RIS, Router→EPR
3. `hie_create_routing_rule` × 2 — Creates HL7 condition expressions:
   - `{MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A02","A03")` → RIS
   - `{MSH-9.1} = "ADT" AND {MSH-9.2} IN ("A01","A03")` → EPR

### Step 3: Test the Integration

```
Test this integration by sending sample HL7 ADT messages:
1. Send an A01 admission for patient John Smith, NHS number 943 476 5919
2. Send an A02 transfer for the same patient
3. Send an A03 discharge

Tell me which messages went to which targets.
```

**What the AI does:**
1. `hie_test_item` × 3 — Generates valid HL7 v2.4 messages with correct MSH, PID, PV1 segments and sends them through the inbound service
2. Reports routing results: A01 → RIS + EPR, A02 → RIS only, A03 → RIS + EPR
3. **PII sanitisation**: The audit log records this action but the NHS number `943 476 5919` is replaced with `[NHS_NUMBER]` before storage

### Step 4: Attempt Production Deploy (RBAC in Action)

```
This looks good. Deploy it to production.
```

**What happens:**
- The AI agent **cannot see** the `hie_deploy_project` tool — it's not in the developer's permitted tool set
- The agent responds: *"I've built and tested the integration successfully. However, as an Integration Developer, I don't have permission to deploy to production. Production deployments require approval from a Clinical Safety Officer or Tenant Admin. I'll create a deployment approval request."*
- The agent-runner hook creates a `DeploymentApproval` record with status `pending`
- **Every tool call above has been logged** to the audit trail with user, role, action, and PII-sanitised input/output

---

## ACT 2: CLINICAL SAFETY REVIEW (CSO)

### Login

1. **Log out** of the developer account
2. Login as: **`cso@sth.nhs.uk`** / **`Demo12345!`**
3. You should see:
   - Role badge: **Clinical Safety Officer** (purple)
   - Capabilities: Test, Review, Approve/Reject, Monitor

### Step 5: Review the Integration

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

### Step 6: Test as CSO

```
Send a test A01 admission through the route so I can verify the
message flow independently.
```

**What the AI does:**
- CSOs have `hie_test_item` permission — they can independently verify routing
- `hie_test_item` sends a test message and the CSO sees the routing result
- This is logged as a CSO action in the audit trail

### Step 7: Approve the Deployment

**Via Portal UI:**
1. Navigate to **Admin > Approvals** in the sidebar
2. You'll see the pending approval request from James Chen (developer)
3. Review the config snapshot (expandable detail view)
4. Click **Approve**, enter review notes: *"DCB0129 review passed. All 32 safety criteria met. ADT routing logic verified. Approved for production."*
5. The approval status changes to **Approved** (green)

**Or via natural language:**
```
Approve the pending deployment for the Cerner ADT Integration.
Add review notes: "DCB0129 review passed. All routing rules verified
against NHS ADT specification. PII sanitisation confirmed. Approved."
```

---

## ACT 3: DEPLOY & MONITOR (Operator)

### Login

1. **Log out** of the CSO account
2. Login as: **`operator@sth.nhs.uk`** / **`Demo12345!`**
3. You should see:
   - Role badge: **Operator** (cyan)
   - Capabilities: Deploy, Start, Stop, Monitor — no build access

### Step 8: Deploy to Production

```
Deploy the approved Cerner ADT Integration to production and start
all items.
```

**What the AI does:**
1. `hie_list_workspaces` → `hie_list_projects` — Finds the approved project
2. `hie_deploy_project` — Deploys the configuration to the HIE Engine
3. `hie_start_project` — Starts all enabled items (receiver, router, senders)
4. `hie_project_status` — Confirms all 4 items are running

### Step 9: Monitor

```
Show me the status of all running integrations at St Thomas'.
Include queue depths, error counts, and connection health.
```

**What the AI does:**
1. `hie_project_status` — Returns runtime metrics:
   - Receiver: Running, 0 messages queued
   - Router: Running, 0 pending evaluations
   - RIS Sender: Running, connected to 10.0.1.50:5002
   - EPR Sender: Running, connected to 10.0.1.60:5003

### Step 10: Operational Commands

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
2. Role badge: **Auditor** (indigo)

### Step 11: Review Audit Trail

**Via Portal UI:**
1. Navigate to **Admin > Audit Log**
2. See the complete chronological record of every AI agent action:
   - Stats cards: Total actions, Successes, Denied, Errors
   - Filter by: Action type, User, Date range, Status
   - Expandable detail rows showing sanitised input/output
   - CSV export for compliance reporting

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

---

## ACT 5: ADMIN OVERVIEW (Trust Admin)

### Login

1. Login as: **`trust.admin@sth.nhs.uk`** / **`Demo12345!`**
2. Role badge: **Tenant Admin** (blue)

### Step 12: Full Lifecycle in One Session

Trust admins have full access within their tenant. They can do the entire lifecycle in a single session:

```
Show me everything in the St Thomas' workspace — all projects,
their status, recent audit entries, and any pending approvals.
```

**What the AI does:**
- Full tool access within tenant scope
- Lists all projects, statuses, audit statistics
- Shows pending approvals (if any)

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
| **GR-1 Role-Based Tool Access** | ACTIVE | 7 roles with defense-in-depth (Layer 1: tool filtering, Layer 2: hook validation) |
| **GR-2 Audit Logging** | ACTIVE | Every AI tool call logged with PII sanitisation (NHS numbers, postcodes) |
| **GR-3 Approval Workflows** | ACTIVE | Production deploys require CSO/Admin approval — developers cannot bypass |
| **GR-4 Configuration Snapshots** | Planned | Rollback capability (Phase 5) |
| **GR-5 Tenant Isolation** | ACTIVE | Users can only access their own tenant's workspaces |
| **GR-6 Namespace Enforcement** | ACTIVE | Core `li.*` classes read-only; developers write to `custom.*` only |

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

---

## Automated E2E Verification

After any demo or code change, run the automated test suite:

```bash
# 38 tests covering the complete lifecycle
make test-e2e-v194

# Quick smoke test
make test-e2e-smoke
```

All tests run inside Docker — never on the host macOS.

---

*OpenLI HIE v1.9.4 — The First GenAI-Native Integration Engine*
*Licensed under AGPL-3.0 or Commercial by Lightweight Integration Ltd*
