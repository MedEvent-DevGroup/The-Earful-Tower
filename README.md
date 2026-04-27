# 🗼 The Earful Tower

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Whisper large-v3](https://img.shields.io/badge/Whisper-large--v3-green.svg)](https://github.com/openai/whisper)
[![pyannote 3.1](https://img.shields.io/badge/pyannote-3.1-green.svg)](https://github.com/pyannote/pyannote-audio)

Local audio transcription with speaker diarization. Runs entirely on your machine — no cloud, no uploads, no data shared.

## What it does

- Converts any audio file to a clean transcript with speaker labels
- Detects and separates speakers automatically using **pyannote.audio 3.1**
- Transcribes in **Canadian French** or **English** using **Whisper large-v3**
- Outputs: timestamped `.txt`, `.md`, `.srt`, or a waveform `.mkv` video with embedded subtitles
- GPU-accelerated on CUDA; falls back to CPU automatically
- Multilingual UI — currently English and French Canadian (add your language by dropping a JSON file in `src/locales/`)

## Platform

**Windows 10/11 only.** The setup script is PowerShell and the GUI uses Windows-specific features. macOS and Linux are not currently supported.

---

## ⚠️ Before you download — size and time expectations

This app is powerful but heavy. Please read before starting:

| Step | What happens | Download | Disk space | Time (estimate) |
|---|---|---|---|---|
| `setup.ps1` | Installs Python packages incl. PyTorch CUDA | ~2.5 GB | ~5 GB | 5–20 min |
| First launch | Downloads Whisper large-v3 + pyannote models | ~3.3 GB | ~3.3 GB | 5–15 min |
| **Total** | | **~5.8 GB** | **~8.5 GB** | **~30 min** |

After the first launch everything is cached locally. All subsequent runs are **fully offline** and start in seconds.

**GPU strongly recommended.** An NVIDIA GPU (CUDA 12.1) is required for reasonable speed:

| Hardware | 90-minute audio |
|---|---|
| RTX 4090 | ~20–35 min |
| RTX 3060 / 3070 | ~45–75 min |
| CPU only | 3–6 hours |

---

## 📥 Installation guide (end users)

Follow these steps in order. The whole process takes about 30 minutes.

### Step 1 — Install Python 3.11

> ⚠️ **Python 3.11 specifically.** Newer versions (3.12, 3.13) are not compatible with all dependencies.

**Option A — Windows Package Manager (recommended):**
```
winget install Python.Python.3.11
```
Open a new PowerShell window after this completes.

**Option B — Manual:**
1. Go to [python.org/downloads/release/python-3119](https://www.python.org/downloads/release/python-3119/)
2. Download `Windows installer (64-bit)`
3. Run the installer — **check "Add Python to PATH"** before clicking Install

Verify it worked:
```
py -3.11 --version
```
You should see `Python 3.11.x`.

---

### Step 2 — Install ffmpeg

ffmpeg converts your audio files before processing.

**Option A — Windows Package Manager (recommended):**
```
winget install Gyan.FFmpeg
```
Open a new PowerShell window after this completes.

**Option B — Manual:**
1. Go to [ffmpeg.org/download.html](https://ffmpeg.org/download.html) → Windows builds
2. Download the latest release zip
3. Extract it and copy the `ffmpeg.exe` file (from the `bin/` folder) to `C:\Windows\System32\`

Verify it worked:
```
ffmpeg -version
```

---

### Step 3 — Create a free HuggingFace account and get a token

The app uses pyannote for speaker detection. pyannote's model weights are hosted on HuggingFace and require a free account to download (one-time only — after first launch the models are cached locally).

1. **Create a free account** at [huggingface.co/join](https://huggingface.co/join)

2. **Get a read token:**
   - Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Click **New token** → Name it anything → Role: **Read** → Create
   - Copy the token (starts with `hf_...`) — you'll paste it during setup

3. **Accept the model terms** (must be signed in — click both links):
   - [huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) → click **Agree and access repository**
   - [huggingface.co/pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) → click **Agree and access repository**

> You only do this once. After the models are downloaded your token is no longer used and the app runs 100% offline.

---

### Step 4 — Download The Earful Tower

1. Go to the [**latest release**](https://github.com/MedEvent-DevGroup/The-Earful-Tower/releases/latest)
2. Under **Assets**, download **`The-Earful-Tower-v*.*.*.zip`**
3. **Extract to a permanent folder** — for example `C:\Apps\EarfulTower\` or `C:\Users\YourName\EarfulTower\`

> ⚠️ **Do not run from Downloads or from inside a zip.** The app needs to stay in a fixed location because the desktop shortcut is created pointing to that path.

---

### Step 5 — Run setup

1. Open the extracted folder
2. **Right-click `setup.ps1`** → **"Run with PowerShell"**
3. The script will:
   - Ask you to confirm the ~5.8 GB download (press **Y**)
   - Download and install PyTorch with CUDA support (~2.5 GB, 5–15 min)
   - Install the remaining Python packages
   - Ask you to paste your HuggingFace token (from Step 3)
   - Create a **"The Earful Tower"** shortcut on your desktop

> **Script blocked?** If Windows shows "cannot be loaded because running scripts is disabled":
> 1. Open PowerShell **as Administrator**
> 2. Run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
> 3. Press **Y** to confirm
> 4. Try right-clicking `setup.ps1` again

---

### Step 6 — First launch

Double-click **"The Earful Tower"** on your desktop.

On the very first launch the app will download the AI models:
- Whisper large-v3 (~3.0 GB)
- pyannote speaker models (~300 MB)

This takes 5–15 minutes depending on your internet connection. A progress bar is shown. **Do not close the app during this step.**

After the models are downloaded, every future launch is instant and fully offline.

---

## 🎙️ How to use the app

1. **Audio file** — click Browse and select your audio file (`.m4a`, `.mp3`, `.wav`, `.mp4`, etc.)
2. **Language** — choose English or French Canadian
3. **Number of speakers** — use `−`/`+` to set how many people are in the recording
4. **Speaker names** *(optional)* — enter names separated by commas, most-talkative first (e.g. `Alice, Bob, Charlie`)
5. **Output formats** — check the formats you want:
   - **Text (.txt)** — plain transcript, optionally with timestamps
   - **Markdown (.md)** — same, formatted for Markdown viewers
   - **Subtitles (.srt)** — subtitle file, importable into video editors
   - **Video (.mkv)** — waveform video with subtitles embedded
   - **Data (.json)** — full structured output with all timing data
6. **Output folder** *(optional)* — defaults to the same folder as your audio file
7. Click **Start** and wait — progress is shown in the log at the bottom

The transcript files appear in the output folder when done.

---

## Privacy

All processing happens locally on your machine.

- **Audio data**: never transmitted anywhere — not during setup, not during transcription
- **Model downloads**: on first launch, pyannote model weights (~300 MB) are fetched from HuggingFace. Their servers log your IP address and token for that one request. No audio is involved. All subsequent runs are fully offline.
- **Your HuggingFace token**: stored in `connectors/huggingface-read.md` on your local machine only. It is never sent anywhere except to HuggingFace to authorize the one-time model download.

---

## Requirements

- Windows 10/11
- Python 3.11 — [download here](https://www.python.org/downloads/release/python-3119/)
- NVIDIA GPU with CUDA 12.1 drivers (CPU works but see speed table above)
- [ffmpeg](https://ffmpeg.org/download.html) on your system PATH
- ~9 GB free disk space
- A free [HuggingFace](https://huggingface.co) account (for model downloads — one-time only)

---

## CLI usage

The pipeline can be run without the GUI:

```powershell
.\.venv\Scripts\Activate.ps1
python src\transcribe_3speakers.py "path\to\audio.m4a" `
    --speakers 3 `
    --names "Alice,Bob,Charlie" `
    --lang fr `
    --formats txt,srt
```

| Flag | Default | Description |
|---|---|---|
| `--speakers` | `3` | Number of speakers (1–8) |
| `--names` | — | Speaker names, most talkative first, comma-separated |
| `--lang` | `fr` | Language: `fr` (Canadian French) or `en` |
| `--no-timestamps` | — | Omit timestamps from `.txt` / `.md` |
| `--formats` | `txt` | Comma-separated: `txt`, `md`, `srt`, `mkv`, `json` |
| `--out-dir` | same as audio | Output folder |
| `--preview` | — | Process only the first N seconds (for testing) |
| `--initial-prompt` | — | Custom context hint for Whisper (e.g. domain vocabulary) |

---

## First-time setup (developer / contributor path)

> **End users:** use `setup.ps1` instead — it does all of this for you. See the [latest release](https://github.com/MedEvent-DevGroup/The-Earful-Tower/releases/latest).

**1. Clone and create the virtual environment**
```powershell
git clone https://github.com/MedEvent-DevGroup/The-Earful-Tower.git
cd The-Earful-Tower
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install torch==2.4.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu121
pip install -r src\requirements.txt
```

**2. Add your HuggingFace token**

Create the `connectors/` folder and a token file inside it:
```
connectors\huggingface-read.md
```
See `_template.md` for the exact format. Get a free read-only token at [huggingface.co](https://huggingface.co) → Settings → Access Tokens → New token.

**3. Accept pyannote model terms** (one-time, in browser while signed into HuggingFace)
- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0

**4. Launch**
```powershell
.\.venv\Scripts\Activate.ps1
python src\app.py
```

---

## Project structure

```
The-Earful-Tower/
├── README.md
├── AGENT_PROMPT.md            — onboarding prompt for AI coding assistants
├── _template.md               — template for connector credential files
├── .gitignore
├── icon.ico                   — app icon
├── connectors/                — API credentials (gitignored, never committed)
│   └── huggingface-read.md    — your HF token
├── .venv/                     — Python environment (gitignored)
└── src/
    ├── app.py                 — GUI (CustomTkinter + splash screen)
    ├── transcribe_3speakers.py — full pipeline (also usable as CLI)
    ├── i18n.py                — UI translation helper
    ├── locales/
    │   ├── en.json            — English strings
    │   ├── fr.json            — French Canadian strings
    │   └── _template.json     — template for adding a new language
    ├── make_icon.py           — icon generator (one-time use)
    └── requirements.txt       — pinned dependencies
```

---

## Adding a language

1. Copy `src/locales/_template.json` → `src/locales/<lang>.json` (e.g. `es.json`)
2. Fill in every string value — do not change key names
3. Add your language's display name to `src/i18n.py` in the `_DISPLAY_NAMES` dict
4. Test: launch the app, select your language in the 🌐 menu, verify all labels
5. Open a pull request

---

## Dependency notes

Versions are pinned in `src/requirements.txt`. Key constraints — do not change these without reading the notes:

| Package | Pinned to | Reason |
|---|---|---|
| `huggingface_hub` | `0.25.2` | ≥ 0.26 removed `use_auth_token` kwarg that pyannote still uses internally |
| `speechbrain` | `1.0.2` | 1.1+ has a lazy-import that conflicts with `pytorch_lightning` |
| `gradio` | not used | requires `huggingface_hub ≥ 0.33.5` — incompatible with pyannote pin |

---

## Credits

Created by [Eddy](https://github.com/eddyafram) · Built with [Claude](https://claude.ai) (Anthropic)

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for details.
