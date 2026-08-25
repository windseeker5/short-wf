#!/bin/bash
# cam.sh — cache ou remontre le médaillon. Fonctionne PENDANT l'enregistrement.
#
# Usage:
#   ./scripts/cam.sh                    bascule
#   ./scripts/cam.sh large              remontre à cette taille
#   ./scripts/cam.sh large bottom-left  taille + coin

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

SIZE="${1:-}"; POS="${2:-bottom-right}"

visible() { hyprctl clients -j | jq -e 'any(.[]; .title == "WebcamOverlay")' >/dev/null 2>&1; }

if visible && [ -z "$SIZE" ]; then
    stop_webcam
    echo "🚫 Médaillon caché"
    exit 0
fi

SIZE="${SIZE:-medium}"
case "$SIZE" in small|medium|large) ;; *) echo "Taille : small, medium ou large"; exit 1 ;; esac

# Retrouver la bande de l'enregistrement en cours, sinon celle de l'écran focus.
AT="center"
if REG=$(pgrep -a -f '^gpu-screen-recorder' | head -1 | grep -oE '[0-9]+x[0-9]+\+-?[0-9]+\+-?[0-9]+'); then
    AT="$REG"
fi
compute_band "$AT" "" || exit 1

if ! start_webcam "$SIZE"; then
    echo "❌ Aucune webcam détectée."
    exit 1
fi
place_webcam "$SIZE" "$POS"
echo "📷 Médaillon visible ($SIZE, $POS)"
