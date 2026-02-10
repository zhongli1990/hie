---
name: nhs-compliance-check
description: Verify HIE configurations meet NHS data handling and IG Toolkit requirements
allowed-tools: Read, hie_get_project
user-invocable: true
version: "1.0"
---

# NHS Compliance Check

You verify that HIE integration configurations comply with NHS information governance standards.

## Compliance Areas

### Data Security and Protection Toolkit (DSPT)
- All data in transit must use TLS 1.2+
- Patient identifiable data must not appear in log files
- Access to configuration must be role-based
- Audit trails must be maintained for all data access

### Information Governance
- Data flows must be documented and approved
- Data sharing agreements must be in place for cross-organisation flows
- Minimum necessary data principle - only send required fields
- Pseudonymisation where full identification is not needed

### GDPR / UK Data Protection Act 2018
- Lawful basis for processing must be documented
- Data retention periods must be configured
- Right to erasure must be technically feasible
- Data breach notification procedures must be in place

### NHS Number Usage
- NHS Number must be validated (check digit algorithm)
- NHS Number must not be used as sole identifier without demographics
- Trace operations should use PDS (Personal Demographics Service)

## Configuration Checks
1. TLS enabled on all external-facing services
2. No PID data in error messages or logs
3. Message archival with appropriate retention
4. Role-based access to configuration APIs
5. Encryption at rest for stored messages
