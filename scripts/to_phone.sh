#!/bin/bash
# to_phone.sh
# Envoie la capsule finie sur le Pixel pour la publier depuis Instagram / YouTube.
#
# Usage: ./scripts/to_phone.sh private/exports/ma_capsule_FINAL.mp4

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $(basename "$0") private/exports/ma_capsule_FINAL.mp4"
    exit 1
fi

VIDEO="$1"

if [ ! -f "$VIDEO" ]; then
    echo "❌ Fichier non trouvé : $VIDEO"
    exit 1
fi

PHONE=$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')
if [ -z "$PHONE" ]; then
    echo "❌ Pas de téléphone détecté."
    echo "   Branche le Pixel et accepte le débogage USB, puis relance."
    exit 1
fi

DEST="/sdcard/Movies/$(basename "$VIDEO")"

echo "📤 Envoi vers le Pixel..."
adb push "$VIDEO" "$DEST"

# Forcer l'indexation pour que la vidéo apparaisse tout de suite dans la galerie
adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE \
    -d "file://$DEST" >/dev/null 2>&1 || true

echo ""
echo "✅ Sur le téléphone : Galerie → Films → $(basename "$VIDEO")"
echo "   Publie depuis l'app Instagram ou YouTube."
