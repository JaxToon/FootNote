from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def run_doctor(chromium_executable: str | None = None) -> list[Check]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    browser_path = chromium_executable
    if not browser_path:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser_path = playwright.chromium.executable_path
        except Exception:
            browser_path = None
    browser_ok = bool(browser_path and Path(browser_path).is_file())
    return [
        Check("Python >=3.11", sys.version_info >= (3, 11), sys.version.split()[0]),
        Check("FFmpeg", ffmpeg is not None, ffmpeg or "not found on PATH"),
        Check("FFprobe", ffprobe is not None, ffprobe or "not found on PATH"),
        Check(
            "Playwright package",
            importlib.util.find_spec("playwright") is not None,
            "installed" if importlib.util.find_spec("playwright") else "pip install playwright",
        ),
        Check(
            "Playwright Chromium",
            browser_ok,
            str(browser_path)
            if browser_ok
            else "run `playwright install chromium` or set PLAYWRIGHT_CHROMIUM_EXECUTABLE",
        ),
        Check(
            "Pillow",
            importlib.util.find_spec("PIL") is not None,
            "installed" if importlib.util.find_spec("PIL") else "pip install Pillow",
        ),
        Check(
            "NumPy",
            importlib.util.find_spec("numpy") is not None,
            "installed" if importlib.util.find_spec("numpy") else "pip install numpy",
        ),
    ]
