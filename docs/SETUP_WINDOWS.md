# Windows Setup

## One-command setup

From the extracted repository root, run PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

The script creates `.venv`, installs the package and development dependencies, installs Playwright Chromium, and copies `.env.example` to `.env` if needed. It does not install FFmpeg automatically because Windows installation methods vary; install FFmpeg and FFprobe and make both available on PATH.

## Manual setup

1. Install Python 3.11 or 3.12 and Git.
2. Install FFmpeg (including `ffprobe`) and add its `bin` folder to PATH.
3. From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
playwright install chromium
Copy-Item .env.example .env
```

4. Add `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` to `.env` after creating your own voice clone.
5. Run the checks:

```powershell
fnvideo doctor
pytest
ruff check .
ruff format --check .
fnvideo validate specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
fnvideo validate specs/fondasi-01-korelasi-bukan-kausalitas/long.yaml
fnvideo preview specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
```

Do not put `.env`, private voice recordings, or rendered audio/video into Git.
