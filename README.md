# Short Workflow

A fast, local-first workflow for creating vertical **Shorts, Reels, and tech-tip videos** on **Omarchy Linux + Hyprland**.

It provides a small terminal control panel to prepare a 9:16 recording area, show or hide a Pixel and camera overlay, record, caption, review, and send the result to an Android phone.

## What it does

- Choose a **left, center, or right** vertical capture area
- Record the real desktop, including the Hyprland bar and icons
- Toggle a clean studio background, Pixel mirror, and webcam during recording
- Capture microphone audio with GPU-accelerated recording
- Turn recordings into **1080×1920** videos
- Remove silence, generate French captions, and burn in animated subtitles
- Review the final video locally or send it to a connected Pixel
- Capture a portrait and generate private sticker-logo candidates with fal.ai

## Launch

```bash
# Main recording control panel
./bin/short-studio

# Portrait → sticker-logo workflow
./bin/logo-studio
```

On this machine, `SUPER + ALT + D` opens Short Studio.

## Workflow

```text
Prepare area → show studio / Pixel / camera → record → process → review → send to Pixel
```

The TUI intentionally keeps the recording workflow simple:

1. Choose **Left**, **Center**, or **Right**
2. Click **Prepare area**
3. Toggle **Studio**, **Pixel**, or **Camera** when needed
4. Start / stop recording
5. Process the finished short

## Stack

### Desktop and capture

- [Omarchy](https://omarchy.org/)
- [Hyprland](https://hypr.land/)
- `gpu-screen-recorder` for GPU screen capture
- `scrcpy` for Android / Pixel mirroring
- `mpv` for camera, preview, and review windows
- A V4L2 webcam
- PipeWire / PulseAudio microphone input

### Processing

- [FFmpeg](https://ffmpeg.org/) and FFprobe
- [auto-editor](https://github.com/WyattBlue/auto-editor) for silence removal
- [OpenAI Whisper](https://github.com/openai/whisper) for French transcription
- Custom ASS subtitle generation for word-highlighted captions
- NVIDIA CUDA when available for faster transcription

### Control applications

- Python 3.14
- [Textual](https://textual.textualize.io/) for the Short Studio TUI
- Bash for small system integrations

### Logo workflow

- Local 4K webcam capture
- [fal.ai](https://fal.ai/) / Nano Banana image editing for private logo candidates
- ImageMagick for contact sheets and local image work

### Motion graphics

[HyperFrames](https://hyperframes.heygen.com/) is installed locally for upcoming branded intros, logo animation, and vertical motion graphics.

## Privacy and repository policy

This repository contains the reusable workflow and public background assets only.

The following remain local and are ignored by Git:

```text
.env                    # API credentials
private/portraits/      # raw camera captures
private/logo-candidates/# generated logo experiments
private/recordings/     # raw recordings
private/exports/        # finished personal videos
.venv/                  # local Python environment
```

Set `FAL_KEY` in the local `.env` file for the logo generator. Never commit it.

## Project layout

```text
app/                    Textual applications
bin/                    User-facing launch commands
scripts/                Recording, processing, and logo helpers
assets/backgrounds/     Reusable visual backgrounds
assets/brand/           Approved public branding assets
private/                Local media and generated output; ignored by Git
```

## Status

Built for one creator workflow on Omarchy/Hyprland. It is intentionally opinionated and optimized for quickly making clean vertical technical videos.
