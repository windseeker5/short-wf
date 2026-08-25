# Faire une capsule

## Les raccourcis clavier

| Raccourci | Lettre | Ce que ça fait |
|---|---|---|
| **`SUPER + ALT + D`** | **D**émarrer / ca**D**rer | Cale la fenêtre active sur la zone qui sera enregistrée |
| **`SUPER + ALT + R`** | **R**ecord | Démarre l'enregistrement — rappuie pour arrêter |
| **`SUPER + ALT + C`** | **C**améra | Cache ou remontre ton médaillon, même en plein enregistrement |
| **`SUPER + ALT + E`** | **E**nvoyer | Coupe les silences, ajoute les sous-titres, envoie au téléphone |
| **`SUPER + T`** | **T**uilé | **Annule le cadrage** — remet la fenêtre à sa place normale |

L'ordre normal : **D** pour cadrer → **R** pour enregistrer → **R** pour arrêter → **E** pour finir
→ **`SUPER + T`** pour ranger ta fenêtre.

> `SUPER + ALT + D` rend la fenêtre flottante pour la caler dans le cadre. Quand tu as fini,
> **`SUPER + T`** la remet en tuilé. Si elle est trop étroite pour cliquer dedans, clique
> dessus d'abord pour lui donner le focus.

Chaque touche te répond par une notification de bureau. Tu n'as jamais besoin d'un terminal.

---

## Les mêmes choses en ligne de commande

```bash
cd /home/kdresdell/Documents/DEV/short-workflow

./scripts/frame.sh      # 1. cadre la fenêtre à montrer      (SUPER+ALT+D)
./scripts/record.sh     # 2. démarre — parle                 (SUPER+ALT+R)
./scripts/record.sh     # 3. arrête                          (SUPER+ALT+R)
./scripts/finish.sh     # 4. coupe, sous-titre, exporte      (SUPER+ALT+E)
```

Le résultat sort en **1080x1920** dans `outputs/`, et part sur ton Pixel s'il est branché.

---

## Ce qu'il faut savoir, et c'est tout

**L'enregistrement capture une bande verticale, pas tout l'écran.**
`frame.sh` met la fenêtre active pile dedans. Tu vois ce que tu enregistres.

**La bande ne bouge pas si tu déplaces une fenêtre.** Elle est fixée au moment où tu lances
`record.sh`. Pour montrer autre chose, change la **position de la bande**, pas la fenêtre.

**La bande est prise sur l'écran qui a le focus.** Tu as deux écrans — clique sur le bon
avant de lancer `record.sh`.

**Fais 2-3 pauses silencieuses** quand tu parles. Elles seront coupées automatiquement.

## Montrer une autre partie de ton écran

Ta barre de menu en haut à droite, un panneau sur le côté… La bande se déplace :

```bash
./scripts/frame.sh  --at=right     # cadre la fenêtre à droite
./scripts/record.sh --at=right     # et enregistre au même endroit
```

`--at=` accepte **`center`** (défaut), **`left`**, **`right`**, ou une zone exacte
`--region=607x1080+1200+0`.

⚠️ Utilise la **même valeur** pour `frame.sh` et `record.sh`, sinon la fenêtre cadrée et la
zone enregistrée ne coïncident pas.

Si la caméra tombe sur ce que tu veux montrer, déplace-la :

```bash
./scripts/record.sh --at=right --cam-pos=bottom-left
```

Coins possibles : `bottom-right` (défaut), `bottom-left`, `top-right`, `top-left`.

Pour figer tes préférences, mets `BAND_AT`, `CAM_SIZE` et `CAM_POS` dans `config.sh`.

---

## Les variantes

| Commande | Effet |
|---|---|
| `./scripts/frame.sh --off` | remet la fenêtre normale |
| `./scripts/record.sh --cam=large` | médaillon plus gros (`small`, `medium`, `large`) |
| `./scripts/record.sh --no-cam` | sans caméra |
| `./scripts/record.sh --at=right` | bande à droite (`center`, `left`, `right`) |
| `./scripts/record.sh --cam-pos=bottom-left` | déplace le médaillon |
| `./scripts/record.sh --monitor=DP-3` | force l'écran |
| `./scripts/cam.sh` | cache / remontre la caméra, **même en cours d'enregistrement** |
| `./scripts/studio.sh` | ouvre le miroir du Pixel, à lancer en premier |
| `CAPTION_STYLE=punch ./scripts/finish.sh` | sous-titres 3 mots à la fois, très gros |

