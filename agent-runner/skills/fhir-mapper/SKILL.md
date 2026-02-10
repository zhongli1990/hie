---
name: fhir-mapper
description: Map between HL7 v2.x messages and FHIR R4 resources for OpenLI HIE
allowed-tools: Read, Write, Bash, hie_create_item, hie_list_item_types
user-invocable: true
version: "1.0"
---

# FHIR Mapper

You are an expert at mapping between HL7 v2.x messages and FHIR R4 resources.

## Common Mappings

### ADT to FHIR Patient
- PID.3 → Patient.identifier (MRN)
- PID.5 → Patient.name (HumanName)
- PID.7 → Patient.birthDate
- PID.8 → Patient.gender
- PID.11 → Patient.address
- PID.13 → Patient.telecom (phone)
- PID.19 → Patient.identifier (NHS Number)

### ADT to FHIR Encounter
- PV1.2 → Encounter.class
- PV1.3 → Encounter.location
- PV1.19 → Encounter.identifier (visit number)
- PV1.44 → Encounter.period.start
- PV1.45 → Encounter.period.end

### ORM to FHIR ServiceRequest
- ORC.1 → ServiceRequest.intent
- OBR.4 → ServiceRequest.code
- OBR.7 → ServiceRequest.occurrenceDateTime
- ORC.12 → ServiceRequest.requester

### ORU to FHIR DiagnosticReport + Observation
- OBR.4 → DiagnosticReport.code
- OBX.3 → Observation.code
- OBX.5 → Observation.value
- OBX.6 → Observation.valueQuantity.unit
- OBX.7 → Observation.referenceRange
- OBX.11 → Observation.status

## NHS-Specific Considerations
- NHS Number goes in Patient.identifier with system "https://fhir.nhs.uk/Id/nhs-number"
- ODS Code for organizations: system "https://fhir.nhs.uk/Id/ods-organization-code"
- Use UK Core FHIR profiles where available
- Validate against CareConnect or UK Core profiles
