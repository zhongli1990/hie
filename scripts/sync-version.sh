#!/usr/bin/env bash
# =============================================================================
# OpenLI HIE — Version Sync Script
#
# Reads the canonical version from the root VERSION file and propagates it
# to every file that cannot read it dynamically at runtime.
#
# Files that DO NOT need this script (they read VERSION or HIE_VERSION at runtime):
#   - Engine/__init__.py          → reads HIE_VERSION env var
#   - agent-runner/app/main.py    → reads HIE_VERSION env var
#   - prompt-manager/app/main.py  → reads HIE_VERSION env var
#   - codex-runner/src/server.ts  → reads HIE_VERSION env var
#   - Portal AboutModal           → reads NEXT_PUBLIC_HIE_VERSION env var
#   - pyproject.toml              → hatchling reads VERSION file at build time
#   - setup.py                    → reads VERSION file at build time
#   - docker-compose.yml          → reads HIE_VERSION from .env
#   - docker-compose.dev.yml      → reads HIE_VERSION from .env
#   - E2E tests + conftest.py     → reads HIE_VERSION env var (injected by run_e2e_tests.sh)
#
# Files this script DOES update (static text that can't read from a file):
#   - .env                        → HIE_VERSION=x.y.z
#   - Portal/package.json         → "version": "x.y.z"
#   - README.md                   → version badge + version line
#   - docs/INDEX.md               → version header
#   - docs/guides/*.md            → version headers
#
# Usage:
#   ./scripts/sync-version.sh          # Sync all files
#   ./scripts/sync-version.sh --check  # Dry run — show what's out of sync
#
# After a release, the only manual steps are:
#   1. Edit VERSION file
#   2. Add entry to Portal/src/components/AboutModal.tsx versionHistory array
#   3. Run ./scripts/sync-version.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Read canonical version
if [ ! -f "$PROJECT_ROOT/VERSION" ]; then
    echo "ERROR: VERSION file not found at $PROJECT_ROOT/VERSION"
    exit 1
fi
VERSION=$(tr -d '[:space:]' < "$PROJECT_ROOT/VERSION")

if [ -z "$VERSION" ]; then
    echo "ERROR: VERSION file is empty"
    exit 1
fi

CHECK_MODE=false
if [ "${1:-}" = "--check" ]; then
    CHECK_MODE=true
fi

DIRTY=0

# ─── Helper: update a file using sed ──────────────────────────────────────────

sync_file() {
    local file="$1"
    local pattern="$2"
    local replacement="$3"
    local label="$4"

    if [ ! -f "$file" ]; then
        echo "  SKIP  $label (file not found)"
        return
    fi

    if grep -qF "$replacement" "$file" 2>/dev/null; then
        echo "  OK    $label → $VERSION"
    else
        DIRTY=1
        if $CHECK_MODE; then
            echo "  STALE $label — needs update to $VERSION"
        else
            sed -i '' "$pattern" "$file" 2>/dev/null || sed -i "$pattern" "$file"
            echo "  SYNC  $label → $VERSION"
        fi
    fi
}

# ─── .env — HIE_VERSION=x.y.z ────────────────────────────────────────────────

echo ""
echo "━━━ Syncing version $VERSION from VERSION file ━━━"
echo ""

ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "^HIE_VERSION=$VERSION$" "$ENV_FILE" 2>/dev/null; then
        echo "  OK    .env HIE_VERSION → $VERSION"
    else
        DIRTY=1
        if $CHECK_MODE; then
            echo "  STALE .env HIE_VERSION — needs update to $VERSION"
        else
            if grep -q "^HIE_VERSION=" "$ENV_FILE"; then
                sed -i '' "s/^HIE_VERSION=.*/HIE_VERSION=$VERSION/" "$ENV_FILE" 2>/dev/null || \
                sed -i "s/^HIE_VERSION=.*/HIE_VERSION=$VERSION/" "$ENV_FILE"
            else
                echo "HIE_VERSION=$VERSION" >> "$ENV_FILE"
            fi
            echo "  SYNC  .env HIE_VERSION → $VERSION"
        fi
    fi
else
    DIRTY=1
    if $CHECK_MODE; then
        echo "  STALE .env — file missing, needs HIE_VERSION=$VERSION"
    else
        echo "HIE_VERSION=$VERSION" > "$ENV_FILE"
        echo "  SYNC  .env created with HIE_VERSION=$VERSION"
    fi
fi

# ─── Portal/package.json ─────────────────────────────────────────────────────

sync_file "$PROJECT_ROOT/Portal/package.json" \
    "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" \
    "\"version\": \"$VERSION\"" \
    "Portal/package.json"

# ─── README.md — version badge ───────────────────────────────────────────────

sync_file "$PROJECT_ROOT/README.md" \
    "s/version-[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/version-$VERSION/" \
    "version-$VERSION" \
    "README.md badge"

# ─── README.md — version line ────────────────────────────────────────────────

sync_file "$PROJECT_ROOT/README.md" \
    "s/\*\*Version:\*\* [0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/\*\*Version:\*\* $VERSION/" \
    "**Version:** $VERSION" \
    "README.md version line"

# ─── docs/INDEX.md ────────────────────────────────────────────────────────────

sync_file "$PROJECT_ROOT/docs/INDEX.md" \
    "s/\*\*Version:\*\* [0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/\*\*Version:\*\* $VERSION/" \
    "**Version:** $VERSION" \
    "docs/INDEX.md"

# ─── docs/guides/DEMO_LIFECYCLE_GUIDE.md ──────────────────────────────────────

sync_file "$PROJECT_ROOT/docs/guides/DEMO_LIFECYCLE_GUIDE.md" \
    "s/\*\*Version:\*\* [0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/\*\*Version:\*\* $VERSION/" \
    "**Version:** $VERSION" \
    "DEMO_LIFECYCLE_GUIDE.md"

# ─── docs/guides/DEVELOPER_AND_USER_GUIDE.md ─────────────────────────────────

sync_file "$PROJECT_ROOT/docs/guides/DEVELOPER_AND_USER_GUIDE.md" \
    "s/\*\*Version:\*\* [0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*/\*\*Version:\*\* $VERSION/" \
    "**Version:** $VERSION" \
    "DEVELOPER_AND_USER_GUIDE.md"

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
if [ $DIRTY -eq 0 ]; then
    echo "✓ All files in sync with VERSION $VERSION"
elif $CHECK_MODE; then
    echo "✗ Some files are out of sync — run ./scripts/sync-version.sh to fix"
    exit 1
else
    echo "✓ All files synced to VERSION $VERSION"
fi
echo ""
