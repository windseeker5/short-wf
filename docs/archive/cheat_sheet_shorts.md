# Cheat Sheet : Workflow YouTube Shorts

Dossier de travail : `/home/kdresdell/Documents/DEV/short-workflow`

> Pour un premier test rapide de bout en bout, suis plutôt
> [`TEST_RAPIDE.md`](TEST_RAPIDE.md). Ce fichier-ci est la référence complète.

---

## Structure

```
/home/kdresdell/Documents/DEV/short-workflow/
├── .venv/                  # Environnement Python (auto-editor, whisper)
├── docs/
│   ├── arch_linux_shorts_workflow_fr.md
│   ├── arch_linux_shorts_workflow_fr.pdf
│   ├── arch_linux_shorts_workflow_fr.docx
│   └── cheat_sheet_shorts.md   <- ce fichier
├── inputs/                 # Vidéos brutes (raw_video.mp4)
├── outputs/                # Vidéos finies
└── scripts/
    ├── process_short.sh          # Script d'automatisation complet
    ├── short-env.sh              # Activer le venv
    └── recordly-launch.sh        # Lanceur Recordly corrigé pour Hyprland/NVIDIA
```

---

## Démarrage rapide

1. Placer la vidéo brute dans `inputs/`.
2. Lancer le traitement :
   ```bash
   cd /home/kdresdell/Documents/DEV/short-workflow
   ./scripts/process_short.sh inputs/ma_video.mp4          # déjà vertical
   ./scripts/process_short.sh inputs/ma_video.mp4 --vertical  # 16:9 -> 1080x1920
   ```
3. Récupérer la vidéo finale : `outputs/ma_video_FINAL.mp4`

---

## Stack installée

| Outil | Version | Rôle |
|-------|---------|------|
| `scrcpy` | 4.1 | Capture écran téléphone Android |
| `ffmpeg` | n9.0.1 | Rendu final et incrustation SRT |
| `recordly-bin` | 1.3.3 | Enregistrement desktop + auto-zoom |
| `auto-editor` | 29.3.1 | Suppression des silences |
| `openai-whisper` | 20250625 | Transcription FR + sous-titres |

---

## Commandes manuelles

### 1. Capturer le téléphone
```bash
scrcpy --show-touches --max-fps=60 --window-title="PhoneCapture"
```

### 2. Lancer Recordly (correction Hyprland/NVIDIA)
**Important :** utiliser le lanceur corrigé, pas `recordly` directement.

```bash
/home/kdresdell/Documents/DEV/short-workflow/scripts/recordly-launch.sh
```

Ou via l’entrée de bureau : **Recordly (Hyprland Fix)**.

### 3. Supprimer les silences
```bash
source /home/kdresdell/Documents/DEV/short-workflow/scripts/short-env.sh
auto-editor raw_video.mp4 --margin 0.1sec -o cut_video.mp4
```

### 4. Générer les sous-titres
```bash
whisper cut_video.mp4 \
  --language fr \
  --model medium \
  --word_timestamps True \
  --highlight_words True \
  --max_line_width 30 \
  --output_format srt
```

La première exécution télécharge le modèle `medium` (~1,5 Go).

### 5. Incruster les sous-titres
```bash
ffmpeg -i cut_video.mp4 \
  -vf "subtitles=cut_video.srt:force_style='Fontname=Arial,FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=25,Bold=1'" \
  -c:v libx264 -crf 23 -c:a copy FINAL_SHORT.mp4
```

---

## Script complet (`process_short.sh`)

Usage :
```bash
./scripts/process_short.sh inputs/ma_video.mp4
```

Étapes exécutées :
1. `auto-editor` pour les cuts
2. `whisper` pour la transcription FR
3. `ffmpeg` pour l’incrustation des sous-titres

---

## Raccourcis utiles

### Activer le venv pour tests manuels
```bash
source /home/kdresdell/Documents/DEV/short-workflow/scripts/short-env.sh
```

### Vérifier que Recordly est bien en XWayland
```bash
hyprctl clients | grep -A2 -i recordly
```

Tu devrais voir `xwayland: 1`.

---

## Dépannage

### Recordly : interface qui disparaît / carré vert
Utiliser impérativement le lanceur corrigé. Il force XWayland et désactive l’accélération GPU :
```bash
/home/kdresdell/Documents/DEV/short-workflow/scripts/recordly-launch.sh
```

### Whisper : première utilisation lente
C’est normal. Le modèle `medium` se télécharge une seule fois.

### Problème d’échelle ou de curseur décalé
La config Hyprland a été corrigée (`GDK_SCALE=1` et monitor scale=1). Pour un autre moniteur, modifier :
```
~/.config/hypr/monitors.lua
```

---

## Prochaine étape

Créer un agent/skill OpenCode pour automatiser encore plus le workflow (scripting, idéation, etc.).
