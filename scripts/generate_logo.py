#!/usr/bin/env python3
"""Generate controlled logo-sticker candidates from an approved local portrait.

The only network operation is performed after both --confirm-upload and FAL_KEY
are present. The selected source image is uploaded to fal.ai and used with
fal-ai/nano-banana/edit. All outputs are saved locally in private/logo-candidates/.

Examples:
  ./scripts/generate_logo.py private/portraits/portrait-...jpg \
      --style vintage-sticker --confirm-upload
  ./scripts/generate_logo.py --list-styles
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "bin" / "python"
ENV_FILE = PROJECT_DIR / ".env"
# Make the tool work when called directly, without asking the user to remember
# which Python environment contains fal-client.
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != (PROJECT_DIR / ".venv").resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])


def load_local_fal_key() -> None:
    """Load only FAL_KEY from .env; never execute or print its contents."""
    if os.environ.get("FAL_KEY") or not ENV_FILE.is_file():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*FAL_KEY\s*=\s*(.*?)\s*$", raw_line)
        if not match:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '\"'}:
            value = value[1:-1]
        if value:
            os.environ["FAL_KEY"] = value
        return


load_local_fal_key()

import fal_client

OUT_DIR = PROJECT_DIR / "private" / "logo-candidates"
ENDPOINT = "fal-ai/nano-banana/edit"

STYLE_PROMPTS = {
    "vintage-sticker": (
        "Transform the person in the reference photo into a premium vintage illustrated "
        "sticker logo. Preserve the exact recognizable facial identity, hairstyle, skin tone, "
        "and expression. Chest-up 3/4 portrait, confident friendly expression, hand-inked "
        "linework, limited screen-print palette of cream, faded teal, burnt orange, and near-black. "
        "Bold die-cut sticker silhouette with a clean off-white border. Centered, no words, no letters, "
        "no watermark, no photorealism, no busy background. Flat clean solid deep navy background."
    ),
    "preserve-style-peel": (
        "Treat the supplied sticker artwork as locked reference art direction. Return an image that is nearly "
        "identical to it: preserve the exact composition, facial likeness, black glasses, pale aqua cap crown, "
        "rust-orange cap brim, cream/off-white sticker border, desaturated teal shirt, deep navy background, "
        "fine hand-inked contour lines, screen-print grain, proportions, and all existing artwork. Do not "
        "recolor, redraw, restyle, replace clothing, change the cap, add text, remove text, change expression, "
        "or change the background. Make exactly one controlled physical change: add a small elegant bottom-right "
        "outer corner of the die-cut sticker gently peeling upward toward the viewer, with a curved paper fold, "
        "cream underside, subtle paper thickness, and a soft realistic shadow below it. Keep the fold entirely "
        "on the outer sticker edge and away from the portrait."
    ),
    "peel-corner-sticker": (
        "Transform the person in the reference photo into a premium vintage illustrated die-cut sticker logo. "
        "Preserve the exact recognizable facial identity, hairstyle, skin tone, and expression. Chest-up "
        "3/4 portrait, confident friendly expression, hand-inked linework, limited screen-print palette "
        "of cream, faded teal, burnt orange, and near-black. The sticker has a thick clean off-white die-cut "
        "border and one clearly visible bottom-right corner gently peeling upward: a curved paper fold, "
        "subtle underside shading, tiny realistic cast shadow, and visible sticker thickness. The lifted "
        "corner must not cover the person's face. Centered, no words, no letters, no watermark, no "
        "photorealism, no busy background. Flat clean solid deep navy background."
    ),
    "retro-tech": (
        "Transform the person in the reference photo into a polished 1980s technical-broadcast "
        "illustrated mascot sticker. Preserve exact recognizable facial identity, hairstyle, skin tone, "
        "and expression. Chest-up portrait, crisp vector-like linework, dark ink-purple, cyan, hot magenta "
        "and warm amber accent palette. Restrained CRT glow, clean die-cut off-white sticker border. "
        "Centered, no words, no letters, no watermark, no photorealism, no busy background. "
        "Flat clean solid deep navy background."
    ),
    "editorial-vector": (
        "Transform the person in the reference photo into a refined editorial vector portrait for a creator "
        "channel logo. Preserve exact recognizable facial identity, hairstyle, skin tone, and expression. "
        "Chest-up portrait, elegant geometric shapes, minimal bold outlines, sophisticated navy, ivory, cyan, "
        "and coral palette. Clean die-cut sticker edge. Centered, no words, no letters, no watermark, "
        "no photorealism, no busy background. Flat clean solid deep navy background."
    ),
    "screenprint": (
        "Transform the person in the reference photo into a hand-pulled retro screen-print sticker portrait. "
        "Preserve exact recognizable facial identity, hairstyle, skin tone, and expression. Chest-up portrait, "
        "slightly imperfect ink texture, halftone shading, thick charcoal contour, limited teal, rust, cream, "
        "and black inks, clean off-white die-cut border. Centered, no words, no letters, no watermark, "
        "no photorealism, no busy background. Flat clean solid deep navy background."
    ),
}


def progress(update: object) -> None:
    status = getattr(update, "status", None) or (update.get("status") if isinstance(update, dict) else None)
    if status:
        print(f"  {status}", flush=True)


def image_urls(result: object) -> list[str]:
    if not isinstance(result, dict):
        return []
    images = result.get("images", [])
    if not isinstance(images, list):
        return []
    return [item.get("url") for item in images if isinstance(item, dict) and item.get("url")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portrait", type=Path, nargs="?", help="Approved local source photograph")
    parser.add_argument("--style", choices=STYLE_PROMPTS, default="vintage-sticker")
    parser.add_argument("--count", type=int, choices=range(1, 5), default=1, help="Candidates (1–4)")
    parser.add_argument("--list-styles", action="store_true")
    parser.add_argument("--confirm-upload", action="store_true", help="Required: authorizes upload of this portrait to fal.ai")
    args = parser.parse_args()

    if args.list_styles:
        print("\n".join(STYLE_PROMPTS))
        return
    if args.portrait is None or not args.portrait.is_file():
        parser.error("Choose an existing portrait file")
    if not args.confirm_upload:
        parser.error("Refusing to upload a face photo without --confirm-upload")
    if not os.environ.get("FAL_KEY"):
        parser.error("FAL_KEY is not set. Export it in your terminal; never paste it into chat.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Uploading approved source portrait to fal.ai: {args.portrait.name}")
    source_url = fal_client.upload_file(args.portrait)
    print("Generating Nano Banana logo candidate(s)…")
    result = fal_client.subscribe(
        ENDPOINT,
        {
            "prompt": STYLE_PROMPTS[args.style],
            "image_urls": [source_url],
            "num_images": args.count,
            "aspect_ratio": "1:1",
            "output_format": "png",
            "safety_tolerance": "4",
        },
        with_logs=True,
        on_queue_update=progress,
    )

    urls = image_urls(result)
    if not urls:
        raise SystemExit(f"No image URLs returned by {ENDPOINT}: {result!r}")
    for index, url in enumerate(urls, start=1):
        output = OUT_DIR / f"{args.portrait.stem}_{args.style}_{index}.png"
        urllib.request.urlretrieve(url, output)
        print(f"✓ {output}")
    print("Review locally before we remove the background, upscale, or use one in the intro.")


if __name__ == "__main__":
    main()
