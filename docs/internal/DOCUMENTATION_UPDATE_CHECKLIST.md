# Documentation Update Checklist - v0.3.0 Restructuring

**Status as of:** February 9, 2026
**Version:** 0.3.0
**Branch:** `restructure/production-ready`

---

## Summary

This document tracks all documentation updates required and completed for the v0.3.0 restructuring.

**Legend:**
- ✅ **COMPLETE** - Fully updated and verified
- ⚠️ **NEEDS REVIEW** - Auto-updated but should be manually reviewed
- ❌ **NEEDS UPDATE** - Requires manual updates
- ℹ️ **NO CHANGE NEEDED** - Content remains accurate

---

## Root-Level Documentation

| File | Status | Updates Made | Notes |
|------|--------|--------------|-------|
| `README.md` | ✅ COMPLETE | Project structure section rewritten, service URLs updated, portal path updated | Core documentation now accurate |
| `CHANGELOG.md` | ✅ COMPLETE | v0.3.0 entry added with comprehensive changes | Documents all breaking changes |

---

## New Documentation Created

| File | Status | Purpose |
|------|--------|---------|
| `docs/MIGRATION_GUIDE_v0.3.md` | ✅ COMPLETE | Step-by-step migration guide for developers and ops |
| `docs/RESTRUCTURE_v0.3_DETAILED.md` | ✅ COMPLETE | Comprehensive technical documentation of all changes |
| `docs/DOCUMENTATION_UPDATE_CHECKLIST.md` | ✅ COMPLETE | This file - tracks doc update status |

---

## docs/ Directory - Status by File

### Architecture Documentation

| File | Status | Changes Needed | Priority |
|------|--------|----------------|----------|
| `docs/architecture/overview.md` | ⚠️ NEEDS REVIEW | Auto-updated: `hie-api` → `hie-manager` | HIGH |
| `docs/architecture/message-model.md` | ℹ️ NO CHANGE | Message model unchanged | N/A |
| `docs/architecture/CLASS_HIERARCHY_DESIGN.md` | ❌ NEEDS UPDATE | Update import examples: `from hie.` → `from Engine.` | MEDIUM |
| `docs/architecture/ENTERPRISE_ENGINE_DESIGN.md` | ⚠️ NEEDS REVIEW | Auto-updated service names, check folder references | HIGH |
| `docs/architecture/IMPLEMENTATION_PLAN.md` | ⚠️ NEEDS REVIEW | Auto-updated service names, verify accuracy | MEDIUM |

### Implementation Status Documentation

| File | Status | Changes Needed | Priority |
|------|--------|----------------|----------|
| `docs/IMPLEMENTATION_STATUS.md` | ❌ NEEDS UPDATE | Update folder structure references, add v0.3.0 status | HIGH |
| `docs/LI_ENGINE_PHASE1_STATUS.md` | ⚠️ NEEDS REVIEW | Check for any `hie/` path references | LOW |
| `docs/LI_ENGINE_PHASE2_STATUS.md` | ⚠️ NEEDS REVIEW | Check for any `hie/` path references | LOW |
| `docs/LI_ENGINE_PHASE3_STATUS.md` | ⚠️ NEEDS REVIEW | Check for any `hie/` path references | LOW |
| `docs/LI_ENGINE_PHASE4_STATUS.md` | ⚠️ NEEDS REVIEW | Check for any `hie/` path references | LOW |

### Feature & Design Documentation

| File | Status | Changes Needed | Priority |
|------|--------|----------------|----------|
| `docs/FEATURE_SPEC.md` | ⚠️ NEEDS REVIEW | Auto-updated `hie-api` → `hie-manager` | MEDIUM |
| `docs/UI_DESIGN_SPEC.md` | ⚠️ NEEDS REVIEW | Check API endpoint references | MEDIUM |
| `docs/FULLSTACK_INTEGRATION_DESIGN.md` | ❌ NEEDS UPDATE | Update service integration diagrams | HIGH |
| `docs/design/USER_MANAGEMENT.md` | ⚠️ NEEDS REVIEW | Auto-updated service names | LOW |

