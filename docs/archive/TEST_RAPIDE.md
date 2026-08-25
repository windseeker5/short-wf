# Mon premier Short — guide pas à pas

Suis les étapes dans l'ordre. Ne saute rien. ~15 minutes.

**Ton téléphone ne sert pas.** Laisse-le dans ta poche. Tout se fait avec la webcam USB.

---

## 1. Branche ta webcam

Branche la webcam EMEET dans un port USB du PC. Attends 3 secondes.

---

## 2. Ouvre un terminal et va dans le dossier

```bash
cd /home/kdresdell/Documents/DEV/short-workflow
```

---

## 3. Lance l'enregistrement

```bash
./scripts/record_me.sh
```

Puis laisse-toi guider :

| Ce qui s'affiche | Ce que tu fais |
|---|---|
| `🎙 Quel micro ?` avec une liste | Tape **`1`** puis Entrée |
| `🔊 Test du micro — PARLE MAINTENANT` | Dis « un, deux, trois » à voix haute |
| `✅ Micro OK` | Rien, ça continue tout seul |
| Une fenêtre s'ouvre avec ton visage | Place-toi bien dans le cadre, puis appuie sur **`q`** dans cette fenêtre |
| `3... 2... 1...` | Prépare-toi |
| `🔴 ENREGISTREMENT` | **Parle** (voir étape 4) |
| Tu as fini de parler | Appuie sur **`q`** dans le terminal |

---

## 4. Quoi dire pendant l'enregistrement

Parle **30 à 60 secondes** en français. Donne un petit conseil, n'importe lequel.
Par exemple :

> « Si tu veux apprendre plus vite, arrête de lire et commence à construire.
> Tu vas retenir dix fois plus en te trompant qu'en regardant des tutoriels.
> Choisis un petit projet, finis-le au complet, même s'il est laid.
> C'est le fait de finir qui t'apprend, pas le fait de commencer. »

**Important pour ce test :** fais **deux ou trois pauses silencieuses de 3 secondes**
au milieu. Reste immobile et tais-toi. C'est exactement ce que le traitement doit couper —
c'est ça qu'on veut voir marcher.

Quand tu as fini : **`q`** dans le terminal.

Le script t'affiche alors la commande de l'étape 5, avec le bon nom de fichier.
Tu peux la copier-coller directement.

---

## 5. Lance le traitement

Copie la commande que le script vient de t'afficher. Elle ressemble à ça :

```bash
./scripts/process_short.sh inputs/short_20260817_153045.mp4
```

Puis **attends**. Compte 5 à 6 minutes pour 60 secondes de vidéo.
Tu verras défiler :

```
✂️  1/3  Suppression des silences (auto-editor)...
🗣  2/3  Transcription française (whisper)...
🎨  3/3  Incrustation des sous-titres (ffmpeg)...
✅ Terminé !
```

C'est l'étape 2/3 qui est longue. C'est normal, ne touche à rien.

---

## 6. Regarde le résultat

Le script t'affiche le chemin du fichier final. Ouvre-le :

```bash
mpv outputs/short_20260817_153045_FINAL.mp4
```

Tu dois voir : une vidéo verticale, tes silences coupés, tes sous-titres en français
incrustés en bas.

**C'est fini. Le workflow marche.**

---

## Si quelque chose bloque

| Message | Quoi faire |
|---|---|
| `❌ Aucune caméra trouvée` | La webcam n'est pas branchée. Rebranche, attends 3 s, relance l'étape 3. |
| `❌ Trop faible — ce micro ne capte rien` | Relance l'étape 3 et tape **`2`** au lieu de `1` pour le micro. |
| `❌ L'audio est quasi silencieux` | Ton enregistrement est muet. Recommence à l'étape 3. |
| La fenêtre de cadrage ne s'ouvre pas | Dis-le-moi, c'est un souci Hyprland. |

---

## Ce que tu voudras peut-être changer après

Une seule ligne à toucher, dans `scripts/process_short.sh` :

- **Sous-titres trop gros ou trop petits** → `FONTSIZE="${FONTSIZE:-14}"`.
  Essaie `12` ou `16`. ⚠️ Ce n'est pas des pixels : ne mets jamais `48`, le texte déborde.
- **Trop de silence coupé** → `--margin 0.1sec` → mets `0.3sec`.
