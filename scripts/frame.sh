#!/bin/bash
# frame.sh — aligne la fenêtre active EXACTEMENT sur la bande qui sera enregistrée.
#
# Usage:
#   ./scripts/frame.sh                 bande centrée (défaut)
#   ./scripts/frame.sh --at=right      bande à droite  (utile pour la barre de menu)
#   ./scripts/frame.sh --at=left
#   ./scripts/frame.sh --region=607x1080+1200+0
#   ./scripts/frame.sh --off           remet la fenêtre en tuilé
#   ./scripts/frame.sh --monitor=DP-3
#
# ⚠️ Utilise la MÊME option --at que record.sh, sinon la fenêtre et la zone
#    enregistrée ne coïncideront pas.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
[ -f "$PROJECT_DIR/config.sh" ] && source "$PROJECT_DIR/config.sh"

AT="${BAND_AT:-center}"; MONITOR=""
for arg in "$@"; do
    case "$arg" in
        --at=*)      AT="${arg#*=}" ;;
        --region=*)  AT="${arg#*=}" ;;
        --monitor=*) MONITOR="${arg#*=}" ;;
        --off)
            hyprctl dispatch 'hl.dsp.window.float({ enabled = false })' >/dev/null 2>&1
            echo "↩️  Fenêtre remise en mode normal (tuilé)."
            exit 0
            ;;
    esac
done

compute_band "$AT" "$MONITOR" || exit 1

TITLE=$(hyprctl activewindow -j | jq -r '.title // empty')
ADDR=$(hyprctl activewindow -j | jq -r '.address // empty')
if [ -z "$ADDR" ]; then
    echo "❌ Aucune fenêtre active. Clique sur la fenêtre à cadrer, puis relance."
    exit 1
fi

W="window = \"address:$ADDR\""

# float() bascule : on ne l'appelle que si la fenêtre n'est pas déjà flottante.
IS_FLOAT=$(hyprctl activewindow -j | jq -r '.floating')
if [ "$IS_FLOAT" != "true" ]; then
    hyprctl dispatch "hl.dsp.window.float({ action = \"toggle\", $W })" >/dev/null 2>&1
    sleep 0.3
fi
hyprctl dispatch "hl.dsp.window.resize({ x = $BAND_W, y = $BAND_H, relative = false, $W })" >/dev/null 2>&1
sleep 0.3
hyprctl dispatch "hl.dsp.window.move({ x = $BAND_X, y = $BAND_Y, relative = false, $W })" >/dev/null 2>&1

echo "🎯 « $TITLE » cadrée sur ${BAND_W}x${BAND_H} à ${BAND_X},${BAND_Y}  ($AT, $MON)"
echo "   Enregistre avec la même option :  ./scripts/record.sh --at=$AT"