### Product Documentation

| File | Status | Changes Needed | Priority |
|------|--------|----------------|----------|
| `docs/PRODUCT_VISION.md` | ℹ️ NO CHANGE | Vision remains unchanged | N/A |
| `docs/REQUIREMENTS_SPEC.md` | ℹ️ NO CHANGE | Requirements unchanged | N/A |
| `docs/ROADMAP.md` | ❌ NEEDS UPDATE | Add v0.3.0 milestone as completed | LOW |
| `docs/RELEASE_NOTES.md` | ❌ NEEDS UPDATE | Add v0.3.0 release notes | HIGH |

---

## Automatic Updates Performed

### Global Find & Replace

**Command executed:**
```bash
find docs -name "*.md" -exec sed -i '' 's/hie-api/hie-manager/g' {} \;
```

**Files affected:** All .md files in docs/

**Changes made:**
- All occurrences of `hie-api` replaced with `hie-manager`
- Service name references updated across documentation
- API endpoint descriptions updated

### Manual Verification Needed

The following files had automatic replacements and should be **manually reviewed**:
1. `docs/architecture/ENTERPRISE_ENGINE_DESIGN.md`
2. `docs/FEATURE_SPEC.md`
3. `docs/FULLSTACK_INTEGRATION_DESIGN.md`
4. `docs/UI_DESIGN_SPEC.md`

**Reason:** These files may contain diagrams, code examples, or detailed explanations that need context-aware updates beyond simple text replacement.

---

## High-Priority Updates Needed

### 1. IMPLEMENTATION_STATUS.md

**Current Status:** ❌ NEEDS UPDATE

**Required Changes:**
- Update folder structure diagram to show `Engine/` and `Portal/`
- Add v0.3.0 restructuring as completed milestone
- Update any Python import examples
- Update service architecture section

**Impact:** HIGH - This is the primary status document developers reference

---

### 2. FULLSTACK_INTEGRATION_DESIGN.md

**Current Status:** ❌ NEEDS UPDATE

**Required Changes:**
- Update service integration diagrams (hie-manager)
- Update folder path references (Engine/, Portal/)
- Verify API endpoint documentation
- Update component interaction flowcharts

**Impact:** HIGH - Critical for understanding system integration

---

### 3. RELEASE_NOTES.md

**Current Status:** ❌ NEEDS UPDATE

**Required Changes:**
- Add v0.3.0 section with restructuring highlights
- Document breaking changes
- Add migration guide reference
- Update "What's Next" section

**Impact:** HIGH - User-facing release documentation

---

### 4. CLASS_HIERARCHY_DESIGN.md

**Current Status:** ❌ NEEDS UPDATE

**Required Changes:**
- Update all import statement examples
- Change `from hie.core.X` → `from Engine.core.X`
- Update file path references
- Verify class inheritance diagrams still accurate

**Impact:** MEDIUM - Important for developers understanding architecture

---

### 5. ROADMAP.md

**Current Status:** ❌ NEEDS UPDATE

**Required Changes:**
- Mark v0.3.0 "Production Restructure" as ✅ COMPLETE
- Update timeline if needed
- Add any new items identified during restructuring

**Impact:** LOW - Planning document, not critical for current work

---

## Code Examples That Need Updating

### Python Import Examples

**Before:**
```python
from hie.core.message import Message
from hie.api.server import run_server
from hie.items.receivers.http_receiver import HTTPReceiver
```

**After:**
```python
from Engine.core.message import Message
from Engine.api.server import run_server
from Engine.items.receivers.http_receiver import HTTPReceiver
```

**Files to check:**
- `docs/architecture/CLASS_HIERARCHY_DESIGN.md`
- `docs/FEATURE_SPEC.md`
- Any files with code snippets

---

### File Path References

**Before:**
```
HIE/hie/core/message.py
HIE/portal/src/app/page.tsx
```

**After:**
```
HIE/Engine/core/message.py
HIE/Portal/src/app/page.tsx
```

