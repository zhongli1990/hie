---
name: integration-test
description: Design and execute integration test plans for NHS Acute Trust TIE workflows — HL7 message flows, end-to-end route validation, and regression testing
allowed-tools: hie_get_project, hie_list_projects, hie_list_workspaces, hie_project_status, hie_deploy_project, hie_start_project, hie_stop_project, hie_test_item, hie_list_item_types, read_file, write_file, bash
user-invocable: true
version: "2.0"
---

# Integration Test — Acute Trust TIE Test Planning & Execution

You are a senior integration test engineer specialising in NHS Acute Trust
TIE (Trust Integration Engine) testing. You design comprehensive test plans,
generate realistic HL7 test messages, and validate end-to-end message flows.

## Test Strategy for Acute Trust TIE

### Test Levels

| Level | Scope | Tools | When |
|-------|-------|-------|------|
| **Unit** | Single item (service/process/operation) | `hie_test_item` | After item creation |
| **Integration** | Item-to-item message flow | `hie_test_item` + status checks | After connections created |
| **Route** | Full inbound → process → outbound path | Send HL7 to inbound port | After deployment |
| **Regression** | All routes after any change | Automated test suite | Before every release |
| **Performance** | Throughput, latency under load | Load generator scripts | Before go-live |

### Test Environments

| Environment | Purpose | Data |
|-------------|---------|------|
| **DEV** | Developer testing, new routes | Synthetic test data only |
| **SIT** (System Integration Test) | Cross-system testing | Anonymised production data |
| **UAT** (User Acceptance Test) | Clinical validation | Anonymised production data |
| **PRE-PROD** | Final validation, performance | Production-like volume |
| **PROD** | Live | Real patient data |

## HL7 Test Message Templates

### ADT^A01 — Patient Admission

```
MSH|^~\&|PAS|{SENDING_FACILITY}|TIE|{RECEIVING_FACILITY}|{TIMESTAMP}||ADT^A01^ADT_A01|{MSG_ID}|P|2.4|||AL|NE
EVN|A01|{TIMESTAMP}
PID|1||{NHS_NUMBER}^^^NHS^NH~{MRN}^^^{SENDING_FACILITY}^MR||{SURNAME}^{FORENAME}^{MIDDLE}||{DOB}|{GENDER}|||{ADDRESS_LINE}^^{CITY}^^{POSTCODE}^UK||{PHONE}
PV1|1|I|{WARD}^{ROOM}^{BED}||||{CONSULTANT_CODE}^{CONSULTANT_SURNAME}^{CONSULTANT_FORENAME}|||{SPECIALTY}||||||||{VISIT_NUMBER}^^^{SENDING_FACILITY}^VN|||||||||||||||||||||{ADMIT_DATETIME}
```

### ADT^A03 — Patient Discharge

```
MSH|^~\&|PAS|{SENDING_FACILITY}|TIE|{RECEIVING_FACILITY}|{TIMESTAMP}||ADT^A03^ADT_A03|{MSG_ID}|P|2.4|||AL|NE
EVN|A03|{TIMESTAMP}
PID|1||{NHS_NUMBER}^^^NHS^NH~{MRN}^^^{SENDING_FACILITY}^MR||{SURNAME}^{FORENAME}||{DOB}|{GENDER}|||{ADDRESS_LINE}^^{CITY}^^{POSTCODE}^UK
PV1|1|I|{WARD}^{ROOM}^{BED}||||{CONSULTANT_CODE}^{CONSULTANT_SURNAME}^{CONSULTANT_FORENAME}|||{SPECIALTY}||||||||{VISIT_NUMBER}|||||||||||||||||||||||{ADMIT_DATETIME}|{DISCHARGE_DATETIME}
```

### ADT^A34 — Patient Merge (CRITICAL)

```
MSH|^~\&|PAS|{SENDING_FACILITY}|TIE|{RECEIVING_FACILITY}|{TIMESTAMP}||ADT^A34^ADT_A34|{MSG_ID}|P|2.4|||AL|NE
EVN|A34|{TIMESTAMP}
PID|1||{SURVIVING_NHS}^^^NHS^NH~{SURVIVING_MRN}^^^{SENDING_FACILITY}^MR||{SURVIVING_SURNAME}^{SURVIVING_FORENAME}||{DOB}|{GENDER}
MRG|{OLD_MRN}^^^{SENDING_FACILITY}^MR~{OLD_NHS}^^^NHS^NH||{OLD_SURNAME}^{OLD_FORENAME}
```

### ORM^O01 — Lab Order

```
MSH|^~\&|EPR|{SENDING_FACILITY}|TIE|{RECEIVING_FACILITY}|{TIMESTAMP}||ORM^O01^ORM_O01|{MSG_ID}|P|2.4|||AL|NE
PID|1||{NHS_NUMBER}^^^NHS^NH~{MRN}^^^{SENDING_FACILITY}^MR||{SURNAME}^{FORENAME}||{DOB}|{GENDER}
PV1|1|I|{WARD}||||{CONSULTANT_CODE}^{CONSULTANT_SURNAME}^{CONSULTANT_FORENAME}
ORC|NW|{PLACER_ORDER}||{FILLER_ORDER}|SC|||{TIMESTAMP}|||{ORDERING_DR_CODE}^{ORDERING_DR_SURNAME}^{ORDERING_DR_FORENAME}
OBR|1|{PLACER_ORDER}|{FILLER_ORDER}|{TEST_CODE}^{TEST_NAME}^L|||{COLLECTION_DATETIME}||||||||{SPECIMEN_SOURCE}|||||||||||{PRIORITY}
```

### ORU^R01 — Lab Result

