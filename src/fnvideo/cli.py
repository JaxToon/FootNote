from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from fnvideo import __version__
from fnvideo.audio.elevenlabs import ElevenLabsClient
from fnvideo.audio.pipeline import generate_tts, preview_voice
from fnvideo.audio.timing import caption_timings
from fnvideo.audio.voice_samples import inspect_voice_samples
from fnvideo.config import load_settings
from fnvideo.models.episode import EpisodeSpec
from fnvideo.render.engine import render_episode
from fnvideo.services.doctor import run_doctor
from fnvideo.services.spec_loader import load_episode_spec


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fnvideo", description="F/N — FOOTNOTE video production pipeline"
    )
    parser.add_argument("--version", action="version", version=f"fnvideo {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check local render dependencies and voice configuration")
    validate = sub.add_parser("validate", help="Validate an episode YAML spec")
    validate.add_argument("spec", type=Path)
    plan = sub.add_parser("plan", help="Print normalized episode production plan")
    plan.add_argument("spec", type=Path)
    voice = sub.add_parser("voice", help="Voice clone utilities")
    voice_sub = voice.add_subparsers(dest="voice_command", required=True)
    check_samples = voice_sub.add_parser(
        "check-samples", help="Inspect voice samples locally before uploading"
    )
    check_samples.add_argument("--samples", nargs="+", required=True)
    check_samples.add_argument(
        "--profile",
        choices=["ivc", "pvc"],
        default="ivc",
        help="Use IVC (1–2 min) or PVC (30+ min, ideally 1–3 hours) recording targets",
    )
    clone = voice_sub.add_parser(
        "clone", help="Create an Instant Voice Clone from your own voice samples"
    )
    clone.add_argument("--name", required=True)
    clone.add_argument(
        "--samples", nargs="+", required=True, help="Audio files containing only your own voice"
    )
    clone.add_argument(
        "--i-own-this-voice",
        action="store_true",
        help="Explicitly confirm this is your voice or you have authorization",
    )
    vprev = voice_sub.add_parser("preview", help="Generate a short voice-clone preview")
    vprev.add_argument(
        "--text",
        default="Halo, ini adalah uji suara untuk F/N Footnote. Kita belajar memahami sesuatu lebih dalam, bukan sekadar menghafal istilah.",
    )
    vprev.add_argument("--output", type=Path, default=Path("out/voice/voice-preview.mp3"))
    vprev.add_argument(
        "--model",
        choices=["eleven_v4", "eleven_multilingual_v2"],
        default=None,
        help="Override the configured model for a same-voice A/B audition",
    )

    tts = sub.add_parser(
        "tts", help="Generate narration from your authorized ElevenLabs voice clone"
    )
    tts.add_argument("spec", type=Path)
    tts.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow test generation while editorial_status is not approved",
    )
    tts.add_argument(
        "--force",
        action="store_true",
        help="Regenerate every scene even when the local audio cache is valid",
    )
    preview = sub.add_parser(
        "preview", help="Render contact sheet without requiring generated audio"
    )
    preview.add_argument("spec", type=Path)
    render = sub.add_parser(
        "render", help="Render final MP4 from generated voice.wav and timing.json"
    )
    render.add_argument("spec", type=Path)
    render.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow a clearly marked test render from draft content",
    )
    build = sub.add_parser("build", help="Run TTS, preview, then final render")
    build.add_argument("spec", type=Path)
    build.add_argument(
        "--allow-draft", action="store_true", help="Allow testing before editorial approval"
    )
    build.add_argument(
        "--force-tts", action="store_true", help="Regenerate TTS even when the local cache is valid"
    )
    return parser


def _output_dir(spec: EpisodeSpec, settings_output: Path) -> Path:
    return settings_output / spec.meta.id.rsplit("-", 1)[0] / spec.meta.format


def _spec_or_exit(path: Path) -> EpisodeSpec:
    try:
        return load_episode_spec(path)
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _print_doctor() -> int:
    settings = load_settings()
    checks = run_doctor(settings.chromium_executable)
    for check in checks:
        status = "OK" if check.ok else "MISSING"
        print(f"[{status}] {check.name}: {check.detail}")
    print(
        f"[{'OK' if settings.elevenlabs_api_key else 'SETUP'}] ElevenLabs API key: {'configured' if settings.elevenlabs_api_key else 'ELEVENLABS_API_KEY not set'}"
    )
    print(
        f"[{'OK' if settings.elevenlabs_voice_id else 'SETUP'}] Voice clone ID: {'configured' if settings.elevenlabs_voice_id else 'ELEVENLABS_VOICE_ID not set'}"
    )
    return 0 if all(c.ok for c in checks) else 1


