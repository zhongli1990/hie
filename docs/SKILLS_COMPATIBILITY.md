# HIE Skills - Claude & Codex Compatibility

**Last Updated:** February 11, 2026
**Status:** ✅ **Skills Successfully Shared Between Runners**

---

## Overview

Both Claude agent-runner and Codex runner use the **same SKILL.md format**, enabling HIE-specific skills to be shared across both AI runners with minimal adaptation.

## Skill Format Comparison

### Claude Agent-Runner

**Location:** `/app/skills/` (mounted from `agent-runner/skills/`)
**Frontmatter:**
```yaml
---
name: hl7-route-builder
description: Build end-to-end HL7/FHIR integration routes...
allowed-tools: hie_list_workspaces, hie_create_workspace...  # Claude-specific
user-invocable: true                                          # Claude-specific
version: "2.0"                                                # Claude-specific
---
```

### Codex SDK

**Location:** `$CODEX_HOME/skills/` (defaults to `/root/.codex/skills/`)
**Frontmatter:**
```yaml
---
name: hl7-route-builder
description: Build end-to-end HL7/FHIR integration routes...  # Standard
---
```

**Key Differences:**
- Claude uses additional frontmatter fields for tool permissions and versioning
- Codex uses minimal frontmatter (just `name` and `description`)
- Both use Markdown body with the same structure

---

## Ported HIE Skills

All 5 HIE skills are now available in **both** Claude and Codex runners:

| Skill | Description | Source |
|-------|-------------|--------|
| **hl7-route-builder** | Build end-to-end HL7/FHIR integration routes | agent-runner/skills |
| **fhir-mapper** | Transform and map FHIR resources | agent-runner/skills |
| **clinical-safety-review** | NHS clinical safety compliance checks | agent-runner/skills |
| **integration-test** | Test HIE integration routes | agent-runner/skills |
| **nhs-compliance-check** | Validate NHS compliance requirements | agent-runner/skills |

---

## Porting Process

### Automated Script

Use the provided script to port skills from Claude to Codex:

```bash
./scripts/port-skills-to-codex.sh
```

**What it does:**
1. Copies skills from `agent-runner/skills/` to temporary directory
2. Strips Claude-specific frontmatter fields (`allowed-tools`, `user-invocable`, `version`)
3. Copies clean skills to Codex container at `/root/.codex/skills/`
4. Restarts Codex runner to load new skills

### Manual Porting (if needed)

1. **Copy skill directory:**
   ```bash
   cp -r agent-runner/skills/hl7-route-builder /tmp/hl7-route-builder
   ```

2. **Edit SKILL.md frontmatter:**
   Remove these lines from YAML frontmatter:
   ```yaml
   allowed-tools: ...
   user-invocable: ...
   version: ...
   ```

3. **Copy to Codex container:**
   ```bash
   docker cp /tmp/hl7-route-builder hie-codex-runner:/root/.codex/skills/
   ```

4. **Restart Codex:**
   ```bash
   docker restart hie-codex-runner
   ```

---

## Verification

### Check Skills in Claude Runner

```bash
docker exec hie-agent-runner ls /app/skills/
```

Expected output:
```
clinical-safety-review
fhir-mapper
hl7-route-builder
integration-test
nhs-compliance-check
```

### Check Skills in Codex Runner

```bash
docker exec hie-codex-runner ls /root/.codex/skills/
```

Expected output:
```
.system                    # Codex system skills (preinstalled)
clinical-safety-review     # HIE skill
fhir-mapper                # HIE skill
hl7-route-builder          # HIE skill
integration-test           # HIE skill
nhs-compliance-check       # HIE skill
```

### Test Skills in UI

**In Agents Page:**
1. Select **Claude Agent** runner
2. Ask: "Can you help me build an HL7 route for ADT messages?"
3. ✅ Claude should invoke `hl7-route-builder` skill

**Then switch to:**
1. Select **OpenAI Agent (Codex)** runner
2. Ask: "Can you help me build an HL7 route for ADT messages?"
3. ✅ Codex should also invoke `hl7-route-builder` skill

---

## Skill Triggering

### Claude Agent-Runner

- Uses `allowed-tools` to restrict which HIE Manager API tools the skill can call
- Checks `user-invocable` flag to determine if skill can be manually invoked
- Triggers based on `description` field matching user intent

### Codex SDK

- Triggers purely based on `description` field matching user intent
- Automatically loads skill body after triggering
- Can use built-in tools (bash, file operations) + skill-specific scripts

---

## Adding New Skills

### Option 1: Create in Claude Format (Recommended)

1. **Create skill directory:**
   ```bash
   mkdir -p agent-runner/skills/my-new-skill
   ```