---

## Si ça coince

| Ce que tu vois | Quoi faire |
|---|---|
| La capsule montre le mauvais écran | Clique sur le bon écran, ou `--monitor=NOM` |
| `❌ L'enregistrement n'a pas démarré` | `pkill -f gpu-screen-recorder` puis relance |
| `❌ L'audio est quasi silencieux` | Le micro n'a rien capté. Refais la prise. |
| Médaillon trop petit ou mal placé | `./scripts/cam.sh large` |
| Une fenêtre reste coincée dans le carré | `SUPER + T`, ou `./scripts/frame.sh --off` |
| La caméra n'apparaît pas dans la vidéo | Elle était hors de la bande. Vérifie que `--at=` est le même pour `frame.sh` et `record.sh`. |
| J'ai bougé ma fenêtre, la zone n'a pas suivi | Normal. Utilise `--at=` pour déplacer la bande. |

---

## Changer la police et les couleurs

Tout est dans **`config.sh`**, à la racine du projet. Tu l'ouvres, tu changes, tu sauvegardes,
tu relances `./scripts/finish.sh`. Pas besoin de toucher aux scripts.

```bash
CAPTION_FONT="Anton"            # Anton, Archivo Black, Bebas Neue, Montserrat, Poppins…
CAPTION_HIGHLIGHT="#FFD700"     # le mot prononcé
CAPTION_TEXT="#FFFFFF"          # le reste du texte
CAPTION_SIZE="130"              # en vrais pixels
CAPTION_MARGINV="430"           # hauteur depuis le bas
CAPTION_STYLE="karaoke"         # karaoke | punch | simple
```

Les couleurs sont en **hex normal `#RRGGBB`**. Quelques-unes qui rendent bien :

| | | |
|---|---|---|
| `#FFD700` or | `#00E5FF` cyan | `#39FF14` vert fluo |
| `#FF3B30` rouge | `#FF6B00` orange | `#FF2D95` rose |

Pour voir toutes tes polices : `fc-list : family | tr ',' '\n' | sort -u`

Pour essayer sans modifier le fichier, préfixe la commande :

```bash
CAPTION_HIGHLIGHT="#39FF14" ./scripts/finish.sh
```

### Masquer les « euh » à l'écran

```bash
CAPTION_FILLERS="euh,heu,hum,hmm,ben,bah,hein,tsé,t'sais"
```

Ces mots sont retirés des **sous-titres seulement** — ta voix n'est pas touchée, on les
entend toujours. Les expressions de plusieurs mots marchent (`tu sais`), et les accents
et la ponctuation sont ignorés : `tsé`, `Tsé,` et `TSÉ` sont tous attrapés.

À ajouter si tu les dis souvent : `genre`, `style`, `faque`, `en fait`, `comme`.

> ⚠️ N'y mets pas `le`, `la`, `de`, `et`. Ce sont des *stop words* — utiles à retirer pour
> de la recherche ou de l'indexation, jamais pour des sous-titres : tes phrases
> deviendraient agrammaticales. Ce qu'on retire ici, ce sont des **disfluences**, et ça,
> c'est une bonne pratique établie.

`config.sh` contient aussi `CUT_MARGIN` (agressivité de la coupe des silences) et
`WHISPER_MODEL` (`medium` rapide, `large-v3` plus précis mais ~3× plus lent).

---

## Quand tes fenêtres sont mêlées

`frame.sh` rend une fenêtre **flottante** pour la caler sur la zone captée. Si elle reste
coincée comme ça, voici les raccourcis Omarchy qui te sortent de là.

| Raccourci | Effet |
|---|---|
| **`SUPER + T`** | **remet la fenêtre en tuilé** — c'est celui à retenir |
| `SUPER + F` | plein écran |
| `SUPER + CTRL + F` | plein écran tuilé |
| `SUPER + ALT + F` | pleine largeur |
| `SUPER + Home` | restaure la largeur d'origine |
| `SUPER + ←` `→` `↑` `↓` | change de fenêtre |
| `SUPER + SHIFT + ←` `→` | déplace la fenêtre |
| `SUPER + W` | ferme la fenêtre |

⚠️ Ce n'est **pas** `SUPER + V` — dans un terminal, ça colle le presse-papier.

Pour voir tous tes raccourcis : `omarchy menu keybindings --print`

---

Détails, mesures et historique : [`REFERENCE.md`](REFERENCE.md)
