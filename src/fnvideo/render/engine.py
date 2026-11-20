from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright

from fnvideo.config import Settings
from fnvideo.models.episode import EpisodeSpec
from fnvideo.render.svg_scene import build_scene_html


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr[-4000:]}")


def _probe_media(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    video = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {
        "video_codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "frame_rate": video.get("r_frame_rate"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": audio.get("sample_rate"),
        "audio_channels": audio.get("channels"),
        "duration_seconds": float(payload.get("format", {}).get("duration", 0.0)),
    }


def _mouth_at(timing: dict[str, Any], frame_time: float, fps: int) -> str:
    idx = max(0, min(len(timing.get("mouth_shapes", [])) - 1, int(round(frame_time * fps))))
    shapes = timing.get("mouth_shapes", [])
    return shapes[idx] if shapes else "smile"


def _render_scene(
    page: Any,
    spec: EpisodeSpec,
    scene: Any,
    scene_timing: dict[str, Any],
    timing: dict[str, Any],
    out_path: Path,
    *,
    stills_dir: Path | None = None,
) -> None:
    width, height, fps = spec.meta.width, spec.meta.height, spec.meta.fps
    duration = float(scene_timing["duration_seconds"])
    frames = max(1, int(round(duration * fps)))
    html = build_scene_html(spec, scene, scene_timing, timing)
    page.set_viewport_size({"width": width, "height": height})
    page.set_content(html, wait_until="load")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-movflags",
        "+faststart",
        str(tmp),
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    try:
        print(f"[RENDER] {scene.id}: {frames} frames ({duration:.2f}s)", flush=True)
        for frame in range(frames):
            t = frame / fps
            mouth = _mouth_at(timing, float(scene_timing["start_seconds"]) + t, fps)
            page.evaluate("([t,m]) => window.render(t,m)", [t, mouth])
            image = page.screenshot(type="jpeg", quality=88)
            if proc.stdin is None:
                raise RuntimeError("FFmpeg stdin pipe unexpectedly unavailable")
            try:
                proc.stdin.write(image)
            except BrokenPipeError as exc:
                stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
                raise RuntimeError(
                    f"FFmpeg closed its frame input unexpectedly: {stderr[-3000:]}"
                ) from exc
            if stills_dir and frame in {0, frames // 2, max(0, frames - 1)}:
                stills_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(stills_dir / f"{scene.id}-{frame:06d}.png"), type="png")
        if proc.stdin:
            proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"FFmpeg scene render failed ({code}): {stderr[-3000:]}")
        tmp.replace(out_path)
    except Exception:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        tmp.unlink(missing_ok=True)
        raise