def _write_estimated_preview_timing(spec: EpisodeSpec, out: Path) -> None:
    cursor = 0.0
    scenes = []
    for index, scene in enumerate(spec.scenes):
        duration = float(scene.duration_hint_seconds or max(4.0, len(scene.narration) / 13.0))
        caps = caption_timings(scene, duration, None)
        scenes.append(
            {
                "id": scene.id,
                "title": scene.title,
                "speech_duration_seconds": duration,
                "duration_seconds": duration + (0.35 if index < len(spec.scenes) - 1 else 0.25),
                "start_seconds": cursor,
                "end_seconds": cursor + duration + (0.35 if index < len(spec.scenes) - 1 else 0.25),
                "captions": caps,
            }
        )
        cursor = scenes[-1]["end_seconds"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "timing.json").write_text(
        json.dumps(
            {
                "episode_id": spec.meta.id,
                "fps": spec.meta.fps,
                "scene_duration_seconds": cursor,
                "scenes": scenes,
                "rms_envelope": [],
                "mouth_shapes": [],
                "preview_timing_only": True,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    args = _parser().parse_args()
    settings = load_settings()
    if args.command == "doctor":
        raise SystemExit(_print_doctor())

    if args.command == "voice":
        if args.voice_command == "check-samples":
            sample_paths: list[Path] = []
            for pattern in args.samples:
                matches = [Path(p) for p in glob.glob(pattern)] or [Path(pattern)]
                sample_paths.extend(matches)
            samples, errors, warnings = inspect_voice_samples(sample_paths, profile=args.profile)
            print(f"Voice sample report ({args.profile.upper()}):")
            for sample in samples:
                print(
                    f"  OK  {sample.path} — {sample.duration_seconds:.1f}s ({sample.size_bytes:,} bytes)"
                )
            print(f"Total duration: {sum(x.duration_seconds for x in samples):.1f}s")
            for warning in warnings:
                print(f"WARN: {warning}")
            for error in errors:
                print(f"ERROR: {error}")
            if not errors:
                print(f"PASS: sample files meet the local {args.profile.upper()} duration checks.")
            raise SystemExit(1 if errors else 0)
        if args.voice_command == "clone":
            if not args.i_own_this_voice:
                raise SystemExit(
                    "Safety check: use --i-own-this-voice only when the samples are your own voice or you have explicit authorization."
                )
            if not settings.elevenlabs_api_key:
                raise SystemExit("Set ELEVENLABS_API_KEY in .env first.")
            sample_paths: list[Path] = []
            for pattern in args.samples:
                matches = [Path(p) for p in glob.glob(pattern)] or [Path(pattern)]
                sample_paths.extend(matches)
            sample_paths = [p for p in sample_paths if p.is_file()]
            if not sample_paths:
                raise SystemExit("No voice sample files found. Check the --samples path(s).")
            samples, errors, warnings = inspect_voice_samples(sample_paths)
            for warning in warnings:
                print(f"WARN: {warning}")
            if errors:
                raise SystemExit("Voice samples failed local validation:\n- " + "\n- ".join(errors))
            print(
                f"Validated {len(samples)} voice sample(s), total {sum(x.duration_seconds for x in samples):.1f}s."
            )
            client = ElevenLabsClient(settings.elevenlabs_api_key)
            clone_result = client.clone_instant_voice(name=args.name, sample_paths=sample_paths)
            print(f"Created Instant Voice Clone: {clone_result.voice_id}")
            if clone_result.requires_verification:
                print(
                    "ACTION REQUIRED: ElevenLabs reports that this voice requires verification before use. Complete the verification in your account first."
                )
            else:
                print(
                    "Provider response: this IVC does not currently require an additional verification step."
                )
            print(
                "Add this line to .env after confirming the clone is usable: ELEVENLABS_VOICE_ID="
                + clone_result.voice_id
            )
            return
        if args.voice_command == "preview":
            path = preview_voice(settings, args.text, args.output, model_id=args.model)
            print(f"Voice preview written: {path}")
            return

    if args.command in {"validate", "plan", "tts", "preview", "render", "build"}:
        spec = _spec_or_exit(args.spec)
        if args.command == "validate":
            print(f"VALID: {spec.meta.id} — {spec.meta.title}")
            print(
                f"Format: {spec.meta.format} | {spec.meta.width}x{spec.meta.height} @ {spec.meta.fps}fps"
            )
            print(f"Scenes: {len(spec.scenes)} | Editorial status: {spec.editorial_status}")
            return
        if args.command == "plan":
            print(
                json.dumps(
                    {
                        "episode_id": spec.meta.id,
                        "title": spec.meta.title,
                        "format": spec.meta.format,
                        "resolution": f"{spec.meta.width}x{spec.meta.height}",
                        "fps": spec.meta.fps,
                        "scene_count": len(spec.scenes),
                        "estimated_hint_seconds": sum(
                            s.duration_hint_seconds or 0 for s in spec.scenes
                        ),
                        "editorial_status": spec.editorial_status,
                        "next_gate": "Human editorial approval before production TTS/render",
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        out = _output_dir(spec, settings.output_root)
        if args.command == "tts":
            print(generate_tts(spec, out, settings, allow_draft=args.allow_draft, force=args.force))
            return
        if args.command == "preview":
            if not (out / "timing.json").exists():
                _write_estimated_preview_timing(spec, out)
            print(
                json.dumps(
                    render_episode(spec, out, settings, preview_only=True),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        if args.command == "render":
            if spec.editorial_status != "approved" and not args.allow_draft:
                raise SystemExit(
                    "Editorial status is not approved. Review the script and set editorial_status: approved, or use --allow-draft for testing."
                )
            print(json.dumps(render_episode(spec, out, settings), indent=2, ensure_ascii=False))
            return
        if args.command == "build":
            generate_tts(spec, out, settings, allow_draft=args.allow_draft, force=args.force_tts)
            print(
                json.dumps(
                    render_episode(spec, out, settings, preview_only=True),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            print(json.dumps(render_episode(spec, out, settings), indent=2, ensure_ascii=False))
            return


if __name__ == "__main__":
    main()
