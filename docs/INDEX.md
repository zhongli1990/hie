# OpenLI HIE — Documentation Index

**Version:** 1.7.5
**Last Updated:** February 11, 2026

---

## Directory Structure

```
docs/
├── INDEX.md                          ← You are here
├── architecture/                     ← Technical architecture & engine design
├── design/                           ← Product vision, roadmaps, design proposals
├── guides/                           ← User-facing how-to guides & tutorials
├── internal/                         ← Dev-only: phase status, checklists, migration
├── reference/                        ← Settings, specs, API, testing
└── releases/                         ← Release notes per version
```

---

## Guides (Start Here)

| Document | Audience | Description |
|----------|----------|-------------|
| [Developer & User Guide](guides/DEVELOPER_AND_USER_GUIDE.md) | All | **Primary guide** — quickstart, NHS scenario, custom classes, GenAI agent |
| [UI Configuration Guide](guides/UI_CONFIGURATION_GUIDE.md) | Users | Portal UI settings reference (Phase 2 enterprise settings) |
| [Custom Classes Guide](guides/CUSTOM_CLASSES_GUIDE.md) | Developers | Writing custom.* host classes, namespace rules, hot-reload |
| [NHS Trust Demo Guide](guides/NHS_TRUST_DEMO_GUIDE.md) | All | Complete NHS acute trust reference implementation |
| [Developer Workflow Scenarios](guides/DEVELOPER_WORKFLOW_SCENARIOS.md) | Developers | 8 workflow scenarios vs IRIS/Rhapsody/Mirth |

## Architecture

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture/ARCHITECTURE_OVERVIEW.md) | Executive summary of HIE platform |
| [Core Principles](architecture/CORE_PRINCIPLES.md) | Foundational design principles |
| [Class Hierarchy Design](architecture/CLASS_HIERARCHY_DESIGN.md) | Python class hierarchy (Host, Adapter, Item) |
| [Enterprise Engine Design](architecture/ENTERPRISE_ENGINE_DESIGN.md) | Workflow engine architecture |
| [Scalability Architecture](architecture/SCALABILITY_ARCHITECTURE.md) | Scaling strategy & assessment |
| [Message Model](architecture/MESSAGE_MODEL.md) | Message envelope design (Phase 4) |
| [Message Envelope Design](architecture/MESSAGE_ENVELOPE_DESIGN.md) | Polymorphic messaging architecture |
| [Engine Implementation Plan](architecture/ENGINE_IMPLEMENTATION_PLAN.md) | LI Engine implementation plan |
| [Optimization Plan](architecture/OPTIMIZATION_PLAN.md) | Phase 4-6 optimization strategy |
| [Meta-Instantiation Plan](architecture/META_INSTANTIATION_PLAN.md) | Meta-instantiation & message uplift |
| [Architecture QA Review](architecture/ARCHITECTURE_QA_REVIEW.md) | Design assessment & QA review |

## Design

| Document | Description |
|----------|-------------|
| [Product Vision](design/PRODUCT_VISION.md) | Strategic positioning & market vision |
| [Product Roadmap](design/PRODUCT_ROADMAP.md) | Technical roadmap (Phase 3-6) |
| [Development Roadmap](design/DEVELOPMENT_ROADMAP.md) | Development status & progress |
| [Fullstack Integration Design](design/FULLSTACK_INTEGRATION_DESIGN.md) | Full-stack integration proposal |
| [UI Design Specification](design/UI_DESIGN_SPECIFICATION.md) | Enterprise UI design spec |
| [User Management](design/USER_MANAGEMENT.md) | Identity & access management design |

## Reference

| Document | Description |
|----------|-------------|
| [Configuration Reference](reference/CONFIGURATION_REFERENCE.md) | All configuration options |
| [Message Routing Workflow](reference/MESSAGE_ROUTING_WORKFLOW.md) | E2E routing implementation details (v1.7.5) |
| [Message Patterns Specification](reference/MESSAGE_PATTERNS_SPECIFICATION.md) | Messaging patterns for enterprise integration |
| [Feature Specification](reference/FEATURE_SPECIFICATION.md) | Complete feature set |
| [Requirements Specification](reference/REQUIREMENTS_SPECIFICATION.md) | Technical requirements |
| [Skills Compatibility](reference/SKILLS_COMPATIBILITY.md) | Claude & Codex skill format compatibility |
| [Testing Guide](reference/TESTING_GUIDE.md) | Test suites & Docker-based testing |

## Releases

| Document | Version | Date |
|----------|---------|------|
| [Release Notes v1.7.5](releases/RELEASE_NOTES_v1.7.5.md) | 1.7.5 | 2026-02-11 |
| [Release Notes v1.7.4](releases/RELEASE_NOTES_v1.7.4.md) | 1.7.4 | 2026-02-11 |
| [Release Notes v1.8.0](releases/RELEASE_NOTES_v1.8.0.md) | 1.8.0 | 2026-02-11 |
| [Release Notes v1.0–v1.3](releases/RELEASE_NOTES_v1.0-v1.3.md) | 1.0–1.3 | 2026-01-25 |

