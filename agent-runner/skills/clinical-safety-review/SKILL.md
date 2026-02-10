---
name: clinical-safety-review
description: Review HIE configurations for clinical safety compliance (DCB0129/DCB0160)
allowed-tools: Read, hie_get_project, hie_list_item_types
user-invocable: true
version: "1.0"
---

# Clinical Safety Review

You are a clinical safety reviewer for healthcare integration configurations.
Review HIE projects against NHS Digital DCB0129 and DCB0160 standards.

## Safety Checklist

### Message Integrity
- [ ] All inbound services have acknowledgement configured
- [ ] Error handling connections exist for all critical paths
- [ ] Message validation is enabled before routing
- [ ] No message loss scenarios (async queuing for unreachable targets)

### Patient Safety
- [ ] PID segments are not modified without clinical validation
- [ ] Patient matching logic uses NHS Number + demographics
- [ ] Duplicate message detection is enabled
- [ ] Message ordering is preserved for time-critical messages (e.g., medication orders)

### Data Quality
- [ ] HL7 message structure validation on inbound
- [ ] Required segments are checked (MSH, PID, PV1 minimum)
- [ ] Character encoding is consistent (UTF-8 recommended)
- [ ] Date/time formats follow ISO 8601 or HL7 DTM

### Audit & Traceability
- [ ] All messages are logged with correlation IDs
- [ ] Configuration changes are tracked
- [ ] Error messages are captured with full context
- [ ] Message content is archived for clinical audit

### Availability
- [ ] Retry logic configured for outbound operations
- [ ] Graceful degradation for non-critical downstream systems
- [ ] Health monitoring enabled for all items
- [ ] Alerting configured for message failures

## Risk Classification
- **High**: Patient identification, medication orders, critical results
- **Medium**: Appointments, referrals, administrative messages
- **Low**: Non-clinical notifications, system status messages
