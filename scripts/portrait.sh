#!/bin/bash
# portrait.sh — local portrait capture for the channel-logo workflow.
#
# Commands:
#   ./scripts/portrait.sh preview       open a live, cropped portrait preview
#   ./scripts/portrait.sh shoot         capture one 4K source photograph
#   ./scripts/portrait.sh sheet         create a contact sheet of local captures
#   ./scripts/portrait.sh clear         delete only local, unapproved captures
#
# The script never uploads a photo. Upload happens only in phase two, after a
# capture has been selected and FAL_KEY is configured locally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$PROJECT_DIR/private/portraits"
CAMERA="${PORTRAIT_CAMERA:-/dev/video0}"
PREVIEW_TITLE="Portrait Preview"
PREVIEW_PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/short-workflow-portrait-preview.pid"

mkdir -p "$OUT_DIR"

preview_pid() {
    # Prefer the PID recorded by this script. The Hyprland lookup also handles
    # a preview created before this state file existed.
    if [ -r "$PREVIEW_PID_FILE" ]; then
        local pid
        pid=$(cat "$PREVIEW_PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            printf '%s\n' "$pid"
            return 0
        fi
        rm -f "$PREVIEW_PID_FILE"
    fi
    hyprctl clients -j 2>/dev/null | jq -r \
        --arg title "$PREVIEW_TITLE" 'first(.[] | select(.title == $title) | .pid) // empty'
}

preview_running() {
    [ -n "$(preview_pid)" ]
}

camera_busy() {
    fuser -s "$CAMERA" 2>/dev/null
}

wait_for_camera_release() {
    local n=0
    while camera_busy && ((n < 40)); do
        sleep 0.1
        ((n++)) || true
    done
    ! camera_busy
}

stop_preview() {
    local pid
    pid=$(preview_pid)
    [ -n "$pid" ] && kill -TERM "$pid" 2>/dev/null || true
    rm -f "$PREVIEW_PID_FILE"
    if ! wait_for_camera_release; then
        echo "Camera is still in use. Close the application using $CAMERA, then try again." >&2
        return 1
    fi
}

start_preview() {
    if preview_running; then
        echo "Preview already open."
        return 0
    fi
    [ -e "$CAMERA" ] || { echo "Camera not found: $CAMERA"; exit 1; }

    # 16:9 live stream, cropped into a portrait-friendly center composition.
    # It is only a framing preview; the actual portrait is captured at 4K.
    mpv "av://v4l2:$CAMERA" \
        --profile=low-latency --untimed --no-cache \
        --demuxer-lavf-o="input_format=mjpeg,video_size=1920x1080,framerate=30" \
        '--vf=lavfi=[crop=ih*3/4:ih]' \
        --title="$PREVIEW_TITLE" --wayland-app-id="PortraitPreview" \
        --no-audio --no-osc --osd-level=0 --really-quiet &>/dev/null &
    echo "$!" > "$PREVIEW_PID_FILE"

    if [ "${PORTRAIT_MENU:-0}" = "1" ]; then
        echo "Portrait preview opened. Return to the Logo Studio menu and choose “Take a portrait”."
    else
        echo "Portrait preview opened. Center your face, look toward the lens, then run:"
        echo "  ./scripts/portrait.sh shoot"
    fi
}

shoot() {
    [ -e "$CAMERA" ] || { echo "Camera not found: $CAMERA"; exit 1; }
    local restart_preview=0
    if preview_running; then
        restart_preview=1
        stop_preview || exit 1
    elif camera_busy; then
        echo "Camera is already in use by another application. Close it, then try again." >&2
        exit 1
    fi

    local output="$OUT_DIR/portrait-$(date +'%Y-%m-%d_%H-%M-%S').jpg"
    local temporary="${output}.part.jpg"
    local capture_log="${temporary}.log"
    rm -f "$temporary" "$capture_log"
    echo "Capturing a 4K portrait…"
    # Some UVC cameras emit a harmless QBUF warning while closing immediately
    # after the first frame. Keep it in a private log; the JPEG validation below
    # is the source of truth, and errors are shown if no valid portrait exists.
    if ! ffmpeg -hide_banner -loglevel error -y \
        -f v4l2 -input_format mjpeg -video_size 3840x2160 -framerate 30 \
        -i "$CAMERA" -frames:v 1 -q:v 2 "$temporary" 2>"$capture_log"; then
        cat "$capture_log" >&2
        rm -f "$temporary" "$capture_log"
        [ "$restart_preview" -eq 1 ] && start_preview
        echo "Portrait capture failed — no photo was saved." >&2
        exit 1
    fi

    # A command exit code is not enough: V4L2 can create a partial JPEG after
    # a device race. Validate the finished still before ever calling it saved.
    dimensions=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
        -of csv=p=0 "$temporary" 2>/dev/null || true)
    if [ "$dimensions" != "3840,2160" ] || [ "$(stat -c %s "$temporary")" -lt 100000 ]; then
        cat "$capture_log" >&2
        rm -f "$temporary" "$capture_log"
        [ "$restart_preview" -eq 1 ] && start_preview
        echo "Portrait capture was incomplete — no photo was saved. Try again." >&2
        exit 1
    fi
    rm -f "$capture_log"
    mv "$temporary" "$output"

    echo "✓ Saved and verified: $output"
    echo "Tip: take 3–5 options with slightly different expressions; we will choose one before upload."
    [ "$restart_preview" -eq 1 ] && start_preview
}

sheet() {
    local images=("$OUT_DIR"/portrait-*.jpg)
    [ -e "${images[0]}" ] || { echo "No portraits captured yet."; exit 1; }
    local output="$OUT_DIR/contact-sheet.jpg"
    magick montage "${images[@]}" -thumbnail '480x480^' -gravity center -extent 480x480 \
        -tile 3x -geometry +12+12 -background '#11101d' "$output"
    echo "✓ Contact sheet: $output"
    mpv "$output" --title="Portrait Contact Sheet" --no-audio --no-osc --really-quiet &>/dev/null &
}

clear() {
    rm -f "$OUT_DIR"/portrait-*.jpg "$OUT_DIR"/contact-sheet.jpg
    echo "✓ Local portrait captures deleted."
}

case "${1:-}" in
    preview) start_preview ;;
    shoot)   shoot ;;
    sheet)   sheet ;;
    clear)   clear ;;
    *)
        sed -n '2,12p' "$0"
        exit 1
        ;;
esac