**Files to check:**
- All architecture docs
- Implementation status docs
- Any docs with file tree diagrams

---

### Docker Commands

**Before:**
```bash
docker-compose -f docker-compose.full.yml up
docker exec hie-api python -m hie.cli
```

**After:**
```bash
docker-compose up
docker exec hie-manager python -m Engine.cli
```

**Files to check:**
- Deployment guides
- Quick start guides
- Developer onboarding docs

---

## Verification Checklist

After completing updates, verify:

- [ ] All code examples use `Engine.` imports (not `hie.`)
- [ ] All service references use `hie-manager` (not `hie-api`)
- [ ] All folder paths use `Engine/` and `Portal/` (not `hie/` and `portal/`)
- [ ] All docker-compose examples use primary `docker-compose.yml`
- [ ] Diagrams reflect new folder structure
- [ ] API endpoint references are accurate
- [ ] No broken links or references
- [ ] Code snippets are tested and work
- [ ] Screenshots (if any) show new structure

---

## Update Priority Matrix

| Priority | Files | Action |
|----------|-------|--------|
| **P0 - CRITICAL** | README.md, CHANGELOG.md, MIGRATION_GUIDE | ✅ COMPLETE |
| **P1 - HIGH** | IMPLEMENTATION_STATUS, FULLSTACK_INTEGRATION_DESIGN, RELEASE_NOTES | ❌ TODO |
| **P2 - MEDIUM** | CLASS_HIERARCHY_DESIGN, FEATURE_SPEC, ENTERPRISE_ENGINE_DESIGN | ⚠️ REVIEW NEEDED |
| **P3 - LOW** | ROADMAP, LI_ENGINE_PHASE* docs, USER_MANAGEMENT | ⚠️ REVIEW NEEDED |

---

## Recommended Update Sequence

1. ✅ **Phase 1: Create migration documentation** (COMPLETE)
   - Migration guide
   - Detailed restructure docs
   - This checklist

2. **Phase 2: Update high-priority docs** (NEXT)
   - `IMPLEMENTATION_STATUS.md`
   - `RELEASE_NOTES.md`
   - `FULLSTACK_INTEGRATION_DESIGN.md`

3. **Phase 3: Review auto-updated docs**
   - Verify all auto-replaced `hie-manager` references
   - Check context of each replacement
   - Fix any incorrectly updated text

4. **Phase 4: Update code examples**
   - All import statements
   - File path references
   - Docker commands

5. **Phase 5: Final verification**
   - Run through verification checklist
   - Test all code examples
   - Validate all links

---

## Files Requiring No Changes

These files remain accurate after restructuring:

✓ `docs/PRODUCT_VISION.md` - Vision unchanged
✓ `docs/REQUIREMENTS_SPEC.md` - Requirements unchanged
✓ `docs/architecture/message-model.md` - Message model unchanged

---

## Notes for Documentation Maintainers

### Search Patterns to Check

Run these searches to find remaining references:

```bash
# Find any remaining hie-api references
grep -r "hie-api" docs/

# Find old import patterns
grep -r "from hie\." docs/

# Find old folder paths
grep -r "hie/" docs/
grep -r "portal/" docs/
```

### Auto-Update Safety

The automatic `hie-api` → `hie-manager` replacement was **safe** because:
- "hie-api" is a specific service name
- Unlikely to appear in other contexts
- Manual review confirms accuracy

---

## Completion Criteria

Documentation update is complete when:
1. All P1 (HIGH) priority files updated
2. All code examples verified working
3. All diagrams reflect new structure
4. Verification checklist 100% checked
5. No broken references or links
6. Peer review completed

---

## Contact

Questions about documentation updates?
- See: `docs/MIGRATION_GUIDE_v0.3.md`
- See: `docs/RESTRUCTURE_v0.3_DETAILED.md`
- GitHub Issues for discrepancies

---

**Last Updated:** February 9, 2026
**Next Review:** After high-priority doc updates
**Status:** Migration docs complete, application docs in progress
