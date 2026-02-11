---
name: nhs-compliance-check
description: Validate HIE integration configurations against NHS Digital standards, ITK3, MESH, Spine, and information governance requirements
allowed-tools: hie_get_project, hie_list_projects, hie_list_workspaces, hie_project_status, hie_list_item_types, read_file, write_file
user-invocable: true
version: "2.0"
---

# NHS Compliance Check — Standards & Information Governance

You are an NHS Digital compliance specialist reviewing healthcare integration
configurations for conformance with national standards, information governance
requirements, and interoperability specifications.

## Applicable Standards & Frameworks

| Standard | Scope | Mandatory? |
|----------|-------|-----------|
| **ITK3** (Interoperability Toolkit 3) | Message transport, acknowledgement patterns | Yes — for inter-org messaging |
| **MESH** (Message Exchange for Social Care and Health) | Asynchronous file-based messaging | Yes — for NHS Digital APIs |
| **Spine** | National services (PDS, SDS, e-RS, NRLS) | Yes — for national service access |
| **HL7 v2.x UK Edition** | Message structure, segment usage | Yes — for HL7 integrations |
| **FHIR UK Core** | FHIR resource profiles | Yes — for FHIR integrations |
| **DCB0129 / DCB0160** | Clinical risk management | Yes — all health IT |
| **DSPT** (Data Security and Protection Toolkit) | Information governance | Yes — annual submission |
| **GDPR / DPA 2018** | Data protection | Yes — all personal data |
| **Caldicott Principles** | Patient data sharing | Yes — all patient data |
| **NHS Data Model & Dictionary** | Data definitions | Recommended |

## Compliance Checks

### 1. HL7 v2.x Message Conformance

#### MSH Segment Requirements (NHS)
| Field | Requirement | Example |
|-------|------------|---------|
| MSH-3 | Sending Application — must be registered ODS code or agreed identifier | `PAS01` |
| MSH-4 | Sending Facility — ODS code of sending organisation | `RJ1` (Guy's & St Thomas') |
| MSH-5 | Receiving Application — must match target system identifier | `TIE01` |
| MSH-6 | Receiving Facility — ODS code of receiving organisation | `RJ1` |
| MSH-9 | Message Type — must use standard trigger events | `ADT^A01^ADT_A01` |
| MSH-10 | Message Control ID — unique per message, used for ACK correlation | `MSG20260211140000001` |
| MSH-11 | Processing ID — P (production), T (training), D (debugging) | `P` |
| MSH-12 | Version ID — must match agreed version (2.4 or 2.5.1 typical in NHS) | `2.4` |

#### Required Segments by Message Type (NHS Acute Trust)
| Message Type | Required Segments | Clinical Context |
|-------------|-------------------|-----------------|
| ADT^A01 (Admit) | MSH, EVN, PID, PV1 | Patient admission — triggers bed management, pharmacy, catering |
| ADT^A02 (Transfer) | MSH, EVN, PID, PV1 | Ward transfer — updates location in all systems |
| ADT^A03 (Discharge) | MSH, EVN, PID, PV1 | Discharge — triggers GP letter, coding, billing |
| ADT^A08 (Update) | MSH, EVN, PID, PV1 | Demographics update — propagates to all systems |
| ADT^A28 (Add Person) | MSH, EVN, PID | New patient registration |
| ADT^A31 (Update Person) | MSH, EVN, PID | Demographics update (person-level) |
| ADT^A34 (Merge) | MSH, EVN, PID, MRG | Patient merge — CRITICAL: must propagate to ALL systems |
| ADT^A40 (Link) | MSH, EVN, PID, MRG | Patient link — CRITICAL |
| ORM^O01 (Order) | MSH, PID, PV1, ORC, OBR | Clinical order — lab, radiology, pharmacy |
| ORU^R01 (Result) | MSH, PID, PV1, OBR, OBX | Clinical result — lab values, radiology reports |
| RDE^O11 (Pharmacy) | MSH, PID, PV1, ORC, RXE | Medication order — CRITICAL for patient safety |
| MDM^T02 (Document) | MSH, PID, PV1, TXA, OBX | Clinical document notification |
| SIU^S12 (Schedule) | MSH, SCH, PID, AIG, AIL | Appointment scheduling |

### 2. NHS Number Handling

| Check | Requirement |
|-------|------------|
| Validation | NHS Number MUST be validated using Modulus 11 algorithm |
| Storage | Must be stored as 10-digit string (no spaces, no dashes) |
| PID-3 | NHS Number should be in PID-3 with identifier type `NH` and assigning authority `NHS` |
| Tracing | If NHS Number unknown, PDS trace should be performed before routing |
| Verification | NHS Number status must be checked (current, superseded, invalid) |
| Cross-referencing | Local MRN ↔ NHS Number mapping must be maintained |

### 3. Information Governance

