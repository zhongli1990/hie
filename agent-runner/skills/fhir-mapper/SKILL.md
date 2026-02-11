---
name: fhir-mapper
description: Map between HL7 v2.x messages and FHIR R4 resources for Acute Trust TIE integrations
allowed-tools: hie_create_item, hie_create_connection, hie_list_item_types, hie_list_projects, hie_get_project, read_file, write_file, bash
user-invocable: true
version: "2.0"
---

# FHIR Mapper — HL7 v2.x ↔ FHIR R4 Mapping Skill

You are an expert at mapping between HL7 v2.x messages and FHIR R4 resources
in the context of NHS Acute Trust TIE (Trust Integration Engine) workflows.

## Acute Trust TIE Context

In a typical NHS Acute Trust, the TIE sits between:
- **PAS** (Patient Administration System) — Cerner, Epic, System C, Meditech
- **EPR** (Electronic Patient Record) — often the same as PAS
- **RIS** (Radiology Information System) — Sectra, Agfa, CRIS
- **LIMS** (Laboratory Information Management System) — Clinisys, Sunquest
- **PDS** (Personal Demographics Service) — NHS Spine
- **NRLS** (National Record Locator Service) — NHS Digital
- **e-RS** (e-Referral Service) — NHS Digital
- **GP Connect** — NHS Digital

The TIE receives HL7 v2.x from legacy systems and must produce FHIR R4 for:
- NHS Digital APIs (PDS, NRLS, e-RS)
- GP Connect (FHIR STU3/R4)
- Inter-trust sharing via MESH/ITK3
- Clinical portals and mobile apps

## HL7 v2.x → FHIR R4 Mapping Reference

### ADT → FHIR Patient + Encounter

| HL7 v2.x Field | FHIR R4 Resource.element | Notes |
|----------------|--------------------------|-------|
| PID-3.1 | `Patient.identifier[mrn].value` | MRN with system `https://fhir.nhs.uk/Id/local-patient-identifier` |
| PID-3.1 (NHS) | `Patient.identifier[nhs].value` | NHS Number with system `https://fhir.nhs.uk/Id/nhs-number` |
| PID-5.1 | `Patient.name.family` | Family name |
| PID-5.2 | `Patient.name.given[0]` | Given name |
| PID-5.3 | `Patient.name.given[1]` | Middle name |
| PID-5.5 | `Patient.name.prefix` | Title (Mr, Mrs, Dr) |
| PID-7 | `Patient.birthDate` | Format: YYYY-MM-DD |
| PID-8 | `Patient.gender` | M→male, F→female, O→other, U→unknown |
| PID-11.1 | `Patient.address.line[0]` | Street |
| PID-11.3 | `Patient.address.city` | City |
| PID-11.5 | `Patient.address.postalCode` | UK postcode |
| PID-11.6 | `Patient.address.country` | Country code |
| PID-13 | `Patient.telecom[phone]` | system=phone |
| PID-14 | `Patient.telecom[work-phone]` | system=phone, use=work |
| PID-29 | `Patient.deceasedDateTime` | Death date |
| PV1-2 | `Encounter.class` | I→IMP, O→AMB, E→EMER, P→PRENC |
| PV1-3.1 | `Encounter.location.location` | Ward |
| PV1-3.2 | `Encounter.location.location` | Room |
| PV1-3.3 | `Encounter.location.location` | Bed |
| PV1-7 | `Encounter.participant[attender]` | Attending doctor |
| PV1-10 | `Encounter.serviceType` | Hospital service |
| PV1-19 | `Encounter.identifier[visit]` | Visit number |
| PV1-44 | `Encounter.period.start` | Admit date/time |
| PV1-45 | `Encounter.period.end` | Discharge date/time |

### ORM/OBR → FHIR ServiceRequest

| HL7 v2.x Field | FHIR R4 Resource.element | Notes |
|----------------|--------------------------|-------|
| ORC-1 | `ServiceRequest.intent` | NW→order, CA→revoked, SC→order |
| ORC-2 | `ServiceRequest.identifier[placer]` | Placer order number |
| ORC-3 | `ServiceRequest.identifier[filler]` | Filler order number |
| ORC-5 | `ServiceRequest.status` | SC→active, CM→completed, CA→revoked |
| ORC-9 | `ServiceRequest.authoredOn` | Transaction date/time |
| ORC-12 | `ServiceRequest.requester` | Ordering provider → Practitioner |
| OBR-4 | `ServiceRequest.code` | Universal service ID |
| OBR-7 | `ServiceRequest.occurrenceDateTime` | Requested date/time |
| OBR-16 | `ServiceRequest.requester` | Ordering provider (if ORC-12 empty) |
| OBR-27 | `ServiceRequest.priority` | S→stat, A→asap, R→routine |

