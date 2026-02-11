#!/bin/bash
# Port HIE Skills from Claude agent-runner to Codex runner
# Strips Claude-specific frontmatter and copies to Codex container

set -e

SKILLS_SOURCE="/Users/zhong/Downloads/CascadeProjects/HIE/agent-runner/skills"
TEMP_DIR="/tmp/codex-skills-$$"
CONTAINER_NAME="hie-codex-runner"
CODEX_SKILLS_PATH="/root/.codex/skills"

echo "🔄 Porting HIE Skills from Claude agent-runner to Codex runner..."
echo ""

# Create temp directory
mkdir -p "$TEMP_DIR"

# Process each skill
for skill_dir in "$SKILLS_SOURCE"/*; do
  if [ -d "$skill_dir" ]; then
    skill_name=$(basename "$skill_dir")
    echo "📦 Processing: $skill_name"

    # Create skill directory in temp
    mkdir -p "$TEMP_DIR/$skill_name"

    # Copy all files
    cp -r "$skill_dir"/* "$TEMP_DIR/$skill_name/"

    # Strip Claude-specific frontmatter from SKILL.md
    if [ -f "$TEMP_DIR/$skill_name/SKILL.md" ]; then
      # Use sed to remove Claude-specific fields from YAML frontmatter
      sed -i '' '/^allowed-tools:/d; /^user-invocable:/d; /^version:/d' "$TEMP_DIR/$skill_name/SKILL.md"
      echo "  ✓ Stripped Claude-specific frontmatter"
    fi
  fi
done

echo ""
echo "📤 Copying skills to Codex container..."

# Copy all skills to Codex container
docker exec "$CONTAINER_NAME" mkdir -p "$CODEX_SKILLS_PATH"
docker cp "$TEMP_DIR/." "$CONTAINER_NAME:$CODEX_SKILLS_PATH/"

echo "  ✓ Skills copied to container"

# Clean up temp directory
rm -rf "$TEMP_DIR"

echo ""
echo "✅ Skills ported successfully!"
echo ""
echo "Ported skills:"
for skill_dir in "$SKILLS_SOURCE"/*; do
  if [ -d "$skill_dir" ]; then
    echo "  • $(basename "$skill_dir")"
  fi
done

echo ""
echo "🔄 Restarting Codex runner to load new skills..."
docker restart "$CONTAINER_NAME"

echo ""
echo "✅ Done! Skills are now available in both Claude and Codex runners."
echo ""
echo "Test by asking in Agents page (with Codex runner selected):"
echo "  'Can you help me build an HL7 route?'"
