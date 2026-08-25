#!/bin/bash
# process_short.sh
# Usage: ./process_short.sh fichier.mp4
#
# Pipeline : raw -> auto-editor (cuts) -> whisper (SRT fr) -> ffmpeg (burn-in)
# Tous les fichiers générés restent dans private/exports/.
# La sortie est toujours normalisée en 1080x1920, quel que soit le cadrage d'entrée.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"
OUT_DIR="$PROJECT_DIR/private/exports"

# Réglages utilisateur. config.sh fournit des valeurs par défaut sans écraser
# les variables déjà définies dans l'environnement :
#   CAPTION_SIZE=160 ./scripts/finish.sh
if [ -f "$PROJECT_DIR/config.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_DIR/config.sh"
fi

if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
else
    echo "Erreur : environnement virtuel non trouvé à $VENV_DIR"
    exit 1
fi

if [ $# -lt 1 ]; then
    echo "Usage: $(basename "$0") fichier.mp4"
    exit 1
fi

INPUT="$1"

if [ ! -f "$INPUT" ]; then
    echo "Erreur : fichier non trouvé : $INPUT"
    exit 1
fi

mkdir -p "$OUT_DIR"
BASENAME=$(basename "$INPUT")
BASENAME="${BASENAME%.*}"
CUT="$OUT_DIR/${BASENAME}_cut.mp4"
SRT="$OUT_DIR/${BASENAME}_cut.srt"
VERT="$OUT_DIR/${BASENAME}_vertical.mp4"
FINAL="$OUT_DIR/${BASENAME}_FINAL.mp4"

# Vérifier que la piste audio contient bien de la voix.
# Sinon auto-editor coupe tout et plante avec "Timeline is empty".
MEAN=$(ffmpeg -hide_banner -i "$INPUT" -af volumedetect -f null - 2>&1 \
    | grep -oP 'mean_volume: \K-?[0-9.]+' | head -1)
if [ -n "$MEAN" ] && [ "${MEAN%.*}" -lt -45 ] 2>/dev/null; then
    echo "❌ L'audio est quasi silencieux (moyenne ${MEAN} dB)."
    echo "   Le micro n'a rien capté. Vérifie :"
    echo "     pactl get-default-source"
    echo "     pactl get-source-mute <ton-micro>"
    echo "   Puis réenregistre. Rien à traiter ici."
    exit 1
fi

echo "✂️  1/3  Suppression des silences (auto-editor)..."
auto-editor "$INPUT" --margin "${CUT_MARGIN:-0.1sec}" -o "$CUT"

# Whisper sur le GPU si CUDA est disponible : ~6 min -> moins d'1 min sur la RTX 3070.
# Repli automatique sur le CPU si quoi que ce soit échoue côté CUDA.
if python -c 'import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    DEVICE=cuda
else
    DEVICE=cpu
fi

echo "🗣  2/3  Transcription française (whisper, device=$DEVICE)..."
if ! whisper "$CUT" --language fr --model "${WHISPER_MODEL:-medium}" --device "$DEVICE" \
    --word_timestamps True --highlight_words True --max_line_width 30 \
    --output_format all --output_dir "$OUT_DIR"; then

    if [ "$DEVICE" = "cuda" ]; then
        echo "⚠️  Échec sur GPU, reprise sur CPU (plus lent)..."
        whisper "$CUT" --language fr --model "${WHISPER_MODEL:-medium}" --device cpu \
            --word_timestamps True --highlight_words True --max_line_width 30 \
            --output_format all --output_dir "$OUT_DIR"
    else
        exit 1
    fi
fi

# Normalisation systématique en 1080x1920 : c'est le format attendu par
# Instagram et YouTube. Peu importe ce qui a été enregistré, la sortie est
# toujours au bon format — plus de drapeau à retenir.
#
# Une vidéo déjà en 9:16 est simplement mise à l'échelle. Tout autre cadrage
# est centré sur un fond flou tiré de l'image elle-même.
CUR=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$CUT")
CUR_W="${CUR%,*}"; CUR_H="${CUR#*,}"

if [ "$CUR_W" = "1080" ] && [ "$CUR_H" = "1920" ]; then
    BURN_SRC="$CUT"
else
    echo "📱 2.5/3  Normalisation ${CUR_W}x${CUR_H} → 1080x1920..."
    ffmpeg -y -i "$CUT" -filter_complex \
"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];\
[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1" \
        -c:v libx264 -crf 23 -c:a copy "$VERT" -loglevel error
    BURN_SRC="$VERT"
fi

echo "🎨  3/3  Incrustation des sous-titres (ffmpeg)..."

# Sous-titres animés : le mot prononcé s'allume en jaune, le bloc entre avec un
# léger rebond. Construits depuis le JSON de Whisper, qui donne le timing de
# chaque mot. Réglable par variables d'environnement.
CAPTION_STYLE="${CAPTION_STYLE:-karaoke}"   # karaoke | punch | simple
JSON="$OUT_DIR/${BASENAME}_cut.json"

if [ "$CAPTION_STYLE" != "simple" ] && [ -f "$JSON" ]; then
    ASS="$OUT_DIR/${BASENAME}_cut.ass"
    python3 "$SCRIPT_DIR/make_captions.py" "$JSON" "$ASS" \
        --style="$CAPTION_STYLE" \
        --font="${CAPTION_FONT:-Anton}" \
        --size="${CAPTION_SIZE:-130}" \
        --marginv="${CAPTION_MARGINV:-430}" \
        --outline="${CAPTION_OUTLINE:-6}" \
        --text="${CAPTION_TEXT:-#FFFFFF}" \
        --highlight="${CAPTION_HIGHLIGHT:-#FFD700}" \
        --outline-color="${CAPTION_OUTLINE_COLOR:-#000000}" \
        --fillers="${CAPTION_FILLERS:-}" >/dev/null

    ffmpeg -y -i "$BURN_SRC" -vf "ass=$ASS" \
        -c:v libx264 -crf 23 -c:a copy "$FINAL" -loglevel error
else
    # Repli : SRT classique.
    # ATTENTION : ffmpeg convertit le SRT sur une base 384x288 puis met à
    # l'échelle. FontSize n'est donc PAS en pixels ici — 14, pas 48.
    ffmpeg -y -i "$BURN_SRC" -vf "subtitles=$SRT:force_style='Fontname=Arial,FontSize=${FONTSIZE:-14},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0.5,MarginV=${MARGINV:-30},Alignment=2,Bold=1'" \
        -c:v libx264 -crf 23 -c:a copy "$FINAL" -loglevel error
fi

echo ""
echo "✅ Terminé ! Vidéo prête :"
echo "   $FINAL"
