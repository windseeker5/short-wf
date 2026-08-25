#!/usr/bin/env python3
"""A small, deliberately simple control panel for vertical screen recordings."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, RichLog, Static

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
VENV_DIR = PROJECT_DIR / ".venv"
VIDEO_DIR = Path(os.environ.get("SHORT_WORKFLOW_RECORDINGS_DIR", PROJECT_DIR / "private" / "recordings")).expanduser()
CONFIG_FILE = PROJECT_DIR / "config.sh"
BACKGROUND_IMAGE = PROJECT_DIR / "assets" / "backgrounds" / "after-hours-terminal.png"
GUIDE_IMAGE = Path("/tmp/short-studio-guide.ppm")


@dataclass(frozen=True)
class Monitor:
    name: str
    x: int
    y: int
    width: int
    height: int
    focused: bool = False


@dataclass(frozen=True)
class Region:
    width: int
    height: int
    x: int
    y: int
    monitor: str
    position: str

    @property
    def recorder_value(self) -> str:
        return f"{self.width}x{self.height}+{self.x}+{self.y}"


def config_value(name: str, default: str) -> str:
    """Read a NAME="${NAME:-default}" setting without executing shell code."""
    try:
        text = CONFIG_FILE.read_text(encoding="utf-8")
    except OSError:
        return default
    line = re.search(rf'^\s*{re.escape(name)}\s*=\s*"([^"]*)"', text, re.MULTILINE)
    if not line:
        return default
    value = line.group(1)
    shell_default = re.fullmatch(rf"\$\{{{re.escape(name)}:-([^}}]+)\}}", value)
    return shell_default.group(1) if shell_default else (value or default)


def executable(name: str) -> str | None:
    local = VENV_DIR / "bin" / name
    return str(local) if local.exists() else shutil.which(name)


async def command_output(*args: str, timeout: float = 15) -> tuple[int, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return process.returncode or 0, output.decode(errors="replace").strip()
    except (FileNotFoundError, asyncio.TimeoutError) as error:
        return 127, str(error)


def detached(*args: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class ShortStudio(App[None]):
    TITLE = "Short Studio"
    SUB_TITLE = "Desktop → vertical video"

    CSS = """
    Screen {
        background: #101722;
        color: #dce7f2;
    }

    Header {
        height: 2;
        background: #152235;
        color: #f4f8fc;
    }

    #tally {
        height: 3;
        padding: 1 2;
        background: #17263a;
        color: #8fe3ff;
        text-style: bold;
        border-bottom: solid #27405d;
    }

    #tally.recording {
        background: #9e2633;
        color: white;
        border-bottom: solid #ff6675;
    }

    #main {
        height: 1fr;
        padding: 0 1;
    }

    .panel {
        height: auto;
        margin-top: 1;
        padding: 0 1 1 1;
        border: round #344d69;
        background: #131e2d;
    }

    .panel-title {
        color: #ffbf69;
        text-style: bold;
        margin-bottom: 1;
    }

    .help {
        height: 2;
        color: #9eb3c7;
    }

    .actions {
        height: 4;
        padding-top: 1;
    }

    Button {
        height: 3;
        min-width: 17;
        margin-right: 1;
        background: #263b52;
        border: tall #486887;
    }

    Button:hover, Button:focus {
        background: #345474;
        border: tall #8fe3ff;
    }

    .position-button {
        min-width: 9;
        width: 9;
    }

    .position-selected {
        background: #195b70;
        color: white;
        border: tall #8fe3ff;
    }

    #prepare {
        width: 1fr;
        background: #195b70;
    }

    #clear {
        width: 1fr;
        background: #4a3440;
    }

    #background, #phone, #camera {
        width: 1fr;
        background: #29465f;
    }

    #record {
        width: 1fr;
        background: #9e2633;
    }

    #process { background: #6a4e19; }
    #send { background: #29553e; }

    #latest {
        height: 2;
        padding: 0 1;
        color: #a9c0d5;
    }

    #log {
        height: 8;
        margin-top: 1;
        padding: 0 1;
        border: round #344d69;
        background: #0c131d;
        scrollbar-color: #486887;
    }

    Footer {
        height: 1;
        background: #152235;
    }
    """

    BINDINGS = [
        ("p", "prepare", "Prepare"),
        ("r", "record", "Record / stop"),
        ("b", "background", "Studio / desktop"),
        ("c", "camera", "Show / hide camera"),
        ("f", "process", "Process"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.monitors: dict[str, Monitor] = {}
        self.main_monitor: Monitor | None = None
        self.position = config_value("BAND_AT", "right")
        if self.position not in {"left", "center", "right"}:
            self.position = "right"
        self.region: Region | None = None
        self.recording = False
        self.record_started = 0.0
        self.recorded_file: Path | None = None
        self.final_file: Path | None = None
        self.background_visible = False
        self.phone_visible = False
        self.camera_visible = False
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("● NOT PREPARED   Choose where the vertical recording goes", id="tally")
        with Vertical(id="main"):
            with Vertical(classes="panel"):
                yield Label("1  PREPARE THE RECORDING AREA", classes="panel-title")
                yield Static(
                    "Records your desktop exactly as shown — including the Hyprland bar and icons.",
                    classes="help",
                )
                with Horizontal(classes="actions"):
                    yield Button("Left", id="left", classes="position-button")
                    yield Button("Center", id="center", classes="position-button")
                    yield Button("Right", id="right", classes="position-button")
                    yield Button("Prepare area", id="prepare")
                    yield Button("Clear desktop", id="clear", disabled=True)
            with Vertical(classes="panel"):
                yield Label("2  SHOW WHAT YOU NEED", classes="panel-title")
                yield Static("Toggle the clean studio, Pixel, or camera — even while recording.", classes="help")
                with Horizontal(classes="actions"):
                    yield Button("Show desktop", id="background", disabled=True)
                    yield Button("Show Pixel", id="phone", disabled=True)
                    yield Button("Show camera", id="camera", disabled=True)
            with Vertical(classes="panel"):
                yield Label("3  RECORD AND FINISH", classes="panel-title")
                with Horizontal(classes="actions"):
                    yield Button("● Start recording", id="record", disabled=True)
                    yield Button("Process short", id="process", disabled=True)
                    yield Button("Send to Pixel", id="send", disabled=True)
                    yield Button("Open video", id="open", disabled=True)
            yield Static("Latest: no recording in this session", id="latest")
            yield RichLog(id="log", markup=True, wrap=True, highlight=True)
        yield Footer()

    async def on_mount(self) -> None:
        self.set_interval(1.0, self.update_tally)
        self.update_position_buttons()
        await self.preflight()
        await self.recover_latest_session()
        self.restore_buttons()
        self.write_log("[bold #8fe3ff]Ready.[/] Choose left, center, or right — then prepare.")

    def write_log(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    def update_position_buttons(self) -> None:
        for position in ("left", "center", "right"):
            button = self.query_one(f"#{position}", Button)
            button.set_class(position == self.position, "position-selected")

    def update_tally(self) -> None:
        tally = self.query_one("#tally", Static)
        if self.recording:
            elapsed = int(time.monotonic() - self.record_started)
            tally.add_class("recording")
            tally.update(f"● RECORDING   {elapsed // 60:02d}:{elapsed % 60:02d}   {self.region.recorder_value if self.region else ''}")
            self.query_one("#record", Button).label = "■ Stop recording"
        elif not self.busy:
            tally.remove_class("recording")
            if self.region:
                tally.update(
                    f"● READY   {self.region.monitor} · {self.position.upper()} · "
                    f"{self.region.width}×{self.region.height}"
                )
            else:
                tally.update("● NOT PREPARED   Choose where the vertical recording goes")
            self.query_one("#record", Button).label = "● Start recording"

    def set_busy(self, message: str) -> None:
        self.busy = True
        for button in self.query(Button):
            button.disabled = True
        self.query_one("#tally", Static).update(f"◆ WORKING   {message}")

    def restore_buttons(self) -> None:
        self.busy = False
        for position in ("left", "center", "right"):
            self.query_one(f"#{position}", Button).disabled = self.recording
        self.query_one("#prepare", Button).disabled = self.recording
        prepared = self.region is not None
        self.query_one("#clear", Button).disabled = not prepared or self.recording
        self.query_one("#background", Button).disabled = not prepared
        self.query_one("#phone", Button).disabled = not prepared
        self.query_one("#camera", Button).disabled = not prepared
        self.query_one("#record", Button).disabled = not prepared
        self.query_one("#process", Button).disabled = self.recorded_file is None or self.recording
        self.query_one("#send", Button).disabled = self.final_file is None
        self.query_one("#open", Button).disabled = self.final_file is None
        self.update_tally()

    async def json_command(self, *args: str) -> object:
        code, output = await command_output(*args)
        if code:
            raise RuntimeError(output or f"{' '.join(args)} failed")
        return json.loads(output)

    async def preflight(self) -> None:
        try:
            raw = await self.json_command("hyprctl", "monitors", "-j")
            monitors: dict[str, Monitor] = {}
            for item in raw if isinstance(raw, list) else []:
                monitor = Monitor(
                    str(item["name"]), int(item["x"]), int(item["y"]),
                    int(item["width"]), int(item["height"]), bool(item.get("focused")),
                )
                monitors[monitor.name] = monitor
            self.monitors = monitors

            configured = config_value("CAPTURE_MONITOR", "")
            self.main_monitor = monitors.get(configured)
            if self.main_monitor is None:
                self.main_monitor = next(
                    (m for m in monitors.values() if m.x == 0 and m.y == 0),
                    next(iter(monitors.values()), None),
                )
            if self.main_monitor:
                self.write_log(
                    f"[green]✓[/] Main screen: {self.main_monitor.name} "
                    f"({self.main_monitor.width}×{self.main_monitor.height})"
                )
            else:
                self.write_log("[bold red]No monitor detected.[/]")

            required = ("hyprctl", "gpu-screen-recorder", "ffmpeg", "ffprobe", "mpv", "adb", "scrcpy")
            missing = [name for name in required if not executable(name)]
            missing += [name for name in ("auto-editor", "whisper") if not executable(name)]
            if missing:
                self.write_log(f"[bold red]Missing tools:[/] {', '.join(missing)}")
            else:
                self.write_log("[green]✓[/] Recording and processing tools available")
        except Exception as error:
            self.write_log(f"[bold red]Startup check failed:[/] {error}")

    async def valid_video(self, path: Path) -> bool:
        if not path.exists() or path.stat().st_size == 0:
            return False
        code, _ = await command_output(
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        )
        return code == 0

    async def recover_latest_session(self) -> None:
        """Recover the newest recording/final output after restarting the TUI."""
        recordings = list(VIDEO_DIR.glob("short-*.mp4"))
        if not recordings:
            return
        latest = max(recordings, key=lambda path: path.stat().st_mtime)
        self.recorded_file = latest
        final = PROJECT_DIR / "private" / "exports" / f"{latest.stem}_FINAL.mp4"
        if await self.valid_video(final):
            self.final_file = final
            self.query_one("#latest", Static).update(f"Ready: {final.name}")
            self.write_log(f"[green]✓ Recovered finished short:[/] {final.name}")
        else:
            self.query_one("#latest", Static).update(f"Latest recording: {latest.name}")
            self.write_log(f"Recovered recording: {latest.name}")

    def calculate_region(self) -> Region:
        monitor = self.main_monitor
        if monitor is None:
            raise RuntimeError("Main screen not found")
        width = monitor.height * 9 // 16
        if self.position == "left":
            x = monitor.x
        elif self.position == "center":
            x = monitor.x + (monitor.width - width) // 2
        else:
            x = monitor.x + monitor.width - width
        return Region(width, monitor.height, x, monitor.y, monitor.name, self.position)

    async def find_client(self, title: str, attempts: int = 60) -> dict | None:
        for _ in range(attempts):
            clients = await self.json_command("hyprctl", "clients", "-j")
            client = next((item for item in clients if item.get("title") == title), None)
            if client:
                return client
            await asyncio.sleep(0.1)
        return None

    async def frame_client(self, client: dict, width: int, height: int, x: int, y: int) -> None:
        address = str(client.get("address", ""))
        if not address:
            raise RuntimeError("The window disappeared")
        selector = f'window = "address:{address}"'
        if not bool(client.get("floating")):
            code, output = await command_output(
                "hyprctl", "dispatch", f'hl.dsp.window.float({{ action = "toggle", {selector} }})'
            )
            if code:
                raise RuntimeError(output or "Could not float a preview window")
            await asyncio.sleep(0.15)
        for dispatch in (
            f"hl.dsp.window.resize({{ x = {width}, y = {height}, relative = false, {selector} }})",
            f"hl.dsp.window.move({{ x = {x}, y = {y}, relative = false, {selector} }})",
        ):
            code, output = await command_output("hyprctl", "dispatch", dispatch)
            if code:
                raise RuntimeError(output or "Could not position a preview window")
            await asyncio.sleep(0.12)

    async def close_window(self, title: str) -> None:
        client = await self.find_client(title, attempts=1)
        if client and client.get("pid"):
            try:
                os.kill(int(client["pid"]), 15)
            except (ProcessLookupError, ValueError):
                pass

    async def hide_guides(self) -> None:
        await self.close_window("ShortGuideLeft")
        await self.close_window("ShortGuideRight")

    async def hide_camera(self) -> None:
        script = 'source "$1"; stop_webcam'
        await command_output("bash", "-c", script, "_", str(SCRIPTS_DIR / "lib.sh"))
        self.camera_visible = False

    async def show_background(self) -> None:
        if self.region is None:
            return
        client = await self.find_client("CaptureBackground", attempts=1)
        if client is None:
            if not BACKGROUND_IMAGE.exists():
                raise RuntimeError(f"Studio background missing: {BACKGROUND_IMAGE}")
            detached(
                "mpv", str(BACKGROUND_IMAGE), "--loop-file=inf",
                "--title=CaptureBackground", "--wayland-app-id=CaptureBackground",
                "--no-border", "--no-audio", "--no-osc", "--osd-level=0", "--really-quiet",
            )
            client = await self.find_client("CaptureBackground")
        if client is None:
            raise RuntimeError("The studio background window did not appear")
        await self.frame_client(
            client, self.region.width, self.region.height, self.region.x, self.region.y
        )
        self.background_visible = True

    async def clear_previews(self) -> None:
        """Remove guides and overlays tied to the previous recording area."""
        await self.hide_guides()
        await self.close_window("PhoneCapture")
        await self.hide_camera()
        await self.close_window("CaptureBackground")
        self.background_visible = False
        self.phone_visible = False
        self.query_one("#background", Button).label = "Show studio"
        self.query_one("#phone", Button).label = "Show Pixel"
        self.query_one("#camera", Button).label = "Show camera"

    async def show_guides(self, region: Region) -> None:
        """Draw thin cyan lines immediately outside the recorded strip."""
        await self.hide_guides()
        if not GUIDE_IMAGE.exists():
            # A tiny cyan PPM image; mpv scales it into a vertical guide line.
            GUIDE_IMAGE.write_bytes(b"P6\n1 1\n255\n" + bytes((65, 210, 255)))

        guides: list[tuple[str, int]] = []
        if self.position != "left":
            guides.append(("ShortGuideLeft", region.x - 5))
        if self.position != "right":
            guides.append(("ShortGuideRight", region.x + region.width))

        for title, x in guides:
            detached(
                "mpv", str(GUIDE_IMAGE), "--loop-file=inf", f"--title={title}",
                f"--wayland-app-id={title}", "--no-border", "--no-audio", "--no-osc",
                "--osd-level=0", "--really-quiet",
            )
            client = await self.find_client(title)
            if client:
                await self.frame_client(client, 5, region.height, x, region.y)

    async def clear_area(self) -> None:
        if self.recording:
            return
        self.set_busy("Restoring desktop…")
        try:
            await self.clear_previews()
            self.region = None
            self.write_log("[bold green]Recording area removed.[/] Guides, Pixel, and camera closed.")
        except Exception as error:
            self.write_log(f"[bold red]Desktop cleanup failed:[/] {error}")
        finally:
            self.restore_buttons()

    async def prepare_area(self) -> None:
        if self.recording:
            return
        self.set_busy("Preparing the recording area…")
        try:
            self.region = self.calculate_region()
            await self.show_background()
            await self.show_guides(self.region)
            self.query_one("#background", Button).label = "Show desktop"
            self.write_log(
                f"[bold green]Recording area ready:[/] {self.position} side of "
                f"{self.region.monitor} · {self.region.width}×{self.region.height}"
            )
            self.write_log("After Hours Terminal background enabled. Use “Show desktop” to reveal the screen.")
        except Exception as error:
            self.region = None
            self.write_log(f"[bold red]Prepare failed:[/] {error}")
            self.notify(str(error), title="Prepare failed", severity="error")
        finally:
            self.restore_buttons()

    async def show_phone(self) -> None:
        if self.region is None:
            return
        code, output = await command_output("adb", "devices")
        if code or not any("\tdevice" in line for line in output.splitlines()):
            raise RuntimeError("Pixel not connected or USB debugging not authorized")
        # A Pixel screen is taller than 9:16 (for example 1080×2424). Do not
        # crop it to the recording strip: fit the complete phone screen inside
        # the strip and center it, preserving its native aspect ratio.
        code, size_output = await command_output("adb", "shell", "wm", "size")
        sizes = re.findall(r"(\d+)x(\d+)", size_output)
        if code == 0 and sizes:
            phone_width, phone_height = map(int, sizes[-1])
        else:
            phone_width, phone_height = 1080, 2400

        window_height = self.region.height
        window_width = max(1, round(window_height * phone_width / phone_height))
        if window_width > self.region.width:
            window_width = self.region.width
            window_height = max(1, round(window_width * phone_height / phone_width))
        window_x = self.region.x + (self.region.width - window_width) // 2
        window_y = self.region.y + (self.region.height - window_height) // 2

        client = await self.find_client("PhoneCapture", attempts=1)
        if client is None:
            detached(
                "scrcpy", "--show-touches", "--max-fps=60", "--window-title=PhoneCapture",
                f"--window-width={window_width}", f"--window-height={window_height}",
                f"--window-x={window_x}", f"--window-y={window_y}",
                "--stay-awake", "--no-audio",
            )
            client = await self.find_client("PhoneCapture")
        if client is None:
            raise RuntimeError("The Pixel window did not appear")
        await self.frame_client(client, window_width, window_height, window_x, window_y)
        self.write_log(
            f"Pixel fitted without cropping · native {phone_width}×{phone_height} · "
            f"window {window_width}×{window_height}"
        )
        self.phone_visible = True

    async def toggle_phone(self) -> None:
        if self.region is None:
            return
        self.set_busy("Changing Pixel preview…")
        try:
            if self.phone_visible or await self.find_client("PhoneCapture", attempts=1):
                await self.close_window("PhoneCapture")
                self.phone_visible = False
                self.write_log("Pixel hidden")
            else:
                await self.show_phone()
                self.write_log("[green]Pixel shown inside the recording area[/]")
        except Exception as error:
            self.phone_visible = False
            self.write_log(f"[bold red]Pixel failed:[/] {error}")
            self.notify(str(error), title="Pixel failed", severity="error")
        finally:
            self.query_one("#phone", Button).label = "Hide Pixel" if self.phone_visible else "Show Pixel"
            self.restore_buttons()

    async def show_camera(self) -> None:
        if self.region is None:
            return
        size = config_value("CAM_SIZE", "large")
        position = config_value("CAM_POS", "bottom-center")
        script = (
            'source "$1"; compute_band "$2" ""; '
            'start_webcam "$3" && place_webcam "$3" "$4"'
        )
        code, output = await command_output(
            "bash", "-c", script, "_", str(SCRIPTS_DIR / "lib.sh"),
            self.region.recorder_value, size, position, timeout=15,
        )
        if code:
            raise RuntimeError(output or "No webcam detected")
        self.camera_visible = True

    async def toggle_background(self) -> None:
        if self.region is None:
            return
        self.set_busy("Changing studio background…")
        try:
            visible = await self.find_client("CaptureBackground", attempts=1)
            if self.background_visible or visible:
                await self.close_window("CaptureBackground")
                self.background_visible = False
                self.write_log("Studio hidden — desktop is visible in the recording area")
            else:
                # A newly opened background would stack over existing overlays.
                # Re-open those overlays afterward to keep the intended order:
                # background → Pixel → camera.
                had_phone = self.phone_visible or bool(await self.find_client("PhoneCapture", attempts=1))
                had_camera = self.camera_visible or bool(await self.find_client("WebcamOverlay", attempts=1))
                if had_phone:
                    await self.close_window("PhoneCapture")
                    self.phone_visible = False
                if had_camera:
                    await self.hide_camera()
                await self.show_background()
                if had_phone:
                    await self.show_phone()
                if had_camera:
                    await self.show_camera()
                self.write_log("[green]After Hours Terminal studio background shown[/]")
        except Exception as error:
            self.write_log(f"[bold red]Background failed:[/] {error}")
            self.notify(str(error), title="Background failed", severity="error")
        finally:
            self.query_one("#background", Button).label = (
                "Show desktop" if self.background_visible else "Show studio"
            )
            self.query_one("#phone", Button).label = "Hide Pixel" if self.phone_visible else "Show Pixel"
            self.query_one("#camera", Button).label = "Hide camera" if self.camera_visible else "Show camera"
            self.restore_buttons()

    async def toggle_camera(self) -> None:
        if self.region is None:
            return
        self.set_busy("Changing camera preview…")
        try:
            visible = await self.find_client("WebcamOverlay", attempts=1)
            if self.camera_visible or visible:
                await self.hide_camera()
                self.write_log("Camera hidden")
            else:
                await self.show_camera()
                size = config_value("CAM_SIZE", "large")
                position = config_value("CAM_POS", "bottom-center")
                self.write_log(f"[green]Camera shown[/] · {size} · {position}")
        except Exception as error:
            self.camera_visible = False
            self.write_log(f"[bold red]Camera failed:[/] {error}")
            self.notify(str(error), title="Camera failed", severity="error")
        finally:
            self.query_one("#camera", Button).label = "Hide camera" if self.camera_visible else "Show camera"
            self.restore_buttons()

    async def start_recording(self) -> None:
        if self.region is None:
            return
        code, _ = await command_output("pgrep", "-f", "^gpu-screen-recorder")
        if code == 0:
            self.write_log("[bold red]Another screen recording is already active.[/]")
            return
        self.set_busy("Starting recorder…")
        try:
            # Guide lines sit outside the region, but hiding them gives a completely clean capture.
            await self.hide_guides()
            before = set(VIDEO_DIR.glob("short-*.mp4"))
            code, output = await command_output(
                str(SCRIPTS_DIR / "record.sh"),
                f"--region={self.region.recorder_value}", "--no-cam", timeout=20,
            )
            if code:
                raise RuntimeError(output.splitlines()[-1] if output else "Recorder did not start")
            candidates = list(set(VIDEO_DIR.glob("short-*.mp4")) - before)
            if not candidates:
                candidates = list(VIDEO_DIR.glob("short-*.mp4"))
            if not candidates:
                raise RuntimeError("Recorder started but no video file appeared")
            self.recorded_file = max(candidates, key=lambda path: path.stat().st_mtime)
            self.final_file = None
            self.recording = True
            self.record_started = time.monotonic()
            self.write_log(f"[bold #ff6675]● Recording[/] {self.region.recorder_value}")
        except Exception as error:
            self.write_log(f"[bold red]Recording failed:[/] {error}")
            await self.show_guides(self.region)
            self.notify(str(error), title="Recording failed", severity="error")
        finally:
            self.restore_buttons()

    async def stop_recording(self) -> None:
        self.set_busy("Finalizing recording…")
        try:
            code, output = await command_output(str(SCRIPTS_DIR / "record.sh"), timeout=20)
            if code:
                raise RuntimeError(output.splitlines()[-1] if output else "Could not stop recorder")
            duration = int(time.monotonic() - self.record_started)
            self.recording = False
            # record.sh closes WebcamOverlay while finalizing.
            self.camera_visible = False
            self.query_one("#camera", Button).label = "Show camera"
            if self.recorded_file:
                self.query_one("#latest", Static).update(f"Recorded: {self.recorded_file.name} · {duration}s")
            self.write_log(f"[bold green]Recording saved[/] · {duration}s")
            if self.region:
                await self.show_guides(self.region)
        except Exception as error:
            self.write_log(f"[bold red]Stop failed:[/] {error}")
        finally:
            self.recording = False
            self.restore_buttons()

    async def stream_process(self, args: Iterable[str], log_path: Path | None = None) -> int:
        """Stream command output without asyncio's newline-size limitation.

        auto-editor writes progress updates separated by carriage returns rather
        than newlines. Reading it with ``async for line`` eventually raises
        LimitOverrunError after 64 KiB. Fixed-size reads cannot hit that limit.
        """
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            limit=1024 * 1024,
        )
        assert process.stdout is not None
        pending = ""
        last_progress_at = 0.0
        log_file = log_path.open("w", encoding="utf-8") if log_path else None
        try:
            while chunk := await process.stdout.read(4096):
                text = chunk.decode(errors="replace")
                if log_file:
                    log_file.write(text)
                    log_file.flush()
                pending += text

                # Newline messages are useful status/error messages. Carriage
                # returns are progress redraws; show at most one per second.
                while True:
                    newline = pending.find("\n")
                    carriage = pending.find("\r")
                    separators = [index for index in (newline, carriage) if index >= 0]
                    if not separators:
                        break
                    index = min(separators)
                    separator = pending[index]
                    line, pending = pending[:index].strip(), pending[index + 1 :]
                    if not line:
                        continue
                    if separator == "\n":
                        self.write_log(line)
                    elif time.monotonic() - last_progress_at >= 1.0:
                        self.write_log(f"[dim]{line}[/]")
                        last_progress_at = time.monotonic()

                # A tool producing neither separator must never grow memory
                # without bound. Preserve the complete bytes in the log file.
                if len(pending) > 16_384:
                    self.write_log(f"[dim]{pending[-500:]}[/]")
                    pending = ""
            if pending.strip():
                self.write_log(pending.strip())
        finally:
            if log_file:
                log_file.close()
        return await process.wait()

    async def process_recording(self) -> None:
        if self.recorded_file is None or self.recording:
            return
        self.set_busy("Cutting and captioning…")
        process_log = PROJECT_DIR / "private" / "exports" / f"{self.recorded_file.stem}_process.log"
        expected_final = PROJECT_DIR / "private" / "exports" / f"{self.recorded_file.stem}_FINAL.mp4"
        self.write_log(f"[bold #ffbf69]Processing[/] {self.recorded_file.name}")
        self.write_log(f"Log: {process_log}")
        try:
            # Do not start a second pipeline for the same recording if a worker
            # survived an earlier UI/output-reader failure.
            code, processes = await command_output("pgrep", "-af", "process_short.sh")
            own_input = str(self.recorded_file)
            if code == 0 and own_input in processes:
                raise RuntimeError(
                    "This recording is already processing in the background. "
                    f"Wait for it to finish; log: {process_log}"
                )
            # A previous pipeline may have completed after its UI reader failed.
            # Reuse that valid result rather than running Whisper and FFmpeg again.
            if await self.valid_video(expected_final):
                self.final_file = expected_final
                self.query_one("#latest", Static).update(f"Ready: {expected_final.name}")
                self.write_log(f"[bold green]✓ Existing finished short recovered:[/] {expected_final}")
                return
            code = await self.stream_process(
                [str(SCRIPTS_DIR / "process_short.sh"), str(self.recorded_file)],
                log_path=process_log,
            )
            if code:
                raise RuntimeError("Processing failed; see the log above")
            final = expected_final
            if not await self.valid_video(final):
                raise RuntimeError("The final MP4 was not created or is invalid")
            self.final_file = final
            self.query_one("#latest", Static).update(f"Ready: {final.name}")
            self.write_log(f"[bold green]✓ Short ready:[/] {final}")
            self.notify(final.name, title="Short ready")
        except Exception as error:
            self.write_log(f"[bold red]Processing failed:[/] {error}")
            self.notify(str(error), title="Processing failed", severity="error")
        finally:
            self.restore_buttons()

    async def send_to_phone(self) -> None:
        if self.final_file is None:
            return
        self.set_busy("Sending to Pixel…")
        try:
            code = await self.stream_process([str(SCRIPTS_DIR / "to_phone.sh"), str(self.final_file)])
            if code:
                raise RuntimeError("Transfer failed; check the Pixel connection")
            self.write_log("[bold green]✓ Sent to Pixel[/]")
            self.notify(self.final_file.name, title="Sent to Pixel")
        except Exception as error:
            self.write_log(f"[bold red]Transfer failed:[/] {error}")
        finally:
            self.restore_buttons()

    @work(exclusive=True, group="operation")
    async def prepare_worker(self) -> None:
        await self.prepare_area()

    @work(exclusive=True, group="operation")
    async def clear_worker(self) -> None:
        await self.clear_area()

    @work(exclusive=True, group="operation")
    async def background_worker(self) -> None:
        await self.toggle_background()

    @work(exclusive=True, group="operation")
    async def phone_worker(self) -> None:
        await self.toggle_phone()

    @work(exclusive=True, group="operation")
    async def camera_worker(self) -> None:
        await self.toggle_camera()

    @work(exclusive=True, group="operation")
    async def record_worker(self) -> None:
        await (self.stop_recording() if self.recording else self.start_recording())

    @work(exclusive=True, group="operation")
    async def process_worker(self) -> None:
        await self.process_recording()

    @work(exclusive=True, group="operation")
    async def send_worker(self) -> None:
        await self.send_to_phone()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id in {"left", "center", "right"}:
            await self.clear_previews()
            self.position = button_id
            self.region = None
            self.update_position_buttons()
            self.restore_buttons()
        elif button_id == "prepare":
            self.prepare_worker()
        elif button_id == "clear":
            self.clear_worker()
        elif button_id == "background":
            self.background_worker()
        elif button_id == "phone":
            self.phone_worker()
        elif button_id == "camera":
            self.camera_worker()
        elif button_id == "record":
            self.record_worker()
        elif button_id == "process":
            self.process_worker()
        elif button_id == "send":
            self.send_worker()
        elif button_id == "open" and self.final_file:
            detached("mpv", str(self.final_file))

    def action_prepare(self) -> None:
        self.prepare_worker()

    def action_record(self) -> None:
        self.record_worker()

    def action_background(self) -> None:
        self.background_worker()

    def action_camera(self) -> None:
        self.camera_worker()

    def action_process(self) -> None:
        self.process_worker()

    async def action_quit(self) -> None:
        if self.recording:
            self.notify("Stop the recording before closing Short Studio", severity="warning")
            return
        await self.clear_previews()
        self.exit()


if __name__ == "__main__":
    ShortStudio().run()
