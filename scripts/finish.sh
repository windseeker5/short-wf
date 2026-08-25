#!/bin/bash
# finish.sh
# Prend le dernier enregistrement, coupe les silences, incruste les sous-titres
# français, et envoie la capsule sur le Pixel.
#
# Usage: ./scripts/finish.sh [fichier.mp4]
#        Sans argument : prend le plus récent enregistrement.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

VIDEO_DIR="${SHORT_WORKFLOW_RECORDINGS_DIR:-$PROJECT_DIR/private/recordings}"

# ---------- Trouver le fichier ----------
if [ $# -ge 1 ]; then
    INPUT="$1"
else
    INPUT=$(ls -t "$VIDEO_DIR"/short-*.mp4 "$VIDEO_DIR"/screenrecording-*.mp4 2>/dev/null | head -1)
    if [ -z "$INPUT" ]; then
        echo "❌ Aucun enregistrement trouvé dans $VIDEO_DIR"
        echo "   Enregistre d'abord : ./scripts/record.sh"
        exit 1
    fi
fi

if [ ! -f "$INPUT" ]; then
    echo "❌ Fichier non trouvé : $INPUT"
    exit 1
fi

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$INPUT" 2>/dev/null | cut -d. -f1)
DIMS=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$INPUT" 2>/dev/null)

echo "🎬 $(basename "$INPUT")  —  ${DUR}s, ${DIMS}"
echo ""

# Avertir si le cadrage n'est pas vertical
W="${DIMS%,*}"; H="${DIMS#*,}"
if [ -n "$W" ] && [ -n "$H" ] && [ "$W" -ge "$H" ] 2>/dev/null; then
    echo "⚠️  Cette vidéo est plus large que haute : la capsule finale sera"
    echo "   recadrée, tu perdras les côtés. Pour du vertical, enregistre"
    echo "   avec ./scripts/record.sh"
    echo ""
fi

# ---------- Traitement ----------
"$SCRIPT_DIR/process_short.sh" "$INPUT"

BASENAME=$(basename "$INPUT"); BASENAME="${BASENAME%.*}"
FINAL="$PROJECT_DIR/private/exports/${BASENAME}_FINAL.mp4"

[ -f "$FINAL" ] || { echo "❌ Le fichier final est introuvable."; exit 1; }

# ---------- Envoi au téléphone ----------
echo ""
if adb devices 2>/dev/null | awk 'NR>1 && $2=="device"' | grep -q .; then
    "$SCRIPT_DIR/to_phone.sh" "$FINAL"
else
    echo "ℹ️  Pas de téléphone branché — capsule gardée ici :"
    echo "   $FINAL"
    echo ""
    echo "   Branche le Pixel puis : ./scripts/to_phone.sh \"$FINAL\""
fi