### ORU/OBX → FHIR DiagnosticReport + Observation

| HL7 v2.x Field | FHIR R4 Resource.element | Notes |
|----------------|--------------------------|-------|
| OBR-4 | `DiagnosticReport.code` | Service ID → SNOMED/LOINC |
| OBR-7 | `DiagnosticReport.effectiveDateTime` | Observation date |
| OBR-22 | `DiagnosticReport.issued` | Results reported date |
| OBR-25 | `DiagnosticReport.status` | F→final, P→preliminary, C→corrected |
| OBX-2 | (value type) | NM→valueQuantity, ST→valueString, CE→valueCodeableConcept |
| OBX-3 | `Observation.code` | Observation identifier → LOINC/SNOMED |
| OBX-5 | `Observation.value[x]` | Result value (type from OBX-2) |
| OBX-6 | `Observation.valueQuantity.unit` | Units (UCUM preferred) |
| OBX-7 | `Observation.referenceRange` | Reference range text |
| OBX-8 | `Observation.interpretation` | H→high, L→low, A→abnormal, N→normal |
| OBX-11 | `Observation.status` | F→final, P→preliminary, C→corrected |
| OBX-14 | `Observation.effectiveDateTime` | Observation date/time |

## UK Core FHIR Profiles

When generating FHIR resources for NHS systems, use UK Core profiles:

| Resource | Profile URL |
|----------|------------|
| Patient | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient` |
| Encounter | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-Encounter` |
| Organization | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization` |
| Practitioner | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-Practitioner` |
| ServiceRequest | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-ServiceRequest` |
| DiagnosticReport | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-DiagnosticReport` |
| Observation | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-Observation` |
| AllergyIntolerance | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-AllergyIntolerance` |
| MedicationRequest | `https://fhir.hl7.org.uk/StructureDefinition/UKCore-MedicationRequest` |

## NHS Identifier Systems

| Identifier | FHIR System URI |
|-----------|----------------|
| NHS Number | `https://fhir.nhs.uk/Id/nhs-number` |
| ODS Code | `https://fhir.nhs.uk/Id/ods-organization-code` |
| ODS Site Code | `https://fhir.nhs.uk/Id/ods-site-code` |
| GMC Number | `https://fhir.hl7.org.uk/Id/gmc-number` |
| GMP Code | `https://fhir.hl7.org.uk/Id/gmp-number` |
| SDS User ID | `https://fhir.nhs.uk/Id/sds-user-id` |
| SDS Role Profile | `https://fhir.nhs.uk/Id/sds-role-profile-id` |

## Creating a FHIR Mapping Transform

When asked to create an HL7-to-FHIR mapping, create a custom transform class:

```python
# Engine/custom/myorg/adt_to_fhir_patient.py
from Engine.custom import register_transform

@register_transform("custom.myorg.ADTToFHIRPatient")
class ADTToFHIRPatient:
    """Transform HL7 ADT message to FHIR Patient resource."""
    
    def transform(self, message):
        parsed = message.parsed
        return {
            "resourceType": "Patient",
            "meta": {"profile": ["https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient"]},
            "identifier": [
                {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": parsed.get_field("PID-3.1")},
            ],
            "name": [{"family": parsed.get_field("PID-5.1"), "given": [parsed.get_field("PID-5.2")]}],
            "gender": {"M": "male", "F": "female"}.get(parsed.get_field("PID-8"), "unknown"),
            "birthDate": parsed.get_field("PID-7")[:10] if parsed.get_field("PID-7") else None,
        }
```

## Best Practices
- Always validate NHS Numbers (Modulus 11) before including in FHIR resources
- Use SNOMED CT codes where possible (NHS mandated for clinical terms)
- Use UCUM units for quantities (mmol/L, g/dL, etc.)
- Include `meta.profile` for UK Core conformance
- Map HL7 v2.x table values to FHIR ValueSets (e.g., PV1-2 patient class)
- Handle missing/null fields gracefully — FHIR resources should be valid even with partial data
- Log all mapping failures for clinical safety audit
