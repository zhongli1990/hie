---
name: integration-test
description: Generate and execute integration tests for HIE route configurations
allowed-tools: Read, Write, Bash, hie_test_item, hie_get_project
user-invocable: true
version: "1.0"
---

# Integration Test

You help generate and execute integration tests for HIE route configurations.

## Test Message Templates

### ADT A01 (Admit)
```
MSH|^~\&|SENDER|FACILITY|RECEIVER|FACILITY|{{timestamp}}||ADT^A01|{{controlId}}|P|2.4
EVN|A01|{{timestamp}}
PID|1||{{patientId}}^^^MRN||{{lastName}}^{{firstName}}||{{dob}}|{{gender}}|||{{address}}
PV1|1|I|{{ward}}^{{bed}}^{{room}}||||{{attendingDr}}|||||||||||{{visitNumber}}
```

### ORM O01 (Order)
```
MSH|^~\&|SENDER|FACILITY|RECEIVER|FACILITY|{{timestamp}}||ORM^O01|{{controlId}}|P|2.4
PID|1||{{patientId}}^^^MRN||{{lastName}}^{{firstName}}
ORC|NW|{{orderNumber}}|||||||{{timestamp}}|||{{orderingDr}}
OBR|1|{{orderNumber}}||{{testCode}}^{{testName}}|||{{timestamp}}
```

### ORU R01 (Result)
```
MSH|^~\&|LAB|FACILITY|RECEIVER|FACILITY|{{timestamp}}||ORU^R01|{{controlId}}|P|2.4
PID|1||{{patientId}}^^^MRN||{{lastName}}^{{firstName}}
OBR|1|{{orderNumber}}||{{testCode}}^{{testName}}|||{{collectionTime}}
OBX|1|NM|{{obsCode}}^{{obsName}}||{{value}}|{{units}}|{{refRange}}|{{abnFlag}}|||F
```

## Test Scenarios
1. **Happy Path**: Send valid message, verify ACK received
2. **Routing Test**: Send message matching routing rule, verify delivery to correct target
3. **Error Handling**: Send malformed message, verify error connection triggered
4. **Load Test**: Send N messages rapidly, verify all processed
5. **Failover Test**: Stop target, send message, verify retry/queue behaviour

## Validation Checks
- ACK message received with AA (Application Accept)
- Message appears in portal message log
- Correct routing to expected target
- No data loss or corruption
- Latency within acceptable bounds (<500ms for standard routes)