## Internal (Dev-Only)

| Document | Description |
|----------|-------------|
| [Phase 1 Status](internal/PHASE1_STATUS.md) | Phase 1 completion report |
| [Phase 2 Status](internal/PHASE2_STATUS.md) | Phase 2 completion report |
| [Phase 3 Status](internal/PHASE3_STATUS.md) | Phase 3 completion report |
| [Phase 4 Status](internal/PHASE4_STATUS.md) | Phase 4 completion report |
| [Implementation Progress](internal/IMPLEMENTATION_PROGRESS.md) | Sprint-level progress tracking |
| [Implementation Status](internal/IMPLEMENTATION_STATUS.md) | Feature-level status tracking |
| [Mandatory Guidelines](internal/MANDATORY_IMPLEMENTATION_GUIDELINES.md) | Technical implementation requirements |
| [Due Diligence Summary](internal/DUE_DILIGENCE_SUMMARY.md) | v0.3.0 due diligence checks |
| [Import Verification](internal/IMPORT_VERIFICATION_REPORT.md) | Python import verification (v0.3.0) |
| [Documentation Checklist](internal/DOCUMENTATION_UPDATE_CHECKLIST.md) | v0.3.0 doc update checklist |
| [Migration Guide v0.3](internal/MIGRATION_GUIDE_v0.3.md) | v0.2 → v0.3 migration |
| [Restructure v0.3 Detail](internal/RESTRUCTURE_v0.3_DETAILED.md) | v0.3.0 restructuring details |

---

## Consolidation Plan

The following documents have significant overlap and should be consolidated in a future cleanup pass:

### High Priority — Merge

| Action | Documents | Rationale |
|--------|-----------|-----------|
| **Merge** | `design/PRODUCT_ROADMAP.md` + `design/DEVELOPMENT_ROADMAP.md` | Both are roadmaps — one is product-level, one is dev-level. Consolidate into a single `design/ROADMAP.md`. |
| **Merge** | `architecture/MESSAGE_MODEL.md` + `architecture/MESSAGE_ENVELOPE_DESIGN.md` | Both describe the message model/envelope. MESSAGE_MODEL is the Phase 4 design; MESSAGE_ENVELOPE_DESIGN is the polymorphic architecture. Consolidate into `architecture/MESSAGE_MODEL.md`. |
| **Merge** | `internal/IMPLEMENTATION_PROGRESS.md` + `internal/IMPLEMENTATION_STATUS.md` | Both track implementation status at different granularities. Consolidate into a single `internal/IMPLEMENTATION_STATUS.md`. |
| **Merge** | `architecture/ENGINE_IMPLEMENTATION_PLAN.md` + `architecture/OPTIMIZATION_PLAN.md` + `architecture/META_INSTANTIATION_PLAN.md` | Three overlapping implementation/uplift plans. Consolidate into `architecture/ENGINE_IMPLEMENTATION_PLAN.md`. |

### Medium Priority — Review & Prune

| Action | Documents | Rationale |
|--------|-----------|-----------|
| **Review** | `internal/PHASE1_STATUS.md` through `PHASE4_STATUS.md` | Historical phase reports. Consider archiving or merging into a single `internal/PHASE_HISTORY.md` since all phases are complete. |
| **Review** | `internal/DUE_DILIGENCE_SUMMARY.md`, `IMPORT_VERIFICATION_REPORT.md`, `DOCUMENTATION_UPDATE_CHECKLIST.md` | One-time v0.3.0 artifacts. Consider archiving to `internal/archive/` or removing. |
| **Review** | `internal/RESTRUCTURE_v0.3_DETAILED.md`, `MIGRATION_GUIDE_v0.3.md` | v0.3 migration docs — no longer needed for current users. Archive. |
| **Review** | `reference/FEATURE_SPECIFICATION.md` + `reference/REQUIREMENTS_SPECIFICATION.md` | Significant overlap between features and requirements. Consider merging into `reference/PRODUCT_SPECIFICATION.md`. |

### Low Priority — Keep As-Is

| Document | Rationale |
|----------|-----------|
| All `guides/*` | Each serves a distinct audience/purpose. No overlap. |
| All `releases/*` | Version-specific, should remain separate per release. |
| `architecture/ARCHITECTURE_OVERVIEW.md` | Standalone executive summary. |
| `architecture/CLASS_HIERARCHY_DESIGN.md` | Unique technical reference. |
| `architecture/SCALABILITY_ARCHITECTURE.md` | Unique scaling assessment. |
| `reference/MESSAGE_ROUTING_WORKFLOW.md` | New v1.7.5 doc, no overlap. |
| `reference/CONFIGURATION_REFERENCE.md` | Unique settings reference. |

### Summary

| Priority | Merges | Files Reduced |
|----------|--------|---------------|
| High | 4 merges | 45 → 38 (−7 files) |
| Medium | 3 archives | 38 → 32 (−6 files to archive) |
| **Total** | | **45 → 32 files** |

---

*OpenLI HIE — Healthcare Integration Engine*