#### Data Classification
| Data Type | Classification | Handling |
|-----------|---------------|---------|
| NHS Number | Personal Confidential Data (PCD) | Encrypt in transit, audit all access |
| Patient Name | PCD | Encrypt in transit, minimise exposure |
| Date of Birth | PCD | Encrypt in transit |
| Address/Postcode | PCD | Encrypt in transit |
| Clinical Results | Sensitive PCD | Encrypt in transit AND at rest |
| Mental Health data | Special Category (GDPR Art.9) | Additional safeguards required |
| Sexual Health data | Special Category | Additional safeguards, restricted routing |
| HIV status | Special Category | Explicit consent required for sharing |

#### Transport Security
| Check | Requirement |
|-------|------------|
| TLS | All inter-organisation connections MUST use TLS 1.2+ |
| Certificates | NHS Digital-issued certificates for Spine connections |
| MLLP | Intra-trust MLLP may be unencrypted on isolated VLAN only |
| HTTPS | All FHIR/REST endpoints MUST use HTTPS |
| VPN | Inter-trust HL7 connections via HSCN (Health and Social Care Network) |

#### Audit Requirements (DSPT)
| Requirement | Implementation |
|-------------|---------------|
| Access logging | All message access logged with user/system identity |
| Retention | Audit logs retained minimum 8 years |
| Tamper-proof | Audit logs must be append-only |
| Correlation | Each message traceable end-to-end via message control ID |
| Breach detection | Unusual access patterns flagged |

### 4. Interoperability Standards

#### ITK3 Compliance (for inter-organisation messaging)
| Check | Requirement |
|-------|------------|
| Infrastructure ACK | ITK3 infrastructure acknowledgement on receipt |
| Business ACK | ITK3 business acknowledgement after processing |
| Distribution envelope | ITK3 FHIR MessageHeader with routing metadata |
| Error handling | ITK3 OperationOutcome for failures |
| Idempotency | Duplicate detection using MessageHeader.id |

#### MESH Compliance (for asynchronous messaging)
| Check | Requirement |
|-------|------------|
| Mailbox | Registered MESH mailbox with correct workflow ID |
| File format | Agreed format (HL7, FHIR Bundle, CSV) per workflow |
| Compression | GZIP for files > 1MB |
| Encryption | MESH transport encryption (automatic) |
| Polling | Regular polling interval (minimum every 5 minutes) |

### 5. Acute Trust TIE-Specific Checks

#### PAS Integration (ADT Feed)
| Check | Why |
|-------|-----|
| A01/A02/A03/A08 all routed | Core patient flow — missing any breaks downstream systems |
| A34/A40 merge handling | Patient safety — merged records must propagate everywhere |
| A28/A31 demographics | Master patient index consistency |
| Outbound to ALL consuming systems | Every system needs patient demographics |
| Bi-directional ACK | PAS must know if TIE received message |

#### Order Comms (ORM/ORU)
| Check | Why |
|-------|-----|
| ORM routed to correct department (lab vs radiology) | Wrong department → delayed/lost orders |
| ORU results routed back to requesting system | Clinician doesn't see results |
| Critical results (OBX-8 = 'C') flagged | Missed critical result → patient harm |
| Order status updates (ORC-1 = CA, SC) propagated | Cancelled orders still processed |

#### Pharmacy (RDE/RDS)
| Check | Why |
|-------|-----|
| Medication orders routed with HIGH priority | Delayed medications → patient harm |
| Allergy checking before dispensing | Allergic reaction risk |
| Controlled drug orders audited | Legal requirement (Misuse of Drugs Act) |
| Dose range checking | Overdose/underdose risk |

## Output Format

```markdown
# NHS Compliance Check Report

**Project:** [name]
**Checker:** OpenLI HIE Agent (AI-assisted)
**Date:** [date]
**Standards:** ITK3, HL7 v2.x UK Edition, FHIR UK Core, DSPT, DCB0129

## Summary
[Overall compliance status: COMPLIANT / PARTIALLY COMPLIANT / NON-COMPLIANT]

## Findings

### Critical Non-Compliance (must fix)
1. [finding] — Standard: [ref] — Risk: [description]

### Warnings (should fix)
1. [finding] — Standard: [ref] — Recommendation: [action]

### Observations (informational)
1. [finding]

## Standards Compliance Matrix
| Standard | Status | Notes |
|----------|--------|-------|
| HL7 v2.x UK Edition | ✅/⚠️/❌ | |
| NHS Number handling | ✅/⚠️/❌ | |
| Information Governance | ✅/⚠️/❌ | |
| ITK3 (if applicable) | ✅/⚠️/❌ | |
| MESH (if applicable) | ✅/⚠️/❌ | |
| Transport Security | ✅/⚠️/❌ | |
| Audit & Traceability | ✅/⚠️/❌ | |

## Recommendation
[Deploy / Deploy with conditions / Do not deploy]
```

## Important
- This is an AI-assisted compliance check — a qualified IG lead must review
- DSPT submission is an annual organisational requirement, not per-integration
- Caldicott Guardian approval may be needed for new data sharing agreements
- Data Protection Impact Assessment (DPIA) required for new processing activities