def make_contact_sheet(stills_dir: Path, output: Path, max_width: int = 1500) -> Path:
    images = [Image.open(p).convert("RGB") for p in sorted(stills_dir.glob("*.png"))]
    if not images:
        raise RuntimeError("No preview stills were rendered")
    thumb_w = 400
    thumbs = []
    for img in images:
        thumb_h = int(img.height * thumb_w / img.width)
        thumb = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        thumbs.append(ImageOps.expand(thumb, border=3, fill="#F3D65B"))
    cols = 3 if len(thumbs) >= 3 else len(thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    cell_w, cell_h = max(t.width for t in thumbs), max(t.height for t in thumbs)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#111D38")
    for i, thumb in enumerate(thumbs):
        x, y = (i % cols) * cell_w, (i // cols) * cell_h
        sheet.paste(thumb, (x, y))
    if sheet.width > max_width:
        new_h = int(sheet.height * max_width / sheet.width)
        sheet = sheet.resize((max_width, new_h), Image.Resampling.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)
    return output


def render_episode(
    spec: EpisodeSpec, output_dir: Path, settings: Settings, *, preview_only: bool = False
) -> dict[str, Any]:
    timing_path = output_dir / "timing.json"
    voice_path = output_dir / "voice.wav"
    if not timing_path.exists():
        raise FileNotFoundError(f"Missing {timing_path}. Run `fnvideo tts <spec>` first.")
    if not preview_only and not voice_path.exists():
        raise FileNotFoundError(f"Missing {voice_path}. Run `fnvideo tts <spec>` first.")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    scene_lookup = {x["id"]: x for x in timing["scenes"]}
    scenes_dir = output_dir / "scenes"
    stills_dir = output_dir / "stills"
    if stills_dir.exists():
        shutil.rmtree(stills_dir)
    stills_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []

    with sync_playwright() as p:
        launch_args: dict[str, Any] = {"headless": True}
        if settings.chromium_executable:
            launch_args["executable_path"] = settings.chromium_executable
        browser = p.chromium.launch(**launch_args)
        page = browser.new_page(
            viewport={"width": spec.meta.width, "height": spec.meta.height}, device_scale_factor=1
        )
        try:
            for scene in spec.scenes:
                scene_timing = scene_lookup[scene.id]
                path = scenes_dir / f"{scene.id}.mp4"
                if not preview_only:
                    _render_scene(
                        page, spec, scene, scene_timing, timing, path, stills_dir=stills_dir
                    )
                    rendered.append(path)
                else:
                    # Render representative stills at several points, without creating encoded scene files.
                    page.set_content(
                        build_scene_html(spec, scene, scene_timing, timing), wait_until="load"
                    )
                    duration = float(scene_timing["duration_seconds"])
                    for i, t in enumerate(
                        [
                            min(0.8, max(0.45, duration * 0.18)),
                            duration * 0.55,
                            max(0.8, duration - 0.55),
                        ]
                    ):
                        page.evaluate(
                            "([t,m])=>window.render(t,m)",
                            [
                                t,
                                _mouth_at(timing, scene_timing["start_seconds"] + t, spec.meta.fps),
                            ],
                        )
                        page.screenshot(path=str(stills_dir / f"{scene.id}-{i}.png"), type="png")
        finally:
            browser.close()

    contact = make_contact_sheet(stills_dir, output_dir / "contact.png")
    if preview_only:
        report = {
            "status": "preview_ready",
            "contact_sheet": str(contact),
            "scene_count": len(spec.scenes),
        }
        (output_dir / "preview_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report

    concat_list = output_dir / "scenes.concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in rendered), encoding="utf-8"
    )
    silent_video = output_dir / "visual.tmp.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(silent_video),
        ]
    )
    normalized_audio = output_dir / "voice.normalized.wav"
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(voice_path),
            "-af",
            f"loudnorm=I={settings.target_lufs}:TP={settings.true_peak_db}:LRA=11",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(normalized_audio),
        ]
    )
    final_tmp = output_dir / "final.tmp.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(silent_video),
            "-i",
            str(normalized_audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final_tmp),
        ]
    )
    final_path = output_dir / "final.mp4"
    final_tmp.replace(final_path)
    silent_video.unlink(missing_ok=True)
    media = _probe_media(final_path)
    checks = {
        "file_exists": final_path.exists(),
        "resolution_matches_profile": media.get("width") == spec.meta.width
        and media.get("height") == spec.meta.height,
        "fps_matches_profile": media.get("frame_rate") == f"{spec.meta.fps}/1",
        "h264_video": media.get("video_codec") == "h264",
        "aac_audio": media.get("audio_codec") == "aac",
        "human_visual_review_required": True,
        "voice_identity_review_required": True,
        "editorial_approval_required": True,
    }
    qa = {
        "status": "rendered_needs_human_qa",
        "episode_id": spec.meta.id,
        "format": spec.meta.format,
        "profile": {"width": spec.meta.width, "height": spec.meta.height, "fps": spec.meta.fps},
        "media_probe": media,
        "scene_count": len(rendered),
        "final_video": str(final_path),
        "contact_sheet": str(contact),
        "audio_target_lufs": settings.target_lufs,
        "audio_true_peak_target_db": settings.true_peak_db,
        "checks": checks,
        "technical_checks_passed": all(
            v
            for k, v in checks.items()
            if k
            not in {
                "human_visual_review_required",
                "voice_identity_review_required",
                "editorial_approval_required",
            }
        ),
    }
    (output_dir / "qa_report.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return qa
