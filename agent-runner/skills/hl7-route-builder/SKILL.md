---
name: hl7-route-builder
description: Build HL7 v2.x message routing configurations for OpenLI HIE
allowed-tools: Read, Write, Bash, hie_create_item, hie_create_connection, hie_deploy_project, hie_list_item_types
user-invocable: true
version: "1.0"
---

# HL7 Route Builder

You are an expert at building HL7 v2.x message routing configurations for OpenLI HIE.

## Common HL7 Route Patterns

### ADT (Admit/Discharge/Transfer) Route
1. **Inbound Service**: `Engine.li.hosts.hl7.HL7TCPService` - Receives HL7 messages via MLLP/TCP
   - Key settings: `port`, `ackMode` (auto/manual), `charSet`
2. **Routing Process**: `Engine.li.hosts.routing.RoutingEngine` - Routes based on MSH.9 message type
   - Rules: Match on MSH.9.1 (message type) and MSH.9.2 (trigger event)
3. **Outbound Operation**: `Engine.li.hosts.hl7.HL7TCPOperation` - Sends via MLLP to downstream systems
   - Key settings: `host`, `port`, `retryCount`, `retryInterval`

### ORM (Order) Route
1. Inbound: HL7TCPService on dedicated port
2. Process: RoutingEngine with ORM/O01 filtering
3. Outbound: HL7TCPOperation to order management system

### ORU (Results) Route
1. Inbound: HL7TCPService or FileService for batch results
2. Process: Transform + Route based on OBR segment
3. Outbound: Multiple operations for different result consumers

## HL7 Message Structure Reference
- **MSH**: Message Header (MSH.9 = message type, MSH.10 = control ID)
- **PID**: Patient Identification (PID.3 = patient ID, PID.5 = patient name)
- **PV1**: Patient Visit (PV1.2 = patient class, PV1.3 = assigned location)
- **OBR**: Observation Request (OBR.4 = universal service ID)
- **OBX**: Observation Result (OBX.3 = observation identifier)

## Best Practices
- Always use dedicated ports per message type (ADT: 10001, ORM: 10002, ORU: 10003)
- Enable auto-acknowledgement for standard routes
- Add error connections for failed message handling
- Use async connections for non-critical downstream systems
- Log all messages for audit compliance
