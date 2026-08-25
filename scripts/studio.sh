#!/bin/bash
# studio.sh
# Prépare le plateau : miroir du Pixel + Recordly.
#
# Usage: ./scripts/studio.sh
#
# Le téléphone est optionnel : sans lui, tu enregistres juste desktop + caméra.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🎬 Préparation du plateau"
echo ""

# ---------- 1. Téléphone ----------
PHONE=$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')

if [ -n "$PHONE" ]; then
    echo "📱 Pixel détecté ($PHONE) — lancement du miroir..."

    # Hauteur de l'écran : la fenêtre du téléphone doit l'occuper entièrement.
    # C'est le seul levier sur la netteté — chaque pixel perdu ici est un pixel
    # que le recadrage 9:16 devra réinventer à l'agrandissement.
    SCREEN_H=$(hyprctl monitors -j 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["height"])' 2>/dev/null)
    SCREEN_W=$(hyprctl monitors -j 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["width"])' 2>/dev/null)
    SCREEN_H="${SCREEN_H:-1080}"
    SCREEN_W="${SCREEN_W:-1920}"

    # Le Pixel est bien plus haut que du 9:16 (~1080x2400). Comme la capsule finale
    # est en 9:16, ces bandes haut/bas seraient perdues de toute façon. On ne demande
    # donc à scrcpy que la tranche 9:16 du téléphone : la fenêtre remplit exactement
    # la bande de recadrage, et chaque pixel du téléphone compte davantage.
    # Trajet : 2400 -> 1080 -> 1920 devient 1920 -> 1080 -> 1920.
    CROP=""
    WIN_W=$(( SCREEN_H * 9 / 16 ))   # défaut : fenêtre 9:16 à la hauteur de l'écran
    SIZE=$(adb shell wm size 2>/dev/null | grep -oE '[0-9]+x[0-9]+' | tail -1)
    if [ -n "$SIZE" ]; then
        PW="${SIZE%x*}"
        PH="${SIZE#*x}"
        # Hauteur d'une tranche 9:16 à la largeur du téléphone
        CROP_H=$(( PW * 16 / 9 ))
        if [ "$CROP_H" -lt "$PH" ]; then
            CROP_Y=$(( (PH - CROP_H) / 2 ))
            CROP="--crop=${PW}:${CROP_H}:0:${CROP_Y}"
            WIN_W=$(( SCREEN_H * PW / CROP_H ))
            echo "   ✂️  Écran ${PW}x${PH} → tranche 9:16 ${PW}x${CROP_H} (plus de détail utile)"
        else
            WIN_W=$(( SCREEN_H * PW / PH ))
        fi
    fi

    # shellcheck disable=SC2086
    scrcpy --show-touches --max-fps=60 --window-title="PhoneCapture" \
           --window-height="$SCREEN_H" --window-y=0 $CROP \
           --stay-awake --no-audio >/dev/null 2>&1 &
    sleep 3

    # Sous Hyprland la fenêtre serait tuilée. On la sort du tuilage, on lui donne la
    # taille exacte de la bande 9:16 et on la centre : le recadrage de Recordly tombe
    # alors toujours au même endroit, d'une capsule à l'autre.
    #
    # NOTE : Hyprland 0.56+ (config Lua) n'accepte plus l'ancienne syntaxe
    # `hyprctl dispatch setfloating title:...`. Les dispatchers passent par hl.dsp.*
    # avec des tables Lua. Vérifié sur cette machine.
    if command -v hyprctl >/dev/null; then
        X=$(( (SCREEN_W - WIN_W) / 2 ))
        WSEL='window = "title:^(PhoneCapture)$"'
        hyprctl dispatch "hl.dsp.window.float({ $WSEL })" >/dev/null 2>&1
        sleep 0.5
        hyprctl dispatch "hl.dsp.window.resize({ x = $WIN_W, y = $SCREEN_H, relative = false, $WSEL })" >/dev/null 2>&1
        sleep 0.5
        hyprctl dispatch "hl.dsp.window.move({ x = $X, y = 0, relative = false, $WSEL })" >/dev/null 2>&1
    fi

    echo "   ✅ Fenêtre « PhoneCapture » : ${WIN_W}x${SCREEN_H}, centrée."
    echo "   👉 Pilote le téléphone À LA SOURIS dans cette fenêtre :"
    echo "      c'est plus précis et les appuis restent visibles à l'écran."
else
    UNAUTH=$(adb devices | awk 'NR>1 && $2=="unauthorized" {print $1; exit}')
    if [ -n "$UNAUTH" ]; then
        echo "⚠️  Pixel branché mais NON AUTORISÉ."
        echo "   Regarde l'écran du téléphone et accepte « Autoriser le débogage USB »."
    else
        echo "ℹ️  Pas de téléphone détecté — on continue sans."
        echo "   Pour l'activer : câble USB + Débogage USB dans les options développeur."
    fi
    echo "   (desktop + caméra fonctionnent quand même)"
fi

# ---------- 2. Enregistrement ----------
# On n'utilise pas Recordly : il lague de façon rédhibitoire sur cette machine,
# GPU activé ou non. L'enregistreur natif d'Omarchy (gpu-screen-recorder, NVENC)
# fait le médaillon webcam, le micro et la capture d'une zone, sans configuration.

cat <<'EOF'

────────────────────────────────────────────────
La bande verticale 9:16 est déjà calculée.
Tu n'as rien à tracer.

  ./scripts/record.sh      démarre
  (tu parles)
  ./scripts/record.sh      arrête
  ./scripts/finish.sh      coupe, sous-titre, envoie

Médaillon webcam et micro inclus.
────────────────────────────────────────────────

Pour que l'écran du Pixel reste lisible :
  • monte la taille d'affichage du téléphone
    (Paramètres → Affichage → Taille d'affichage et texte)

EOF
