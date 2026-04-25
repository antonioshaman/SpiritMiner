#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/root/SpiritMiner"
SERVICE_NAME="spiritminer"
VENV_DIR="$PROJECT_DIR/venv"

cd "$PROJECT_DIR"

# Read current version
CURRENT_VERSION=$(cat VERSION)
echo "=== SpiritMiner Deploy ==="
echo "Current version: $CURRENT_VERSION"

# Bump patch version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
echo "$NEW_VERSION" > VERSION
echo "New version: $NEW_VERSION"

# Commit version bump
git add VERSION
git commit -m "bump: v$NEW_VERSION

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# Push to GitHub
echo "Pushing to GitHub..."
git push origin main

# Install/update dependencies
echo "Installing dependencies..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -q -r requirements.txt

# Restart service
echo "Restarting $SERVICE_NAME..."
sudo systemctl restart "$SERVICE_NAME"
sleep 2

if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "=== Deploy successful: v$NEW_VERSION ==="
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 10
else
    echo "=== Deploy FAILED ==="
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 30
    exit 1
fi
