# Référence

Ce que le guide ne dit pas, pour ne pas l'alourdir. À lire seulement au besoin.

---

## Les scripts

| Script | Rôle |
|---|---|
| `frame.sh` | Aligne une fenêtre pile sur la zone captée (`--off` pour annuler) |
| `record.sh` | Démarre / arrête l'enregistrement de la bande 9:16 |
| `cam.sh` | Cache / remontre le médaillon, même en cours d'enregistrement |
| `finish.sh` | Enchaîne traitement + envoi au téléphone |
| `studio.sh` | Ouvre et place le miroir du Pixel |
| `process_short.sh` | Le moteur : cuts, sous-titres, normalisation 1080x1920 |
| `to_phone.sh` | Envoie un fichier sur le Pixel |
| `short-env.sh` | Active le venv Python pour des tests manuels |

## Comment la zone est calculée

L'écran fait 1920x1080. Une bande 9:16 à cette hauteur fait **607x1080**, centrée.

Avec deux écrans, les coordonnées de `gpu-screen-recorder` sont dans l'espace logique
**global** du compositeur. Il faut donc ajouter le décalage `x/y` de l'écran visé —
sans ça, on capture une bande sur le mauvais moniteur. C'était la cause du désalignement.

```
HDMI-A-1  x=0      y=0      →  bande 607x1080+656+0
DP-3      x=1920   y=-700   →  bande 607x1080+2576+-700
```

## Comment les sous-titres animés fonctionnent

Whisper produit un JSON avec le timing de **chaque mot** (`' Hey,' 0.00 → 0.42`).
`scripts/make_captions.py` le transforme en fichier ASS animé :

- le mot prononcé change de couleur pendant sa durée exacte
- le bloc entre avec un rebond (88 % → 100 % en 110 ms)
- groupes de 4 mots en `karaoke`, 3 en `punch`

Le fichier ASS déclare `PlayResX/Y = 1080x1920`, donc **les tailles sont en vrais pixels**.

> Ce n'était pas le cas avant. L'ancien rendu passait par le filtre `subtitles=` de ffmpeg,
> qui convertit le SRT sur une base 384x288 puis met à l'échelle — `FontSize=14` y valait
> ~90 px à l'écran, et `48` faisait déborder le texte. C'est le piège qui a été éliminé
> en passant à l'ASS généré.

Tous les réglages sont dans `config.sh` à la racine. Le style `simple` réactive l'ancien
rendu SRT si besoin.

### Appeler le générateur à la main

```bash
python3 scripts/make_captions.py outputs/xxx_cut.json sortie.ass \
    --style=punch --font="Archivo Black" --size=150 \
    --highlight="#39FF14" --text="#FFFFFF" --outline-color="#000000"
```

## Préparer le Pixel (une seule fois)

1. **Paramètres → À propos du téléphone**
2. Taper **7 fois** sur « Numéro de build »
3. **Paramètres → Système → Options pour les développeurs**
4. Activer **Débogage USB**
5. Brancher, accepter « Autoriser le débogage USB » sur l'écran du téléphone

## Lisibilité de l'écran du Pixel

La bande fait 607x1080, agrandie ensuite vers 1080x1920. Le Pixel étant nativement en
1080x2424, son écran fait le trajet `1920 → 1080 → 1920`. Le texte des apps est donc un
peu adouci.

Deux leviers gratuits :

1. **Déjà automatique** — `studio.sh` interroge le Pixel (`adb shell wm size`) et ne
   demande à scrcpy que la tranche 9:16 centrale plutôt que l'écran entier. La fenêtre
   fait alors 607 px de large, soit exactement la bande. ~26 % de détail utile en plus.
2. **Monte la taille d'affichage du Pixel** — Paramètres → Affichage → Taille d'affichage
   et texte. Une grosse UI encaisse bien mieux la réduction d'échelle.

### Faut-il acheter un meilleur moniteur ?

Non. Un 1440p ferait passer l'étirement de 1,78× à 1,33× — gain modeste pour de l'argent
réel. Et surtout **pas de 4K** : mesuré sur cette machine, l'encodage VP9 logiciel tient
2,27× le temps réel en 1440p mais seulement **1,05× en 4K**. Tu perdrais des images.
Le goulot n'est pas l'écran, c'est le CPU (Ryzen 7 1700, 2017).

## Coins arrondis du médaillon

`record.sh` et `cam.sh` posent une règle Hyprland `rounding = 20` sur la fenêtre du
médaillon. Elle est **sans effet avec le thème Omarchy actuel**, qui a
`decoration:rounding = 0`. Change pour un thème à coins ronds et le médaillon suivra.

## Pourquoi Recordly a été abandonné

Ses fonctions étaient séduisantes — auto-zoom au curseur, fond stylisé — mais il lague de
façon rédhibitoire sur cette machine.

Le lanceur d'origine forçait `--disable-gpu`, ce qui mettait tout le rendu Electron sur le
CPU. Le correctif a bien remis Recordly sur la RTX 3070 (vérifié : processus GPU présent,
2,2 % de CPU au repos) — **mais ça n'a rien changé en usage réel**. Le goulot est ailleurs,
dans Recordly, et n'a pas été identifié.

L'enregistrement passe donc par `gpu-screen-recorder` (NVENC), l'outil derrière
l'enregistreur natif d'Omarchy : médaillon webcam, micro, encodage GPU, zéro configuration.

Le workflow d'origine bâti sur Recordly est conservé dans
`arch_linux_shorts_workflow_fr.md`. Les anciens guides sont dans `archive/`.

## Les touches M1–M5 du clavier ne sont pas utilisables

Recherche menée le 2026-08-18, conclusion négative. À ne pas refaire.

Le clavier est derrière un récepteur sans fil **Compx `3554:fa09`** (chaîne USB :
manufacturer `CX`, product `2.4G Wireless Receiver`).

Ses touches macro sont programmées en firmware pour envoyer des raccourcis d'édition :

| Touche | Émet |
|---|---|
| M1 | `Ctrl+Z` |
| M2 | `Ctrl+X` |
| M3 | `Ctrl+A` |
| M4 | `Ctrl+V` |
| M5 | `Ctrl+C` |

Et surtout : elles sortent sur **le même nœud d'entrée** (`event2`) que les touches
normales — vérifié en comparant avec `a s d f`, qui sortent aussi sur `event2`.

Conséquence : appuyer sur M1 produit un flux d'événements **identique** à une vraie
frappe `Ctrl+Z`. Il n'y a rien à distinguer, donc `keyd`, `xremap` et les règles
Hyprland ne peuvent pas séparer les deux. Les lier casserait l'annulation, le
copier-coller et la sélection dans toutes les applications.

Aucun outil Linux ne configure ces puces Compx (ni QMK, ni VIA, ni projet open source).
La seule voie serait le logiciel Windows du fabricant, pour reprogrammer M1–M5 vers des
codes inutilisés comme **F13–F17**. Ces codes-là se lieraient sans aucun conflit.

Outil de diagnostic conservé : `scripts/sniff_keys.py` (à lancer avec `sudo`), qui dit
quel périphérique émet quelle touche.

> ⚠️ M1 envoie `Ctrl+Z` et M5 `Ctrl+C` : dans un terminal, ils suspendent ou tuent le
> processus en cours — y compris le renifleur lui-même. Le script ignore ces signaux,
> mais `sudo` reste sensible à `Ctrl+Z`. Presser M2/M3/M4 suffit au diagnostic.