2. **Create SKILL.md with Claude frontmatter:**
   ```yaml
   ---
   name: my-new-skill
   description: Description of what the skill does and when to use it
   allowed-tools: hie_list_workspaces, hie_create_project
   user-invocable: true
   version: "1.0"
   ---

   # My New Skill

   Skill body content...
   ```

3. **Port to Codex:**
   ```bash
   ./scripts/port-skills-to-codex.sh
   ```

### Option 2: Create Directly in Codex Container

1. **Use Codex skill-installer:**
   In Agents page with Codex runner, ask:
   ```
   "Can you help me create a new skill for [task description]?"
   ```

2. **Codex will guide you through:**
   - Initializing skill structure
   - Writing SKILL.md
   - Adding scripts/references/assets
   - Packaging the skill

3. **Export and add to Claude:**
   ```bash
   # Export from Codex
   docker cp hie-codex-runner:/root/.codex/skills/my-new-skill ./agent-runner/skills/

   # Add Claude-specific frontmatter
   # Edit ./agent-runner/skills/my-new-skill/SKILL.md
   # Add: allowed-tools, user-invocable, version

   # Restart Claude runner
   docker restart hie-agent-runner
   ```

---

## Architecture Notes

### Claude Agent-Runner (Python-based)

- **Framework:** Custom Python skill loader
- **Skills Location:** `/app/skills` (mounted volume)
- **Environment Variable:** `GLOBAL_SKILLS_PATH=/app/skills`
- **Tool Restriction:** `allowed-tools` frontmatter field
- **Loader:** `app/skills.py` in agent-runner

### Codex SDK (Markdown-based)

- **Framework:** OpenAI Codex SDK with built-in skill system
- **Skills Location:** `$CODEX_HOME/skills` (defaults to `~/.codex/skills`)
- **System Skills:** `.system/skill-installer`, `.system/skill-creator`
- **Progressive Loading:** Metadata → SKILL.md → References/Scripts as needed
- **Tool Access:** Built-in bash, file operations, custom scripts in `scripts/`

---

## Best Practices

### Writing Skills for Both Runners

1. **Use standard frontmatter:**
   - Always include `name` and `description`
   - Add Claude-specific fields only in Claude source
   - Let porting script handle cleanup

2. **Keep skills portable:**
   - Don't rely on runner-specific features in skill body
   - Use clear, imperative instructions
   - Include examples and workflows

3. **Test in both runners:**
   - Verify skill triggers correctly in Claude
   - Port and verify in Codex
   - Ensure consistent behavior

4. **Maintain single source:**
   - Keep master skills in `agent-runner/skills/`
   - Use porting script to sync to Codex
   - Don't edit skills directly in Codex container

---

## Troubleshooting

### Skill Not Triggering in Codex

**Symptoms:** Codex doesn't invoke skill when expected

**Solutions:**
1. Check skill is in container:
   ```bash
   docker exec hie-codex-runner ls /root/.codex/skills/
   ```

2. Verify SKILL.md frontmatter:
   ```bash
   docker exec hie-codex-runner head -10 /root/.codex/skills/[skill-name]/SKILL.md
   ```
   - Should have `name` and `description` fields
   - Should NOT have `allowed-tools` or other Claude-specific fields

3. Restart Codex runner:
   ```bash
   docker restart hie-codex-runner
   ```

4. Ask Codex to list skills:
   In Agents page: "What skills are available?"

### Skill Not Triggering in Claude

**Symptoms:** Claude doesn't invoke skill when expected

**Solutions:**
1. Check `GLOBAL_SKILLS_PATH` is set:
   ```bash
   docker exec hie-agent-runner env | grep GLOBAL_SKILLS_PATH
   ```

2. Verify skill exists:
   ```bash
   docker exec hie-agent-runner ls /app/skills/
   ```

3. Check `allowed-tools` frontmatter includes required tools

4. Restart Claude runner:
   ```bash
   docker restart hie-agent-runner
   ```

---

## Success Criteria

✅ **Skills Shared:** All 5 HIE skills available in both Claude and Codex runners
✅ **Frontmatter Compatible:** Claude-specific fields stripped for Codex
✅ **Triggers Work:** Skills invoke correctly in both runners
✅ **Portable Format:** Single source in `agent-runner/skills/`, synced to Codex
✅ **Automated Porting:** Script handles conversion and deployment

---

## Future Enhancements

1. **Bi-directional Sync:** Support creating skills in Codex and porting back to Claude
2. **CI/CD Integration:** Automatically port skills on commit to `agent-runner/skills/`
3. **Skill Validation:** Pre-deployment checks for frontmatter compatibility
4. **Version Management:** Track skill versions across both runners

---

*This document is maintained by the HIE Core Team.*
