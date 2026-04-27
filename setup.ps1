# ============================================================
#  The Earful Tower — One-time setup
#  Run this once after extracting the zip.
#  Right-click → "Run with PowerShell"
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step  { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  ✔  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  ⚠  $msg" -ForegroundColor Yellow }
function Write-Fatal { param($msg) Write-Host "  ✖  $msg" -ForegroundColor Red; Read-Host "`nPress Enter to exit"; exit 1 }

Clear-Host
Write-Host ""
Write-Host "  🗼  The Earful Tower — Setup" -ForegroundColor White
Write-Host "  ─────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Before this script runs, please note:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  This script will download and install approximately 5.8 GB:" -ForegroundColor White
Write-Host "    • PyTorch + dependencies  ~2.5 GB  (installed now)" -ForegroundColor Gray
Write-Host "    • Whisper large-v3 model  ~3.0 GB  (downloaded on first launch)" -ForegroundColor Gray
Write-Host "    • pyannote models          ~300 MB  (downloaded on first launch)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Total disk space required: ~8.5 GB" -ForegroundColor White
Write-Host "  Estimated setup time:      5–20 minutes" -ForegroundColor White
Write-Host "  Internet connection:       required for setup + first launch only" -ForegroundColor White
Write-Host ""
$confirm = Read-Host "  Continue? (Y/N)"
if ($confirm -notmatch "^[Yy]") { Write-Host "  Cancelled."; exit 0 }
Write-Host ""

# ── 1. Find Python 3.11 ──────────────────────────────────────────────────────
Write-Step "Looking for Python 3.11..."
$pythonExe = $null
foreach ($candidate in @("py -3.11", "python3.11", "python3", "python")) {
    try {
        $parts = $candidate -split " ", 2
        $args  = if ($parts.Count -gt 1) { $parts[1..99] + "--version" } else { @("--version") }
        $ver   = & $parts[0] @args 2>&1
        if ($ver -match "3\.11") { $pythonExe = $candidate; break }
    } catch {}
}
if (-not $pythonExe) {
    Write-Fatal "Python 3.11 not found. Install it from https://www.python.org/downloads/ then re-run setup."
}
Write-Ok "Found: $pythonExe"

# ── 2. Create virtual environment ────────────────────────────────────────────
$venvDir    = Join-Path $ProjectDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip    = Join-Path $venvDir "Scripts\pip.exe"

if (Test-Path $venvPython) {
    Write-Ok "Virtual environment already exists — skipping creation"
} else {
    Write-Step "Creating virtual environment..."
    $parts = $pythonExe -split " ", 2
    $args  = if ($parts.Count -gt 1) { $parts[1..99] + @("-m", "venv", $venvDir) } else { @("-m", "venv", $venvDir) }
    & $parts[0] @args
    Write-Ok "Virtual environment created"
}

# ── 3. Install PyTorch (CUDA 12.1) ───────────────────────────────────────────
Write-Host ""
Write-Step "Installing PyTorch with CUDA 12.1 support (~2.5 GB download, one-time)..."
Write-Warn "This step can take 5–15 minutes depending on your connection. Please wait."
Write-Host ""
& $venvPip install torch==2.4.1 torchaudio==2.4.1 `
    --index-url https://download.pytorch.org/whl/cu121 `
    --quiet --no-warn-script-location
Write-Ok "PyTorch installed"

# ── 4. Install remaining dependencies ────────────────────────────────────────
Write-Step "Installing remaining dependencies..."
& $venvPip install -r (Join-Path $ProjectDir "src\requirements.txt") `
    --quiet --no-warn-script-location
Write-Ok "Dependencies installed"

# ── 5. HuggingFace token ─────────────────────────────────────────────────────
$connDir  = Join-Path $ProjectDir "connectors"
$connFile = Join-Path $connDir "huggingface-read.md"
New-Item -ItemType Directory -Force -Path $connDir | Out-Null

if (Test-Path $connFile) {
    Write-Ok "HuggingFace token file already exists — skipping"
} else {
    Write-Host ""
    Write-Host "  ─── HuggingFace Token ───────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  The app uses pyannote for speaker detection." -ForegroundColor White
    Write-Host "  A free HuggingFace account + read token is required (one-time)." -ForegroundColor White
    Write-Host ""
    Write-Host "  Step 1 — Get a free token:" -ForegroundColor Yellow
    Write-Host "           https://huggingface.co → Settings → Access Tokens → New token (Read)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Step 2 — Accept model terms (while signed in):" -ForegroundColor Yellow
    Write-Host "           https://huggingface.co/pyannote/speaker-diarization-3.1" -ForegroundColor Gray
    Write-Host "           https://huggingface.co/pyannote/segmentation-3.0" -ForegroundColor Gray
    Write-Host ""

    $token = Read-Host "  Paste your token here (hf_...)"
    $token = $token.Trim()

    $connContent = @"
# Connector: HuggingFace (read)

Read-only token for downloading pyannote diarization models.

## Credential

``````
$token
``````

## Renewal

1. huggingface.co → Settings → Access Tokens
2. Replace the value above
3. Re-accept model terms if pyannote releases a new major version:
   - huggingface.co/pyannote/speaker-diarization-3.1
   - huggingface.co/pyannote/segmentation-3.0
"@
    $connContent | Set-Content $connFile -Encoding utf8

    if ($token -match "^hf_") {
        Write-Ok "Token saved to connectors\huggingface-read.md"
    } else {
        Write-Warn "Token format looks unusual. Edit connectors\huggingface-read.md if the app fails to connect."
    }
}

# ── 6. Desktop shortcut ───────────────────────────────────────────────────────
Write-Step "Creating desktop shortcut..."
$desktop      = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "The Earful Tower.lnk"
$shell        = New-Object -ComObject WScript.Shell
$sc           = $shell.CreateShortcut($shortcutPath)
$sc.TargetPath       = $venvPython
$sc.Arguments        = "src\app.py"
$sc.WorkingDirectory = $ProjectDir
$sc.IconLocation     = Join-Path $ProjectDir "icon.ico"
$sc.Description      = "The Earful Tower — Local audio transcription"
$sc.Save()
Write-Ok "Shortcut created on your desktop"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ─────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  ✅  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  On first launch the app will download the AI models (~1 GB)." -ForegroundColor White
Write-Host "  After that, everything runs 100% offline." -ForegroundColor White
Write-Host ""
Write-Host "  Launch: double-click 'The Earful Tower' on your desktop." -ForegroundColor Cyan
Write-Host ""
Read-Host "  Press Enter to close"
