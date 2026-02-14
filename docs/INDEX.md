# OpenLI HIE — Documentation Index

**Version:** 1.8.2
**Last Updated:** February 13, 2026

---

## Directory Structure

```
docs/
├── index.md                          ← You are here
├── api/                              ← API endpoint documentation
├── architecture/                     ← Technical architecture & engine design
├── design/                           ← Product vision, roadmaps, UX/UI design
├── guides/                           ← User-facing how-to guides & tutorials
├── internal/                         ← Dev-only: phase status, checklists, migration
├── reference/                        ← Settings, specs, testing guides
├── releases/                         ← Release notes per version
└── requirements/                     ← Requirements specifications
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
| [Message Model Session Analysis](architecture/MESSAGE_MODEL_SESSION_ANALYSIS.md) | Session tracking gaps & meta message model architecture |
| [Session ID Design](architecture/SESSION_ID_DESIGN.md) | Enterprise session ID tracking for sequence diagram visualization |
| [**MessageHeader & Body Redesign**](architecture/MESSAGE_HEADER_BODY_REDESIGN.md) | **Revised message model: IRIS/Rhapsody/Mirth-compatible, one-row-per-leg design** |
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
| [Topology Viewer UX/UI Design](design/TOPOLOGY_VIEWER_UXUI_DESIGN.md) | Production topology viewer design |
| [Visual Production Diagram](design/VISUAL_PRODUCTION_DIAGRAM.md) | Visual production diagram design |
| [Message Trace Swimlanes](design/MESSAGE_TRACE_SWIMLANES.md) | IRIS-style message trace swimlane design |
| [Enterprise Topology Executive Summary](design/ENTERPRISE_TOPOLOGY_EXECUTIVE_SUMMARY.md) | Enterprise-grade topology visualization overview |
| [Implementation Gap Analysis](design/IMPLEMENTATION_GAP_ANALYSIS.md) | Gap analysis between design and implementation |

## API

| Document | Description |
|----------|-------------|
| [Message Trace API](api/MESSAGE_TRACE_API.md) | Session trace and message sequence diagram API |

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
| [Testing Sequence Diagram](reference/TESTING_SEQUENCE_DIAGRAM.md) | Sequence diagram test strategy & procedures |

## Requirements

| Document | Description |
|----------|-------------|
| [Topology Viewer Requirements](requirements/TOPOLOGY_VIEWER_REQUIREMENTS.md) | Topology viewer feature requirements |

## Releases

| Document | Version | Date |
|----------|---------|------|
| [Release Notes v1.8.2](releases/RELEASE_NOTES_v1.8.2.md) | 1.8.2 | 2026-02-13 |
| [Sequence Diagram Delivery](releases/SEQUENCE_DIAGRAM_DELIVERY.md) | 1.8.1 | 2026-02-12 |
| [Release Notes v1.8.1](releases/RELEASE_NOTES_v1.8.1.md) | 1.8.1 | 2026-02-12 |
| [Release Notes v1.8.0](releases/RELEASE_NOTES_v1.8.0.md) | 1.8.0 | 2026-02-11 |
| [Release Notes v1.7.5](releases/RELEASE_NOTES_v1.7.5.md) | 1.7.5 | 2026-02-11 |
| [Release Notes v1.7.4](releases/RELEASE_NOTES_v1.7.4.md) | 1.7.4 | 2026-02-11 |
| [Release Notes v1.0-v1.3](releases/RELEASE_NOTES_v1.0-v1.3.md) | 1.0-1.3 | 2026-01-25 |

## Internal (Dev-Only)

| Document | Description |
|----------|-------------|
| [Phase 1 Status](internal/PHASE1_STATUS.md) | Phase 1 completion report |
| [Phase 2 Status](internal/PHASE2_STATUS.md) | Phase 2 completion report |
| [Phase 3 Status](internal/PHASE3_STATUS.md) | Phase 3 completion report |
| [Phase 4 Status](internal/PHASE4_STATUS.md) | Phase 4 completion report |
| [Implementation Progress](internal/IMPLEMENTATION_PROGRESS.md) | Sprint-level progress tracking |
| [Implementation Status](internal/IMPLEMENTATION_STATUS.md) | Feature-level status tracking |
| [Message Model Implementation Complete](internal/MESSAGE_MODEL_IMPLEMENTATION_COMPLETE.md) | Message model metadata implementation report |
| [Session ID Implementation Summary](internal/SESSION_ID_IMPLEMENTATION_SUMMARY.md) | Session ID propagation implementation report |
| [Mandatory Guidelines](internal/MANDATORY_IMPLEMENTATION_GUIDELINES.md) | Technical implementation requirements |
| [Due Diligence Summary](internal/DUE_DILIGENCE_SUMMARY.md) | v0.3.0 due diligence checks |
| [Import Verification](internal/IMPORT_VERIFICATION_REPORT.md) | Python import verification (v0.3.0) |
| [Documentation Checklist](internal/DOCUMENTATION_UPDATE_CHECKLIST.md) | v0.3.0 doc update checklist |
| [Migration Guide v0.3](internal/MIGRATION_GUIDE_v0.3.md) | v0.2 to v0.3 migration |
| [Restructure v0.3 Detail](internal/RESTRUCTURE_v0.3_DETAILED.md) | v0.3.0 restructuring details |

---

*OpenLI HIE — Healthcare Integration Engine*
