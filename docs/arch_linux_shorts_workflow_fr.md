# Guide Complet : Pipeline Automatisé de YouTube Shorts sur Arch Linux (Édition Française)

Ce document contient l'intégralité du workflow, des scripts et des commandes pour produire rapidement des vidéos courtes (30s) en français avec auto-zoom, suppression de silences et sous-titres animés au mot près.

---

## 🛠 1. La Stack Logicielle (100% Linux & Open Source)

* **Idéation & Scripting :** LLM (Claude / ChatGPT / OpenRouter API)
* **Capture Téléphone :** `scrcpy` (Miroir de l'écran avec affichage des touches)
* **Enregistrement & Polish Visuel :** `recordly-bin` (Auto-zoom, fond stylisé, bulle caméra, micro)
* **Jump Cuts Automatiques :** `auto-editor` (Suppression des silences)
* **Transcription & Sous-titres :** `whisper` CLI (Whisper-timestamped / OpenAI)
* **Rendu Final :** `ffmpeg` (Incrustation des sous-titres stylisés)

---

## ⚙️ 2. Installation des Outils sur Arch Linux

Exécutez ces commandes une fois dans votre terminal :

```bash
# 1. Installer scrcpy et ffmpeg
sudo pacman -S scrcpy ffmpeg

# 2. Installer Recordly via l'AUR
yay -S recordly-bin

# 3. Installer Auto-Editor pour les cuts automatiques
pip install auto-editor

# 4. Installer Whisper pour la transcription française
pip install openai-whisper
```

---

## 📝 3. Étape 1 : Le Script & Les Mots d'Accroche (LLM)

Utilisez votre LLM avec ce prompt configuré pour le français et la mise en évidence des mots clés :

> **Prompt LLM :**
> "Je veux montrer une astuce technique sur [TON ASTUCE]. Rédige un script de 30 secondes pour un YouTube Short vertical en français. Accroche le spectateur dans les 3 premières secondes. Mets en gras les **mots d'impact** clés que je devrais animer en grand sur l'écran (ex: **Gratuit**, **Secret**, **Temps**). Précise aussi les actions à faire sur l'écran."

---

## 📱 4. Étape 2 : Capture & Enregistrement (Recordly + scrcpy)

1. Connectez votre téléphone Android en USB (Mode Débogage USB activé).
2. Lancez `scrcpy` avec les touches visuelles :
   ```bash
   scrcpy --show-touches --max-fps=60 --window-title="PhoneCapture"
   ```
3. Ouvrez **Recordly**.
4. Sélectionnez la fenêtre `PhoneCapture`, activez votre webcam (bulle caméra) et votre micro desktop.
5. Lisez votre script face caméra tout en manipulant le téléphone. Arrêtez l'enregistrement.
6. Dans l'éditeur de Recordly, laissez l'auto-zoom s'appliquer sur vos clics, ajoutez un fond stylisé, et exportez en `raw_video.mp4`.

---

## ✂️ 5. Étape 3 : Suppression des Silences (Auto-Editor)

Éliminez automatiquement les blancs, respirations et hésitations :

```bash
auto-editor raw_video.mp4 --margin 0.1sec --export cut_video.mp4
```

---

## 🗣 6. Étape 4 : Génération des Sous-titres Animés (Whisper)

Générez un fichier de sous-titres `.srt` en français avec mise en valeur du mot prononcé (`--highlight_words True`) :

```bash
whisper cut_video.mp4 --language fr --model medium --word_timestamps True --highlight_words True --max_line_width 30 --output_format srt
```

---

## 🎨 7. Étape 5 : Incrustation des Sous-titres (FFmpeg)

Incrustez les sous-titres stylisés directement dans la vidéo (Format Jaune/Blanc dynamique) :

```bash
ffmpeg -i cut_video.mp4 -vf "subtitles=cut_video.srt:force_style='Fontname=Arial,FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=25,Bold=1'" -c:v libx264 -crf 23 -c:a copy FINAL_SHORT.mp4
```

---

## 🚀 8. Automation Complète (Master Bash Script)

Créez un fichier `process_short.sh` :

```bash
#!/bin/bash
# Usage: ./process_short.sh raw_video.mp4

INPUT=$1
BASENAME=$(basename "$INPUT" .mp4)

echo "✂️ 1. Cut des silences..."
auto-editor "$INPUT" --margin 0.1sec --export "${BASENAME}_cut.mp4"

echo "🗣 2. Transcription Whisper en Français..."
whisper "${BASENAME}_cut.mp4" --language fr --model medium --word_timestamps True --highlight_words True --max_line_width 30 --output_format srt

echo "🎨 3. Incrustation des sous-titres..."
ffmpeg -i "${BASENAME}_cut.mp4" -vf "subtitles=${BASENAME}_cut.srt:force_style='Fontname=Arial,FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=25,Bold=1'" -c:v libx264 -crf 23 -c:a copy "${BASENAME}_FINAL.mp4"

echo "✅ Terminé ! Vidéo prête : ${BASENAME}_FINAL.mp4"
```

Rendez le script exécutable :
```bash
chmod +x process_short.sh
```

Utilisation :
```bash
./process_short.sh raw_video.mp4
```