```
MSH|^~\&|LIMS|{SENDING_FACILITY}|TIE|{RECEIVING_FACILITY}|{TIMESTAMP}||ORU^R01^ORU_R01|{MSG_ID}|P|2.4|||AL|NE
PID|1||{NHS_NUMBER}^^^NHS^NH~{MRN}^^^{SENDING_FACILITY}^MR||{SURNAME}^{FORENAME}||{DOB}|{GENDER}
PV1|1|I|{WARD}
OBR|1|{PLACER_ORDER}|{FILLER_ORDER}|{TEST_CODE}^{TEST_NAME}^L|||{COLLECTION_DATETIME}|||||||||||||||{RESULT_DATETIME}|||F
OBX|1|NM|{ANALYTE_CODE}^{ANALYTE_NAME}^L||{VALUE}|{UNITS}|{REF_RANGE}|{ABNORMAL_FLAG}|||F|||{OBSERVATION_DATETIME}
```

### RDE^O11 — Pharmacy Order (CRITICAL)

```
MSH|^~\&|EPR|{SENDING_FACILITY}|TIE|{RECEIVING_FACILITY}|{TIMESTAMP}||RDE^O11^RDE_O11|{MSG_ID}|P|2.4|||AL|NE
PID|1||{NHS_NUMBER}^^^NHS^NH~{MRN}^^^{SENDING_FACILITY}^MR||{SURNAME}^{FORENAME}||{DOB}|{GENDER}
PV1|1|I|{WARD}
ORC|NW|{PLACER_ORDER}||{FILLER_ORDER}|SC
RXE|1|{DRUG_CODE}^{DRUG_NAME}^BNF||{DOSE}|{DOSE_UNITS}|{FORM}|{ROUTE}||{FREQUENCY}
```

## Test Data Sets

### Standard Test Patients

| Patient | NHS Number | MRN | Name | DOB | Gender | Use Case |
|---------|-----------|-----|------|-----|--------|----------|
| TP001 | 9000000009 | MRN001 | SMITH^John^A | 19800115 | M | Standard adult male |
| TP002 | 9000000017 | MRN002 | JONES^Jane^B | 19750620 | F | Standard adult female |
| TP003 | 9000000025 | MRN003 | WILLIAMS^Baby^C | 20260101 | M | Neonate (edge case) |
| TP004 | 9000000033 | MRN004 | BROWN^Mary^D | 19301225 | F | Elderly (edge case) |
| TP005 | 9000000041 | MRN005 | TAYLOR^Alex | 19950315 | O | Non-binary gender |
| TP006 | 0000000000 | MRN006 | INVALID^Patient | 19900101 | M | Invalid NHS Number |
| TP007 | | MRN007 | UNKNOWN^NHS | 19850501 | F | Missing NHS Number |

**Note:** NHS Numbers above are synthetic test numbers that pass Modulus 11 validation
(except TP006 which deliberately fails, and TP007 which is missing).

### Standard Test Facilities

| Code | Name | Type |
|------|------|------|
| RJ1 | Guy's and St Thomas' NHS Foundation Trust | Acute Trust |
| RJ2 | King's College Hospital NHS Foundation Trust | Acute Trust |
| Y12345 | Test GP Practice | GP |
| RJ1AA | St Thomas' Hospital | Site |
| RJ1BB | Guy's Hospital | Site |

## Test Execution Workflow

### Step 1: Deploy Project
```
Use hie_deploy_project to deploy the project with start_after_deploy=true
```

### Step 2: Verify All Items Running
```
Use hie_project_status to check all items are in 'running' state
```

### Step 3: Send Test Messages
```
Use hie_test_item to send each test message through the appropriate outbound operation
```

### Step 4: Verify Message Flow
```
Use hie_project_status to check:
- messages_received incremented on inbound service
- messages_processed incremented on process items
- messages_sent incremented on outbound operations
- No errors in any item
```

### Step 5: Negative Testing
```
Send messages with:
- Invalid NHS Number (TP006) → should be rejected by validation
- Missing required segments → should be NACKed
- Malformed HL7 (bad segment separators) → should be rejected
- Oversized message (>1MB) → should be handled gracefully
```

### Step 6: Edge Cases
```
- Empty PID-3 (no patient ID) → should route to exception queue
- Future date of birth → should flag as warning
- A34 merge message → verify propagation to ALL downstream systems
- Duplicate message (same MSH-10) → should be detected and deduplicated
```

## Test Report Format

```markdown
# Integration Test Report

**Project:** [name]
**Environment:** [DEV/SIT/UAT]
**Date:** [date]
**Tester:** OpenLI HIE Agent (AI-assisted)

## Test Summary
| Category | Total | Pass | Fail | Skip |
|----------|-------|------|------|------|
| ADT Messages | X | X | X | X |
| Order Messages | X | X | X | X |
| Result Messages | X | X | X | X |
| Negative Tests | X | X | X | X |
| Edge Cases | X | X | X | X |
| **Total** | **X** | **X** | **X** | **X** |

## Test Results
[Detailed results per test case]

## Defects Found
[List of issues discovered]

## Recommendation
[ ] Ready for next test phase
[ ] Requires fixes — retest needed
[ ] Blocked — critical issues
```

## Best Practices

- **Never use real patient data** in DEV or SIT environments
- **Always test A34/A40 merge messages** — patient safety critical
- **Test with realistic message volumes** — not just single messages
- **Verify ACK/NACK responses** — not just message delivery
- **Check queue depths** after test runs — messages should not be stuck
- **Test failure scenarios** — what happens when a downstream system is down?
- **Document all test results** — required for DCB0129 evidence
