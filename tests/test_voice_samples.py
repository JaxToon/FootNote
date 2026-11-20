from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fnvideo.audio.voice_samples import inspect_voice_samples


def test_voice_sample_inspection_reports_recommended_duration(tmp_path: Path, monkeypatch) -> None:
    sample = tmp_path / "sample.mp3"
    sample.write_bytes(b"audio")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, json.dumps({"format": {"duration": "72.5"}}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    samples, errors, warnings = inspect_voice_samples([sample])
    assert not errors
    assert samples[0].duration_seconds == 72.5
    assert not warnings


def test_voice_sample_inspection_blocks_too_short_sample(tmp_path: Path, monkeypatch) -> None:
    sample = tmp_path / "tiny.mp3"
    sample.write_bytes(b"audio")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, json.dumps({"format": {"duration": "4.0"}}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    _, errors, _ = inspect_voice_samples([sample])
    assert any("at least 5 seconds" in item for item in errors)


def test_pvc_profile_does_not_apply_short_ivc_duration_warning(monkeypatch, tmp_path):
    sample = tmp_path / "long-session.wav"
    sample.write_bytes(b"fake")

    class Completed:
        stdout = '{"format": {"duration": "4200"}}'

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr("fnvideo.audio.voice_samples.subprocess.run", fake_run)
    samples, errors, warnings = inspect_voice_samples([sample], profile="pvc")

    assert len(samples) == 1
    assert not errors
    assert any("1–3 hour target" in warning for warning in warnings)
    assert not any("IVC" in warning for warning in warnings)


def test_pvc_profile_requires_at_least_30_minutes(monkeypatch, tmp_path):
    sample = tmp_path / "short-session.wav"
    sample.write_bytes(b"fake")

    class Completed:
        stdout = '{"format": {"duration": "900"}}'

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr("fnvideo.audio.voice_samples.subprocess.run", fake_run)
    _, errors, _ = inspect_voice_samples([sample], profile="pvc")

    assert any("at least 30 minutes for PVC" in error for error in errors)
