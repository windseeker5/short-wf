#!/bin/bash
# hotkey.sh — point d'entrée pour les raccourcis clavier.
#
# Usage: ./scripts/hotkey.sh frame|record|cam|finish|unframe
#
# Pourquoi ce script existe : lancé depuis une touche, un script n'a PAS de
# terminal. Tous les echo de record.sh & co partiraient dans le vide, et on ne
# saurait pas si l'enregistrement a démarré. Ici on convertit tout en
# notifications de bureau.
#
# Les scripts d'origine restent inchangés et utilisables au terminal.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RECORDINGS_DIR="${SHORT_WORKFLOW_RECORDINGS_DIR:-$PROJECT_DIR/private/recordings}"
EXPORTS_DIR="$PROJECT_DIR/private/exports"

notify() {  # notify <titre> [description] [urgence]
    omarchy-notification-send "$1" "${2:-}" -u "${3:-low}" 2>/dev/null \
        || notify-send "$1" "${2:-}" 2>/dev/null || true
}

recording() { pgrep -f '^gpu-screen-recorder' >/dev/null; }

# Rafraîchit le témoin d'enregistrement de la barre Omarchy. Il teste
# pgrep gpu-screen-recorder, donc il reconnaît notre enregistrement.
refresh_indicator() { omarchy-shell -q omarchy.indicators refresh >/dev/null 2>&1 || true; }

case "${1:-}" in

    frame)
        OUT=$("$SCRIPT_DIR/frame.sh" 2>&1)
        if [ $? -eq 0 ]; then
            notify "Fenêtre cadrée" "$(echo "$OUT" | head -1 | sed 's/^🎯 //')"
        else
            notify "Cadrage impossible" "$(echo "$OUT" | head -1)" critical
        fi
        ;;

    unframe)
        "$SCRIPT_DIR/frame.sh" --off >/dev/null 2>&1
        notify "Fenêtre libérée" "Remise en mode tuilé"
        ;;

    record)
        if recording; then
            "$SCRIPT_DIR/record.sh" >/dev/null 2>&1
            refresh_indicator
            LAST=$(ls -t "$RECORDINGS_DIR"/short-*.mp4 2>/dev/null | head -1)
            DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$LAST" 2>/dev/null | cut -d. -f1)
            notify "Enregistrement terminé" "${DUR}s — lance «finish» pour traiter" normal
        else
            OUT=$("$SCRIPT_DIR/record.sh" 2>&1)
            if recording; then
                refresh_indicator
                BANDE=$(echo "$OUT" | sed -n 's/^ *Bande : //p')
                notify "🔴 Enregistrement en cours" "${BANDE:-parle maintenant}" normal
            else
                notify "L'enregistrement n'a pas démarré" "$(echo "$OUT" | tail -1)" critical
            fi
        fi
        ;;

    cam)
        OUT=$("$SCRIPT_DIR/cam.sh" 2>&1)
        notify "Caméra" "$(echo "$OUT" | tail -1 | sed 's/^[^ ]* //')"
        ;;

    finish)
        if recording; then
            notify "Enregistrement encore en cours" "Arrête-le d'abord" critical
            exit 1
        fi
        SRC=$(ls -t "$RECORDINGS_DIR"/short-*.mp4 2>/dev/null | head -1)
        if [ -z "$SRC" ]; then
            notify "Rien à traiter" "Aucun enregistrement trouvé" critical
            exit 1
        fi

        notify "Traitement lancé" "$(basename "$SRC") — une à deux minutes" normal

        # Détaché : finish.sh prend 1-2 min, la touche ne doit pas bloquer.
        setsid nohup bash -c '
            SD="$1"; PD="$2"
            LOG=$(mktemp)
            if "$SD/finish.sh" >"$LOG" 2>&1; then
                FINAL=$(ls -t "$PD"/private/exports/*_FINAL.mp4 2>/dev/null | head -1)
                omarchy-notification-send "Capsule prête" "$(basename "$FINAL")" \
                    -u normal --exec "$(printf "mpv %q" "$FINAL")" 2>/dev/null \
                    || notify-send "Capsule prête" "$(basename "$FINAL")"
            else
                omarchy-notification-send "Le traitement a échoué" \
                    "$(tail -3 "$LOG" | head -1)" -u critical 2>/dev/null \
                    || notify-send "Le traitement a échoué" "$(tail -1 "$LOG")"
            fi
            rm -f "$LOG"
        ' _ "$SCRIPT_DIR" "$PROJECT_DIR" >/dev/null 2>&1 < /dev/null &
        ;;

    *)
        echo "Usage: $(basename "$0") frame|record|cam|finish|unframe"
        exit 1
        ;;
esac
