#!/bin/bash
# record.sh — enregistre une bande verticale 9:16, avec médaillon webcam et micro.
#
# Usage:
#   ./scripts/record.sh                    démarre (ou arrête si déjà en cours)
#   ./scripts/record.sh --at=right         bande sur la droite de l'écran
#   ./scripts/record.sh --at=left
#   ./scripts/record.sh --region=607x1080+1200+0    zone exacte
#   ./scripts/record.sh --cam=large        small | medium | large
#   ./scripts/record.sh --cam-pos=bottom-left       coin du médaillon
#   ./scripts/record.sh --no-cam
#   ./scripts/record.sh --monitor=DP-3

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

# Captures stay private to this project by default. Override only when needed:
# SHORT_WORKFLOW_RECORDINGS_DIR=/somewhere ./scripts/record.sh
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUT_DIR="${SHORT_WORKFLOW_RECORDINGS_DIR:-$PROJECT_DIR/private/recordings}"
mkdir -p "$OUT_DIR"

# Défauts depuis config.sh, surchargeables par les options ci-dessous.
[ -f "$PROJECT_DIR/config.sh" ] && source "$PROJECT_DIR/config.sh"

AT="${BAND_AT:-center}"; CAM_SIZE="${CAM_SIZE:-medium}"
CAM_POS="${CAM_POS:-bottom-right}"; USE_CAM=1; MONITOR=""
for arg in "$@"; do
    case "$arg" in
        --at=*)      AT="${arg#*=}" ;;
        --region=*)  AT="${arg#*=}" ;;
        --cam=*)     CAM_SIZE="${arg#*=}" ;;
        --cam-pos=*) CAM_POS="${arg#*=}" ;;
        --no-cam)    USE_CAM=0 ;;
        --monitor=*) MONITOR="${arg#*=}" ;;
    esac
done

# ---------- Arrêt si déjà en cours ----------
if pgrep -f "^gpu-screen-recorder" >/dev/null; then
    echo "⏹  Arrêt de l'enregistrement..."
    pkill -SIGINT -f "^gpu-screen-recorder"   # SIGINT : nécessaire pour finaliser le MP4
    n=0
    while pgrep -f "^gpu-screen-recorder" >/dev/null && ((n < 50)); do sleep 0.1; ((n++)); done
    stop_webcam

    LAST=$(ls -t "$OUT_DIR"/short-*.mp4 2>/dev/null | head -1)
    echo ""
    echo "✅ Enregistré : $LAST"
    echo ""
    echo "👉 Étape suivante :  ./scripts/finish.sh"
    exit 0
fi

compute_band "$AT" "$MONITOR" || exit 1
REGION="${BAND_W}x${BAND_H}+${BAND_X}+${BAND_Y}"

echo "🎬 Écran : $MON"
echo "   Bande : ${BAND_W}x${BAND_H} à ${BAND_X},${BAND_Y}  ($AT)"

# ---------- Médaillon ----------
if [ "$USE_CAM" -eq 1 ]; then
    if start_webcam "$CAM_SIZE"; then
        place_webcam "$CAM_SIZE" "$CAM_POS"
        sleep 0.4
        echo "📷 Médaillon : $CAM_SIZE, $CAM_POS"
    else
        echo "⚠️  Aucune webcam détectée — enregistrement sans médaillon"
    fi
else
    echo "🚫 Sans médaillon"
fi

# ---------- Enregistrement ----------
FILE="$OUT_DIR/short-$(date +'%Y-%m-%d_%H-%M-%S').mp4"
gpu-screen-recorder -w "$REGION" -k auto -f 60 -fm cfr \
    -fallback-cpu-encoding yes -a "default_input" -ac aac \
    -o "$FILE" >/dev/null 2>&1 &

n=0
while [ ! -f "$FILE" ] && ((n < 50)); do sleep 0.2; ((n++)); done
if [ ! -f "$FILE" ]; then
    echo "❌ L'enregistrement n'a pas démarré."
    stop_webcam
    exit 1
fi

echo ""
echo "🔴 ENREGISTREMENT EN COURS"
echo ""
echo "   Arrêter :             ./scripts/record.sh"
echo "   Cacher/montrer cam :  ./scripts/cam.sh"
