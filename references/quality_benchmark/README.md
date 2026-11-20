# Reference Video Benchmark

The user's reference MP4 is required to verify the explicit goal: the new F/N video must outperform it. The reference video was not included in the available source files for this build.

Place the reference file here as `reference.mp4` (or supply it during a review session). Keep it out of Git if it is private; `.gitignore` excludes video files by default.

Compare reference and candidate on the same device, display size, volume, and playback conditions. Use `scorecard_template.csv` and the pass criteria in `docs/QUALITY_BAR.md`.

Until a side-by-side review is completed, status must remain `benchmark_pending`. Never claim the new video is better based only on renderer settings or an automated QA report.
