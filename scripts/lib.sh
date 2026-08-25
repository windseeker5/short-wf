# lib.sh — géométrie partagée entre frame.sh, record.sh et cam.sh.
# Ne s'exécute pas seul : à sourcer.

# Calcule la bande 9:16 à capturer.
# Sortie : BAND_W BAND_H BAND_X BAND_Y MON  (coordonnées GLOBALES du compositeur)
#
# $1 = position : center | left | right | WxH+X+Y
# $2 = nom d'écran, ou vide pour celui qui a le focus
compute_band() {
    local at="${1:-center}" mon_name="${2:-}"

    # Zone explicite : on la prend telle quelle.
    if [[ "$at" =~ ^([0-9]+)x([0-9]+)\+(-?[0-9]+)\+(-?[0-9]+)$ ]]; then
        BAND_W="${BASH_REMATCH[1]}"; BAND_H="${BASH_REMATCH[2]}"
        BAND_X="${BASH_REMATCH[3]}"; BAND_Y="${BASH_REMATCH[4]}"
        MON="(zone explicite)"
        return 0
    fi

    local sel
    if [ -n "$mon_name" ]; then
        sel=".[] | select(.name == \"$mon_name\")"
    else
        sel='.[] | select(.focused == true)'
    fi

    local mx my sw sh
    read -r MON mx my sw sh < <(hyprctl monitors -j | jq -r "$sel | \"\(.name) \(.x) \(.y) \(.width) \(.height)\"")

    if [ -z "${sh:-}" ]; then
        echo "❌ Écran introuvable. Disponibles :" >&2
        hyprctl monitors -j | jq -r '.[] | "   " + .name' >&2
        return 1
    fi

    BAND_H="$sh"
    BAND_W=$(( sh * 9 / 16 ))
    BAND_Y="$my"

    # IMPORTANT : avec plusieurs écrans il faut ajouter le décalage x de l'écran,
    # sinon on capture une bande sur le mauvais moniteur.
    case "$at" in
        left)   BAND_X=$(( mx )) ;;
        right)  BAND_X=$(( mx + sw - BAND_W )) ;;
        *)      BAND_X=$(( mx + (sw - BAND_W) / 2 )) ;;
    esac
}

# Place le médaillon dans un coin de la bande, en coordonnées absolues.
# On ne s'en remet pas à omarchy-capture-webcam-resize : son ancrage dépend du
# moniteur de la fenêtre, ce qui déplaçait la caméra hors cadre.
# $1 = taille small|medium|large   $2 = coin
place_webcam() {
    local size="${1:-medium}" corner="${2:-bottom-right}" margin=36
    local w h

    case "$size" in
        small)  w=$(( BAND_H * 4 / 25 )) ;;
        # 41.4% of band height: 15% larger than the previous 36% preset.
        large)  w=$(( (BAND_H * 207 + 250) / 500 )) ;;
        *)      w=$(( BAND_H * 2 / 9 ))  ;;
    esac
    h=$(( w * 9 / 8 ))   # les préréglages sont en 8:9 portrait

    local x y
    case "$corner" in
        bottom-center|top-center) x=$(( BAND_X + (BAND_W - w) / 2 )) ;;
        bottom-left|top-left)     x=$(( BAND_X + margin )) ;;
        *)                        x=$(( BAND_X + BAND_W - w - margin )) ;;
    esac
    case "$corner" in
        top-left|top-center|top-right) y=$(( BAND_Y + margin )) ;;
        *)                             y=$(( BAND_Y + BAND_H - h - margin )) ;;
    esac

    local W='window = "title:^(WebcamOverlay)$"'

    # float() est une BASCULE, et Hyprland accepte silencieusement les champs
    # inconnus — on ne peut donc pas forcer un état par argument. On lit l'état
    # réel et on ne bascule que si besoin. Sans ça, le médaillon (déjà flottant
    # via une règle Omarchy) repassait en tuilé et sortait du cadre.
    local is_float
    is_float=$(hyprctl clients -j | jq -r 'first(.[] | select(.title=="WebcamOverlay") | .floating) // false')
    if [ "$is_float" != "true" ]; then
        hyprctl dispatch "hl.dsp.window.float({ action = \"toggle\", $W })" >/dev/null 2>&1
        sleep 0.2
    fi
    hyprctl dispatch "hl.dsp.window.resize({ x = $w, y = $h, relative = false, $W })" >/dev/null 2>&1
    hyprctl dispatch "hl.dsp.window.move({ x = $x, y = $y, relative = false, $W })" >/dev/null 2>&1
}

# Ferme le médaillon.
#
# On NE fait PAS `pkill -f WebcamOverlay` : ça tue tout processus dont la ligne
# de commande contient ce mot — y compris le shell qui exécute ce script.
# On récupère le PID exact de la fenêtre via Hyprland.
stop_webcam() {
    local pid
    pid=$(hyprctl clients -j | jq -r 'first(.[] | select(.title=="WebcamOverlay") | .pid) // empty')
    [ -n "$pid" ] && kill "$pid" 2>/dev/null
    # Filet de sécurité : uniquement les mpv portant notre app-id.
    pkill -f 'mpv .*wayland-app-id=WebcamOverlay' 2>/dev/null
    return 0
}

# Lance la fenêtre webcam. $1 = taille
start_webcam() {
    local size="${1:-medium}"
    local cam
    cam=$(omarchy-capture-webcam-list 2>/dev/null | sed -n '1s/[[:space:]].*//p')
    [ -z "$cam" ] && return 1

    stop_webcam
    sleep 0.3

    mpv "av://v4l2:$cam" \
        --profile=low-latency --untimed --no-cache \
        --demuxer-lavf-o="video_size=1280x720,framerate=30" \
        '--vf=lavfi=[crop=ih*8/9:ih]' \
        --title="WebcamOverlay" --wayland-app-id="WebcamOverlay-$size" \
        --no-border --no-audio --no-osc --osd-level=0 --really-quiet &>/dev/null &

    local n=0
    while ((n < 60)) && ! hyprctl clients -j | jq -e 'any(.[]; .title == "WebcamOverlay")' >/dev/null 2>&1; do
        sleep 0.05; ((n++))
    done
    sleep 0.4   # laisser les règles de fenêtre d'Omarchy s'appliquer avant de placer
    return 0
}
