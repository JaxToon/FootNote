from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps
from playwright.sync_api import sync_playwright

from fnvideo.audio.timing import scene_frame_range
from fnvideo.config import Settings
from fnvideo.models.episode import EpisodeSpec
from fnvideo.render.svg_scene import build_scene_html

HUMAN_REVIEW_KEYS = (
    "human_visual_review_required",
    "voice_identity_review_required",
    "editorial_approval_required",
)


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr[-4000:]}")


def tmp_path_for(path: Path) -> Path:
    """Temporary sibling with the same extension, so FFmpeg still infers the container."""
    return path.with_name(f"{path.stem}.tmp{path.suffix}")


def run_ffmpeg_atomic(args: list[str], output: Path) -> Path:
    """Run `ffmpeg <args> <tmp>` and move tmp onto *output* only on success.

    A failed or interrupted run never leaves a truncated file at *output*; a previous good
    file there is preserved.
    """
    tmp = tmp_path_for(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run(["ffmpeg", "-y", "-loglevel", "error", *args, str(tmp)])
        if not tmp.is_file() or tmp.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg reported success but produced no output for {output}")
        tmp.replace(output)
    finally:
        tmp.unlink(missing_ok=True)
    return output


def write_silent_wav(path: Path, seconds: float, sample_rate: int = 44100) -> Path:
    """Write a stereo 16-bit silent WAV (placeholder audio for draft/silent renders)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(round(seconds * sample_rate))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00\x00\x00" * frames)
    return path


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
        "frame_count": int(video["nb_frames"])
        if str(video.get("nb_frames", "")).isdigit()
        else None,
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": audio.get("sample_rate"),
        "audio_channels": audio.get("channels"),
        "duration_seconds": float(payload.get("format", {}).get("duration", 0.0)),
    }


def _mouth_at_frame(timing: dict[str, Any], frame: int) -> str:
    shapes = timing.get("mouth_shapes", [])
    if not shapes:
        return "smile"
    return shapes[max(0, min(len(shapes) - 1, frame))]


_PAGE_ERRORS: dict[int, list[str]] = {}


def page_errors(page: Any) -> list[str]:
    return _PAGE_ERRORS.setdefault(id(page), [])


def load_scene_page(page: Any, html: str) -> None:
    """Load scene HTML and fail loudly if its script threw (e.g. a broken render())."""
    errors = page_errors(page)
    errors.clear()
    page.set_content(html, wait_until="load")
    if errors:
        raise RuntimeError(f"Scene page script error: {errors[0]}")
    if not page.evaluate("() => typeof window.render === 'function'"):
        raise RuntimeError("Scene page did not define window.render")


def still_times(duration: float) -> list[float]:
    """Representative scene-relative still times: early, middle, late."""
    return [min(0.8, max(0.45, duration * 0.18)), duration * 0.55, max(0.8, duration - 0.55)]


def _still_name(order: int, scene_id: str, k: int) -> str:
    # Zero-padded scene order first so a plain sort is scene order, not alphabetical by id.
    return f"{order:02d}-{scene_id}-{k}.png"


def _render_scene(
    page: Any,
    spec: EpisodeSpec,
    order: int,
    scene: Any,
    scene_timing: dict[str, Any],
    timing: dict[str, Any],
    out_path: Path,
    stills_dir: Path,
) -> list[tuple[Path, str]]:
    fps = spec.meta.fps
    first, last = scene_frame_range(
        float(scene_timing["start_seconds"]), float(scene_timing["end_seconds"]), fps
    )
    frames = last - first
    still_frames = {
        min(frames - 1, int(round(t * fps))): k
        for k, t in enumerate(still_times(float(scene_timing["duration_seconds"])))
    }
    load_scene_page(page, build_scene_html(spec, scene, scene_timing, timing))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(out_path)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-vcodec", "mjpeg",
        "-framerate", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", str(tmp),
    ]  # fmt: skip
    stills: list[tuple[Path, str]] = []
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    try:
        print(f"[RENDER] {scene.id}: {frames} frames ({frames / fps:.2f}s)", flush=True)
        for local in range(frames):
            t = local / fps
            page.evaluate(
                "([t,m]) => window.render(t,m)", [t, _mouth_at_frame(timing, first + local)]
            )
            image = page.screenshot(type="jpeg", quality=90)
            if proc.stdin is None:
                raise RuntimeError("FFmpeg stdin pipe unexpectedly unavailable")
            try:
                proc.stdin.write(image)
            except BrokenPipeError as exc:
                err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
                raise RuntimeError(
                    f"FFmpeg closed its frame input unexpectedly: {err[-3000:]}"
                ) from exc
            if local in still_frames:
                still = stills_dir / _still_name(order, scene.id, still_frames[local])
                page.screenshot(path=str(still), type="png")
                stills.append((still, f"{scene.id}  t={t:.2f}s"))
        if proc.stdin:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"FFmpeg scene render failed ({code}): {err[-3000:]}")
        tmp.replace(out_path)
    except BaseException:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        tmp.unlink(missing_ok=True)
        raise
    return stills


def make_contact_sheet(
    stills: list[tuple[Path, str]] | Path, output: Path, max_width: int = 1500
) -> Path:
    """Grid of stills in the given order (one row per scene), each labelled."""
    if isinstance(stills, Path):
        stills = [(p, p.stem) for p in sorted(stills.glob("*.png"))]
    if not stills:
        raise RuntimeError("No preview stills were rendered")
    thumb_w = 400
    thumbs = []
    for path, label in stills:
        img = Image.open(path).convert("RGB")
        thumb = img.resize(
            (thumb_w, int(img.height * thumb_w / img.width)), Image.Resampling.LANCZOS
        )
        draw = ImageDraw.Draw(thumb)
        draw.rectangle((0, thumb.height - 22, thumb_w, thumb.height), fill="#000000")
        draw.text((6, thumb.height - 18), label, fill="#F3D65B")
        thumbs.append(ImageOps.expand(thumb, border=3, fill="#F3D65B"))
    cols = min(3, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    cell_w, cell_h = max(t.width for t in thumbs), max(t.height for t in thumbs)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#111D38")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * cell_w, (i // cols) * cell_h))
    if sheet.width > max_width:
        sheet = sheet.resize(
            (max_width, int(sheet.height * max_width / sheet.width)), Image.Resampling.LANCZOS
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)
    return output


def build_qa_report(
    spec: EpisodeSpec,
    timing: dict[str, Any],
    media: dict[str, Any],
    settings: Settings,
    *,
    final_path: Path,
    contact: Path,
    scene_count: int,
    silent_audio: bool,
) -> dict[str, Any]:
    fps = spec.meta.fps
    expected_seconds = float(timing["scenes"][-1]["end_seconds"]) if timing["scenes"] else 0.0
    expected_frames = int(round(expected_seconds * fps))
    tolerance = 1.0 / fps + 0.05
    caption_quality: dict[str, int] = {}
    for scene in timing["scenes"]:
        for cap in scene.get("captions", []):
            key = cap.get("timing_quality", "unknown")
            caption_quality[key] = caption_quality.get(key, 0) + 1
    checks: dict[str, bool] = {
        "file_exists": final_path.exists(),
        "resolution_matches_profile": media.get("width") == spec.meta.width
        and media.get("height") == spec.meta.height,
        "fps_matches_profile": media.get("frame_rate") == f"{fps}/1",
        "h264_video": media.get("video_codec") == "h264",
        "aac_audio": media.get("audio_codec") == "aac",
        "duration_matches_timing": abs(float(media.get("duration_seconds") or 0) - expected_seconds)
        <= tolerance,
    }
    if media.get("frame_count") is not None:
        checks["frame_count_matches_timing"] = abs(media["frame_count"] - expected_frames) <= 1
    checks.update(dict.fromkeys(HUMAN_REVIEW_KEYS, True))
    technical = all(v for k, v in checks.items() if k not in HUMAN_REVIEW_KEYS)
    draft = spec.editorial_status != "approved" or silent_audio or timing.get("preview_timing_only")
    return {
        "status": "draft_test_render" if draft else "rendered_needs_human_qa",
        "publish_ready": False,
        "episode_id": spec.meta.id,
        "format": spec.meta.format,
        "editorial_status": spec.editorial_status,
        "profile": {"width": spec.meta.width, "height": spec.meta.height, "fps": fps},
        "audio_source": "silent_placeholder" if silent_audio else "voice",
        "timing_source": timing.get("timing_source", "unknown"),
        "caption_timing_quality": caption_quality,
        "expected_duration_seconds": round(expected_seconds, 3),
        "expected_frame_count": expected_frames,
        "media_probe": media,
        "scene_count": scene_count,
        "final_video": str(final_path),
        "contact_sheet": str(contact),
        "audio_target_lufs": settings.target_lufs,
        "audio_true_peak_target_db": settings.true_peak_db,
        "checks": checks,
        "technical_checks_passed": technical,
    }


def render_episode(
    spec: EpisodeSpec,
    output_dir: Path,
    settings: Settings,
    *,
    preview_only: bool = False,
    silent: bool = False,
) -> dict[str, Any]:
    timing_path = output_dir / "timing.json"
    voice_path = output_dir / "voice.wav"
    if not timing_path.exists():
        raise FileNotFoundError(f"Missing {timing_path}. Run `fnvideo tts <spec>` first.")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    if silent and not preview_only:
        voice_path = write_silent_wav(
            output_dir / "silent.wav", float(timing["scenes"][-1]["end_seconds"])
        )
    elif not preview_only and not voice_path.exists():
        raise FileNotFoundError(f"Missing {voice_path}. Run `fnvideo tts <spec>` first.")
    scene_lookup = {x["id"]: x for x in timing["scenes"]}
    scenes_dir = output_dir / "scenes"
    stills_dir = output_dir / "stills"
    if stills_dir.exists():
        shutil.rmtree(stills_dir)
    stills_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    stills: list[tuple[Path, str]] = []

    with sync_playwright() as p:
        launch_args: dict[str, Any] = {"headless": True}
        if settings.chromium_executable:
            launch_args["executable_path"] = settings.chromium_executable
        browser = p.chromium.launch(**launch_args)
        page = browser.new_page(
            viewport={"width": spec.meta.width, "height": spec.meta.height},
            device_scale_factor=1,
        )
        page.on("pageerror", lambda exc: page_errors(page).append(str(exc)))
        try:
            for order, scene in enumerate(spec.scenes):
                scene_timing = scene_lookup[scene.id]
                if not preview_only:
                    path = scenes_dir / f"{scene.id}.mp4"
                    stills += _render_scene(
                        page, spec, order, scene, scene_timing, timing, path, stills_dir
                    )
                    rendered.append(path)
                    continue
                load_scene_page(page, build_scene_html(spec, scene, scene_timing, timing))
                first, _ = scene_frame_range(
                    float(scene_timing["start_seconds"]),
                    float(scene_timing["end_seconds"]),
                    spec.meta.fps,
                )
                for k, t in enumerate(still_times(float(scene_timing["duration_seconds"]))):
                    frame = first + int(round(t * spec.meta.fps))
                    page.evaluate(
                        "([t,m])=>window.render(t,m)", [t, _mouth_at_frame(timing, frame)]
                    )
                    still = stills_dir / _still_name(order, scene.id, k)
                    page.screenshot(path=str(still), type="png")
                    stills.append((still, f"{scene.id}  t={t:.2f}s"))
        finally:
            browser.close()

    contact = make_contact_sheet(stills, output_dir / "contact.png")
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
    silent_video = run_ffmpeg_atomic(
        ["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy"],
        output_dir / "visual.mp4",
    )
    if silent:
        mix_audio = voice_path  # loudness normalisation of digital silence is meaningless
    else:
        mix_audio = run_ffmpeg_atomic(
            ["-i", str(voice_path), "-af",
             f"loudnorm=I={settings.target_lufs}:TP={settings.true_peak_db}:LRA=11",
             "-ar", "44100", "-ac", "2"],
            output_dir / "voice.normalized.wav",
        )  # fmt: skip
    final_path = run_ffmpeg_atomic(
        ["-i", str(silent_video), "-i", str(mix_audio), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
         "-movflags", "+faststart"],
        output_dir / ("final.silent-draft.mp4" if silent else "final.mp4"),
    )  # fmt: skip
    silent_video.unlink(missing_ok=True)
    qa = build_qa_report(
        spec,
        timing,
        _probe_media(final_path),
        settings,
        final_path=final_path,
        contact=contact,
        scene_count=len(rendered),
        silent_audio=silent,
    )
    (output_dir / "qa_report.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return qa
