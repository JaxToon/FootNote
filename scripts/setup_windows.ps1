$ErrorActionPreference = "Stop"

Write-Host "[F/N] Setting up the local video pipeline..." -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ first."
}

$pythonVersion = & py -3.11 --version 2>$null
if (-not $pythonVersion) {
    throw "Python 3.11 was not found. Install Python 3.11, then rerun this script."
}

if (-not (Test-Path ".venv")) {
    & py -3.11 -m venv .venv
}

$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e ".[dev]"
& $venvPython -m playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Add your ElevenLabs credentials after voice cloning." -ForegroundColor Yellow
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffmpeg -or -not $ffprobe) {
    Write-Warning "FFmpeg/FFprobe not found on PATH. Install FFmpeg before rendering."
} else {
    Write-Host "FFmpeg and FFprobe found." -ForegroundColor Green
}

Write-Host "Setup completed. Activate with: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "Then run: fnvideo doctor; pytest; fnvideo preview specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml"
