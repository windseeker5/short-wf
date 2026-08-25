# config.sh — tous tes réglages de sous-titres, à un seul endroit.
#
# Édite ce fichier, sauvegarde, relance ./scripts/finish.sh. C'est tout.
# Pour un essai ponctuel sans toucher au fichier, préfixe la commande :
#     CAPTION_HIGHLIGHT="#00E5FF" ./scripts/finish.sh

# ── Style ────────────────────────────────────────────────────────────────
# karaoke : la phrase reste affichée, le mot prononcé s'allume
# punch   : 3 mots à la fois, très gros, façon Reels
# simple  : sous-titres classiques sans animation
CAPTION_STYLE="${CAPTION_STYLE:-karaoke}"

# ── Police ───────────────────────────────────────────────────────────────
# Installées chez toi : Anton, Archivo Black, Bebas Neue, Montserrat,
#                       Poppins, Inter, Impact
# Pour voir toutes tes polices :  fc-list : family | tr ',' '\n' | sort -u
CAPTION_FONT="${CAPTION_FONT:-Anton}"

# ── Couleurs (hex normal, #RRGGBB) ───────────────────────────────────────
CAPTION_TEXT="${CAPTION_TEXT:-#FFFFFF}"          # le texte au repos
CAPTION_HIGHLIGHT="${CAPTION_HIGHLIGHT:-#FFD700}"     # le mot prononcé  (or)
CAPTION_OUTLINE_COLOR="${CAPTION_OUTLINE_COLOR:-#000000}" # le contour

# Quelques couleurs de surlignage qui rendent bien :
#   #FFD700  or         #00E5FF  cyan       #39FF14  vert fluo
#   #FF3B30  rouge      #FF6B00  orange     #FF2D95  rose

# ── Taille et position ───────────────────────────────────────────────────
# En VRAIS PIXELS sur une image 1080x1920.
CAPTION_SIZE="${CAPTION_SIZE:-170}"      # 130 = standard, 170 = grand format Reels
CAPTION_MARGINV="${CAPTION_MARGINV:-430}"   # hauteur depuis le bas. Monte si ça cache ta caméra.
CAPTION_OUTLINE="${CAPTION_OUTLINE:-8}"     # contour proportionné au texte plus grand

# ── Cadrage et médaillon ─────────────────────────────────────────────────
# Où la bande verticale est prise sur ton écran : center | left | right
# Utilise la MÊME valeur pour frame.sh et record.sh.
BAND_AT="${BAND_AT:-right}"

CAM_SIZE="${CAM_SIZE:-large}"            # small | medium | large
CAM_POS="${CAM_POS:-bottom-center}"      # bottom-center | bottom-right | bottom-left | top-right | top-left

# ── Mots masqués à l'écran ───────────────────────────────────────────────
# Les disfluences ("euh", "hum") n'apportent rien à l'écrit. On les retire des
# SOUS-TITRES seulement : ta voix n'est pas touchée, l'audio reste intact.
#
# ⚠️ N'y mets PAS de mots utiles comme "le", "la", "de", "et". Ce sont des
# stop words au sens recherche/indexation — les enlever ici rendrait tes
# phrases agrammaticales.
#
# Les expressions de plusieurs mots fonctionnent ("tu sais"). Accents et
# ponctuation sont ignorés à la comparaison.
if [ -z "${CAPTION_FILLERS+x}" ]; then
    CAPTION_FILLERS="euh,heu,heuh,hum,hmm,hm,mmh,mmm,mm,ben,bah,hein,tsé,t'sais"
fi

# À ajouter si tu les dis souvent :  genre,style,faque,tu sais,en fait,comme

# ── Coupe des silences ───────────────────────────────────────────────────
# Marge laissée autour de la parole. Plus grand = coupe moins.
CUT_MARGIN="${CUT_MARGIN:-0.1sec}"

# ── Transcription ────────────────────────────────────────────────────────
# medium = rapide et bon. large-v3 = meilleur mais ~3x plus lent.
WHISPER_MODEL="${WHISPER_MODEL:-medium}"
