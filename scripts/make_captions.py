#!/usr/bin/env python3
"""
make_captions.py — construit des sous-titres ASS animés à partir du JSON de Whisper.

Whisper donne le timing de CHAQUE mot. On s'en sert pour animer :
le mot prononcé change de couleur, et le bloc apparaît avec un petit rebond.

Usage:
    make_captions.py transcription.json sortie.ass [options]

Options:
    --style=karaoke|punch   --font=Anton        --size=130
    --marginv=430           --outline=6
    --text=#FFFFFF          --highlight=#FFD700 --outline-color=#000000
    --fillers="euh,hum,tu sais"   mots masqués à l'écran (audio inchangé)

Styles :
    karaoke  la phrase reste affichée, le mot prononcé s'allume (défaut)
    punch    2-3 mots à la fois, très gros, façon Reels
"""
import json
import re
import sys
import unicodedata


def norm(w):
    """Minuscules, sans ponctuation ni accents — pour comparer les mots."""
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z']", "", w)


def drop_fillers(words, fillers):
    """Retire les disfluences de l'AFFICHAGE. L'audio n'est pas touché.

    Gère les expressions de plusieurs mots ("tu sais") en comparant des
    séquences consécutives, le plus long d'abord.
    """
    if not fillers:
        return words

    single = {f for f in fillers if " " not in f}
    multi = sorted([f.split() for f in fillers if " " in f], key=len, reverse=True)

    keep = [True] * len(words)
    normed = [norm(w.get("word", "")) for w in words]

    for seq in multi:
        n = len(seq)
        for i in range(len(words) - n + 1):
            if all(keep[i:i + n]) and normed[i:i + n] == seq:
                for j in range(i, i + n):
                    keep[j] = False

    for i, nw in enumerate(normed):
        if keep[i] and nw in single:
            keep[i] = False

    return [w for i, w in enumerate(words) if keep[i]]

def ass_color(hexrgb):
    """#RRGGBB -> &H00BBGGRR. L'ASS stocke les couleurs à l'envers (BGR)."""
    h = hexrgb.strip().lstrip("#")
    if len(h) != 6:
        raise SystemExit(f"Couleur invalide : {hexrgb} (attendu #RRGGBB)")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def ass_time(t):
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def esc(s):
    return s.replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def header(font, size, marginv, outline, c_text, c_outline):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},{c_text},{c_text},{c_outline},{c_outline},0,0,0,0,100,100,0,0,1,{outline},3,2,60,60,{marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def chunks(words, n):
    for i in range(0, len(words), n):
        yield words[i:i + n]


def build(data, style, font, size, marginv, outline, c_text, c_outline, c_hl, fillers):
    out = [header(font, size, marginv, outline, c_text, c_outline)]
    per_line = 3 if style == "punch" else 4

    for seg in data.get("segments", []):
        words = [w for w in seg.get("words", []) if w.get("word", "").strip()]
        words = drop_fillers(words, fillers)
        if not words:
            continue

        for group in chunks(words, per_line):
            text = " ".join(esc(w["word"]) for w in group)
            g_start, g_end = group[0]["start"], group[-1]["end"]

            for i, w in enumerate(group):
                start = w["start"] if i else g_start
                end = w["end"] if i < len(group) - 1 else g_end
                if end <= start:
                    continue

                # La ligne entière, le mot courant en jaune
                parts = []
                for j, ww in enumerate(group):
                    t = esc(ww["word"])
                    if j == i:
                        parts.append(f"{{\\c{c_hl}}}{t}{{\\c{c_text}}}")
                    else:
                        parts.append(t)
                line = " ".join(parts)

                # Petit rebond seulement au premier mot du bloc
                anim = r"{\fscx88\fscy88\t(0,110,\fscx100\fscy100)}" if i == 0 else ""

                out.append(
                    f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Main,,0,0,0,,{anim}{line}"
                )
    return "\n".join(out) + "\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(
        a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a
    )
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    style = opts.get("style", "karaoke")
    font = opts.get("font", "Anton")
    size = int(opts.get("size", 150 if style == "punch" else 130))
    marginv = int(opts.get("marginv", 430))
    outline = int(opts.get("outline", 6))

    c_text = ass_color(opts.get("text", "#FFFFFF"))
    c_outline = ass_color(opts.get("outline-color", "#000000"))
    c_hl = ass_color(opts.get("highlight", "#FFD700"))

    # Disfluences à masquer à l'écran. Elles restent dans l'audio.
    raw = opts.get("fillers", "")
    fillers = {norm(p) if " " not in p else " ".join(norm(x) for x in p.split())
               for p in raw.split(",") if p.strip()}
    fillers.discard("")

    data = json.load(open(args[0]))
    open(args[1], "w").write(
        build(data, style, font, size, marginv, outline, c_text, c_outline, c_hl, fillers)
    )
    print(f"✅ {args[1]}  (style={style}, police={font}, taille={size})")


if __name__ == "__main__":
    main()
