#!/bin/bash
# short-env.sh
# Helper pour activer l'environnement du workflow short-workflow
# Usage: source /home/kdresdell/Documents/DEV/short-workflow/scripts/short-env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"

if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    echo "✅ Environnement activé : $VENV_DIR"
    echo "   auto-editor : $(command -v auto-editor)"
    echo "   whisper     : $(command -v whisper)"
else
    echo "❌ Environnement virtuel non trouvé à $VENV_DIR"
    return 1 2>/dev/null || exit 1
fi
