#!/usr/bin/env bash
# ==============================================================================
# Cyber Evidence Box (CEB) - Safe Git Update & Restart Script
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/frontend" ] && [ -d "$SCRIPT_DIR/Backend" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/../frontend" ] && [ -d "$SCRIPT_DIR/../Backend" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

cd "$PROJECT_DIR"

echo "=================================================="
echo "  CYBER EVIDENCE BOX (CEB) - SAFE UPDATE MANAGER"
echo "=================================================="
echo "[CEB] Project Location: $PROJECT_DIR"

# 1. Verify SSD mount / directory
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "ERROR: Not a valid git repository at $PROJECT_DIR"
    exit 1
fi

# 2. Check for local modifications
echo "[CEB] Checking local repository status..."
GIT_DIRTY=0
if [ -n "$(git status --porcelain)" ]; then
    GIT_DIRTY=1
fi

if [ "$GIT_DIRTY" -eq 1 ]; then
    echo ""
    echo "=================================================="
    echo "  WARNING: Local modifications detected!"
    echo "=================================================="
    git status -s
    echo ""
    echo "To protect your forensic configuration and code, updates will not be automatically merged over uncommitted files."
    echo "Please commit, stash, or review your local changes before running update-ceb.sh."
    echo "No files were modified."
    exit 1
fi

# 3. Pull latest code
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "[CEB] Fetching updates from remote repository ($CURRENT_BRANCH)..."

PREV_COMMIT=$(git rev-parse --short HEAD)
git pull origin "$CURRENT_BRANCH"
NEW_COMMIT=$(git rev-parse --short HEAD)

echo "[CEB] Updated from commit $PREV_COMMIT to $NEW_COMMIT"

# 4. Check if dependencies need updating
if git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" | grep -q "Backend/requirements.txt"; then
    echo "[CEB] Backend dependencies changed. Updating virtual environment..."
    if [ -f "$PROJECT_DIR/Backend/venv/bin/pip" ]; then
        "$PROJECT_DIR/Backend/venv/bin/pip" install -r "$PROJECT_DIR/Backend/requirements.txt"
    fi
fi

if git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" | grep -q "frontend/package.json"; then
    echo "[CEB] Frontend dependencies changed. Updating npm packages..."
    (cd "$PROJECT_DIR/frontend" && npm install)
    (cd "$PROJECT_DIR/frontend" && npm run build)
fi

# 5. Show Current Version Info
echo ""
echo "=================================================="
echo "  CURRENT VERSION INFO"
echo "=================================================="
git log -1 --format="Commit:  %h%nAuthor:  %an <%ae>%nDate:    %ad%nSubject: %s"
echo "=================================================="

# 6. Restart Services
echo ""
echo "[CEB] Restarting services with latest updates..."
"$PROJECT_DIR/restart-ceb.sh"
